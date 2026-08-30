from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core import load_jsonl, validate_response
from freeze_real_cams import freeze

CONFIG = HERE / "config" / "preflight.json"
PILOT_CONFIG = HERE / "config" / "pilot.json"
SCHEMA = HERE / "prompts" / "response_schema.json"
FREEZE_RECORD = HERE / "outputs" / "frozen" / "STUDY1_REQUEST_FREEZE.json"
BASE = "https://openrouter.ai/api/v1"
CONDITION_ORDER = {"off": 0, "low": 1, "medium": 2}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def request_json(url: str, key: str, body: dict | None = None, timeout: int = 90) -> dict:
    headers = {
        "Authorization": f"Bearer {key}",
        "User-Agent": "LLM-Persona-RPF-Engineering-Pilot/1.3",
        "Content-Type": "application/json",
    }
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url, headers=headers, data=data, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
            msg = parsed.get("error", {}).get("message") or parsed.get("message") or f"HTTP {e.code}"
        except Exception:
            msg = f"HTTP {e.code}"
        raise RuntimeError(f"OpenRouter request failed: {e.code}: {msg[:300]}") from None


def reconstruct_and_verify(workdir: Path) -> tuple[list[dict], dict]:
    record = load_json(FREEZE_RECORD)
    generated = freeze(workdir / "base.jsonl", workdir / "requests.jsonl", workdir / "freeze_manifest.json")
    if record.get("freeze_version") != generated.get("freeze_version"):
        raise RuntimeError("Committed freeze version does not match reconstructed freeze")
    for name in ("base_jsonl_sha256", "config_sha256", "request_id_set_sha256", "requests_jsonl_sha256", "schema_sha256"):
        if record["hashes"][name] != generated["hashes"][name]:
            raise RuntimeError(f"Frozen request verification failed for {name}")
    if record["respondents"] != generated["respondents"] or record["requests"] != generated["requests"]:
        raise RuntimeError("Frozen request counts do not match committed freeze record")
    if record["conditions"] != generated["conditions"]:
        raise RuntimeError("Frozen treatment arms do not match committed freeze record")
    return load_jsonl(workdir / "requests.jsonl"), generated


def select_pilot(rows: list[dict], n_respondents: int, label: str) -> list[dict]:
    ids = sorted({r["anon_id"] for r in rows}, key=lambda x: hashlib.sha256(f"{label}|{x}".encode()).hexdigest())
    selected_ids = set(ids[:n_respondents])
    selected = [r for r in rows if r["anon_id"] in selected_ids]
    selected.sort(key=lambda r: (hashlib.sha256(f"{label}|{r['anon_id']}".encode()).hexdigest(), CONDITION_ORDER[r["reasoning"]]))
    if len(selected) != n_respondents * 3:
        raise RuntimeError("Pilot selection does not contain complete respondent triplets")
    for anon in selected_ids:
        group = [r for r in selected if r["anon_id"] == anon]
        if {r["reasoning"] for r in group} != {"off", "low", "medium"}:
            raise RuntimeError(f"Incomplete pilot triplet for {anon}")
        if len({r["prompt"] for r in group}) != 1:
            raise RuntimeError(f"Pilot prompt mismatch for {anon}")
    return selected


def projected_ceiling_cost(rows: list[dict], cfg: dict, attempts: int = 1) -> float:
    ceiling = cfg["run_policy"]["provider_max_price_usd_per_million"]
    input_tokens = sum(max(1, math.ceil(len(r["prompt"]) / 3.2)) for r in rows)
    output_tokens = sum(int(r["reasoning_settings"]["max_completion_tokens"]) for r in rows)
    one_attempt = input_tokens / 1e6 * float(ceiling["prompt"]) + output_tokens / 1e6 * float(ceiling["completion"])
    return one_attempt * attempts


def reasoning_payload(row: dict, exclude: bool) -> dict:
    settings = row["reasoning_settings"]
    if settings.get("enabled") is False:
        return {"enabled": False, "exclude": bool(exclude)}
    effort = settings.get("effort")
    if effort not in {"low", "medium"}:
        raise RuntimeError(f"Unexpected enabled reasoning effort: {effort}")
    return {"effort": effort, "exclude": bool(exclude)}


def build_payload(row: dict, cfg: dict, schema: dict, reasoning_exclude: bool) -> dict:
    generation = row["generation_settings"]
    policy = cfg["run_policy"]
    provider = {
        "allow_fallbacks": bool(policy["allow_provider_fallbacks"]),
        "require_parameters": bool(policy["require_parameters"]),
        "data_collection": policy["provider_data_collection"],
        "max_price": {
            "prompt": float(policy["provider_max_price_usd_per_million"]["prompt"]),
            "completion": float(policy["provider_max_price_usd_per_million"]["completion"]),
        },
    }
    order = policy.get("provider_order") or []
    if order:
        provider["order"] = list(order)
    else:
        provider["sort"] = policy["provider_sort"]
    return {
        "model": row["model"],
        "messages": [{"role": "user", "content": row["prompt"]}],
        "temperature": float(generation["temperature"]),
        "top_p": float(generation["top_p"]),
        "max_tokens": int(row["reasoning_settings"]["max_completion_tokens"]),
        "reasoning": reasoning_payload(row, reasoning_exclude),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "cams_reasoning_population_response",
                "strict": True,
                "schema": schema,
            },
        },
        "provider": provider,
        "usage": {"include": True},
    }


def generation_metadata(key: str, generation_id: str) -> dict:
    url = f"{BASE}/generation?{urllib.parse.urlencode({'id': generation_id})}"
    for attempt in range(5):
        try:
            data = request_json(url, key, body=None, timeout=30).get("data") or {}
            if data:
                return data
        except Exception:
            pass
        if attempt < 4:
            time.sleep(0.5)
    return {}


def usage_record(response: dict, key: str) -> dict:
    generation_id = response.get("id") or ""
    meta = generation_metadata(key, generation_id) if generation_id else {}
    usage = response.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or meta.get("tokens_prompt") or 0)
    completion_tokens = int(usage.get("completion_tokens") or meta.get("tokens_completion") or 0)
    details = usage.get("completion_tokens_details") or usage.get("completionTokensDetails") or {}
    reasoning_tokens = int(details.get("reasoning_tokens") or details.get("reasoningTokens") or meta.get("native_tokens_reasoning") or 0)
    cost = usage.get("cost")
    if cost is None:
        cost = meta.get("total_cost")
    provider_name = response.get("provider") or meta.get("provider_name")
    return {
        "generation_id": generation_id,
        "provider_name": provider_name,
        "model_returned": response.get("model") or meta.get("model"),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "cost_usd": None if cost is None else float(cost),
        "meta_finish_reason": meta.get("finish_reason"),
    }


def encrypt_raw(raw_rows: list[dict], out: Path, key: str) -> None:
    plaintext = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in raw_rows).encode("utf-8")
    compressed = gzip.compress(plaintext, compresslevel=9)
    aes_key = hashlib.sha256(("RPF_ENGINEERING_PILOT_RESULTS_V1|" + key).encode()).digest()
    nonce = os.urandom(12)
    aad = b"RPF_ENGINEERING_PILOT_RESULTS_V1"
    blob = nonce + AESGCM(aes_key).encrypt(nonce, compressed, aad)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(base64.b64encode(blob).decode("ascii"), encoding="ascii")


def run_pilot(n_respondents: int, spend_cap: float, workdir: Path) -> dict:
    if os.getenv("RPF_ENABLE_PILOT") != "YES_I_ACCEPT_PILOT_COST":
        raise RuntimeError("Engineering pilot authorization environment variable is missing")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    cfg = load_json(CONFIG)
    pilot_cfg = load_json(PILOT_CONFIG)
    if cfg["paid_runs_enabled"] is not False:
        raise RuntimeError("Full paid-run flag must remain false during engineering pilot")
    if not pilot_cfg["pilot_enabled"]:
        raise RuntimeError("Pilot is disabled")
    max_attempts = int(pilot_cfg["max_attempts_per_request"])
    if max_attempts < 1 or max_attempts > 3:
        raise RuntimeError("Engineering pilot max attempts must be between 1 and 3")
    if n_respondents not in {int(pilot_cfg["canary_respondents"]), int(pilot_cfg["full_pilot_respondents"])}:
        raise RuntimeError("Pilot respondent count is not an allowed pilot size")

    rows, freeze_manifest = reconstruct_and_verify(workdir)
    selected = select_pilot(rows, n_respondents, pilot_cfg["selection_seed_label"])
    ceiling_projection = projected_ceiling_cost(selected, cfg, max_attempts)
    if ceiling_projection > spend_cap:
        raise RuntimeError(f"Pilot worst-case projection {ceiling_projection:.6f} exceeds cap {spend_cap:.6f}")

    schema = load_json(SCHEMA)
    final_rows: list[dict] = []
    attempt_rows: list[dict] = []
    raw_rows: list[dict] = []
    actual_cost_known = 0.0
    failures = 0
    parse_failures = 0
    total_attempts_sent = 0

    for index, row in enumerate(selected, start=1):
        payload = build_payload(row, cfg, schema, bool(pilot_cfg["reasoning_exclude_from_response"]))
        succeeded = False
        last_error = "unknown"
        final_attempt = 0

        for attempt in range(1, max_attempts + 1):
            total_attempts_sent += 1
            final_attempt = attempt
            started = time.perf_counter()
            try:
                response = request_json(f"{BASE}/chat/completions", key, payload, timeout=120)
            except Exception as e:
                last_error = f"request:{type(e).__name__}:{str(e)[:200]}"
                attempt_rows.append({
                    "ordinal": index,
                    "request_id": row["request_id"],
                    "reasoning": row["reasoning"],
                    "attempt": attempt,
                    "response_received": False,
                    "schema_valid": False,
                    "error": last_error,
                    "latency_seconds": round(time.perf_counter() - started, 4),
                })
                if attempt < max_attempts:
                    time.sleep(0.5 * attempt)
                    continue
                break

            accounting = usage_record(response, key)
            if accounting["cost_usd"] is not None:
                actual_cost_known += float(accounting["cost_usd"])
            if actual_cost_known > spend_cap:
                raise RuntimeError(f"Known realized pilot cost {actual_cost_known:.6f} exceeded hard pilot cap {spend_cap:.6f}")

            choices = response.get("choices") or []
            choice = choices[0] if choices else {}
            finish_reason = choice.get("finish_reason") or accounting.pop("meta_finish_reason", None)
            attempt_record = {
                "ordinal": index,
                "request_id": row["request_id"],
                "reasoning": row["reasoning"],
                "attempt": attempt,
                "response_received": True,
                **accounting,
                "finish_reason": finish_reason,
                "latency_seconds": round(time.perf_counter() - started, 4),
                "schema_valid": False,
            }

            try:
                if not choices:
                    raise RuntimeError("OpenRouter response has no choices")
                content = (choice.get("message") or {}).get("content")
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("OpenRouter response content is not a non-empty string")
                parsed = json.loads(content)
                validate_response(parsed)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = f"schema_or_json:{type(e).__name__}"
                attempt_record["error"] = last_error
                attempt_rows.append(attempt_record)
                if attempt < max_attempts:
                    time.sleep(0.5 * attempt)
                    continue
                parse_failures += 1
                break
            except Exception as e:
                last_error = f"request:{type(e).__name__}:{str(e)[:200]}"
                attempt_record["error"] = last_error
                attempt_rows.append(attempt_record)
                if attempt < max_attempts:
                    time.sleep(0.5 * attempt)
                    continue
                break

            attempt_record["schema_valid"] = True
            attempt_rows.append(attempt_record)
            final_rows.append({
                "ordinal": index,
                "request_id": row["request_id"],
                "reasoning": row["reasoning"],
                "generation_id": attempt_record.get("generation_id"),
                "provider_name": attempt_record.get("provider_name"),
                "model_returned": attempt_record.get("model_returned"),
                "finish_reason": finish_reason,
                "prompt_tokens": attempt_record.get("prompt_tokens", 0),
                "completion_tokens": attempt_record.get("completion_tokens", 0),
                "reasoning_tokens": attempt_record.get("reasoning_tokens", 0),
                "cost_usd": attempt_record.get("cost_usd"),
                "latency_seconds": attempt_record.get("latency_seconds"),
                "schema_valid": True,
                "attempts": attempt,
            })
            raw_rows.append({
                "request_id": row["request_id"],
                "anon_id": row["anon_id"],
                "reasoning": row["reasoning"],
                "generation_id": attempt_record.get("generation_id"),
                "response": parsed,
            })
            succeeded = True
            break

        if not succeeded:
            failures += 1
            final_rows.append({
                "ordinal": index,
                "request_id": row["request_id"],
                "reasoning": row["reasoning"],
                "schema_valid": False,
                "attempts": final_attempt,
                "error": last_error,
            })
            break

    outdir = workdir / "pilot_output"
    outdir.mkdir(parents=True, exist_ok=True)
    encrypt_raw(raw_rows, outdir / "raw_results.enc.b64", key)
    valid_rows = [r for r in final_rows if r.get("schema_valid")]
    response_attempts = [r for r in attempt_rows if r.get("response_received")]
    known_costs = [float(r["cost_usd"]) for r in response_attempts if r.get("cost_usd") is not None]
    provider_order = cfg["run_policy"].get("provider_order") or []

    summary = {
        "pilot_type": "canary" if n_respondents == int(pilot_cfg["canary_respondents"]) else "engineering_pilot",
        "respondents_requested": n_respondents,
        "requests_planned": n_respondents * 3,
        "requests_schema_valid": len(valid_rows),
        "failures": failures,
        "parse_failures": parse_failures,
        "all_schema_valid": len(valid_rows) == n_respondents * 3 and failures == 0 and parse_failures == 0,
        "max_attempts_per_request": max_attempts,
        "total_attempts_sent": total_attempts_sent,
        "retry_count": max(0, total_attempts_sent - len(valid_rows) - failures),
        "spend_cap_usd": spend_cap,
        "worst_case_all_attempts_provider_ceiling_projection_usd": round(ceiling_projection, 6),
        "known_realized_cost_usd": round(sum(known_costs), 8) if known_costs else None,
        "prompt_tokens_all_responses": sum(int(r.get("prompt_tokens") or 0) for r in response_attempts),
        "completion_tokens_all_responses": sum(int(r.get("completion_tokens") or 0) for r in response_attempts),
        "reasoning_tokens_all_responses": sum(int(r.get("reasoning_tokens") or 0) for r in response_attempts),
        "finish_reasons": sorted({str(r.get("finish_reason")) for r in response_attempts if r.get("finish_reason") is not None}),
        "providers": sorted({str(r.get("provider_name")) for r in response_attempts if r.get("provider_name")}),
        "provider_order": provider_order,
        "allow_provider_fallbacks": bool(cfg["run_policy"]["allow_provider_fallbacks"]),
        "models_returned": sorted({str(r.get("model_returned")) for r in response_attempts if r.get("model_returned")}),
        "freeze_requests_sha256": freeze_manifest["hashes"]["requests_jsonl_sha256"],
        "freeze_request_id_set_sha256": freeze_manifest["hashes"]["request_id_set_sha256"],
        "human_truth_loaded_for_scoring": False,
        "substantive_outputs_inspected": False,
        "raw_results_storage": "AES-GCM encrypted artifact only",
    }
    (outdir / "engineering_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "engineering_requests.json").write_text(json.dumps(final_rows, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "attempt_history.json").write_text(json.dumps(attempt_rows, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["all_schema_valid"]:
        raise SystemExit(2)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--respondents", type=int, required=True)
    ap.add_argument("--spend-cap", type=float, required=True)
    ap.add_argument("--workdir", default="/tmp/rpf_paid_pilot")
    args = ap.parse_args()
    run_pilot(args.respondents, args.spend_cap, Path(args.workdir))


if __name__ == "__main__":
    main()
