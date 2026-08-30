from __future__ import annotations

import argparse
import base64
import concurrent.futures
import gzip
import hashlib
import json
import math
import os
import sys
import threading
import time
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core import validate_response
from paid_pilot import (
    BASE,
    build_payload,
    load_json,
    reconstruct_and_verify,
    request_json,
    usage_record,
)

CONFIG = HERE / "config" / "preflight.json"
PILOT_CONFIG = HERE / "config" / "pilot.json"
SCHEMA = HERE / "prompts" / "response_schema.json"
AAD = b"RPF_STUDY1_RESULTS_V1"
PRINT_LOCK = threading.Lock()


def request_ceiling_cost(row: dict, cfg: dict) -> float:
    ceiling = cfg["run_policy"]["provider_max_price_usd_per_million"]
    prompt_tokens = max(1, math.ceil(len(row["prompt"]) / 3.2))
    completion_tokens = int(row["reasoning_settings"]["max_completion_tokens"])
    return prompt_tokens / 1e6 * float(ceiling["prompt"]) + completion_tokens / 1e6 * float(ceiling["completion"])


def encrypt_raw(raw_rows: list[dict], out: Path, api_key: str) -> None:
    plaintext = "".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in raw_rows
    ).encode("utf-8")
    compressed = gzip.compress(plaintext, compresslevel=9)
    aes_key = hashlib.sha256(AAD + b"|" + api_key.encode()).digest()
    nonce = os.urandom(12)
    blob = nonce + AESGCM(aes_key).encrypt(nonce, compressed, AAD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(base64.b64encode(blob).decode("ascii"), encoding="ascii")


def one_attempt(row: dict, cfg: dict, schema: dict, reasoning_exclude: bool, key: str, ordinal: int, attempt: int) -> dict:
    payload = build_payload(row, cfg, schema, reasoning_exclude)
    started = time.perf_counter()
    ceiling = request_ceiling_cost(row, cfg)
    try:
        response = request_json(f"{BASE}/chat/completions", key, payload, timeout=150)
    except Exception as exc:
        return {
            "ordinal": ordinal,
            "request_id": row["request_id"],
            "anon_id": row["anon_id"],
            "reasoning": row["reasoning"],
            "attempt": attempt,
            "response_received": False,
            "schema_valid": False,
            "error": f"request:{type(exc).__name__}:{str(exc)[:220]}",
            "latency_seconds": round(time.perf_counter() - started, 4),
            "cost_usd": None,
            "accounted_upper_bound_usd": ceiling,
            "request_ceiling_usd": ceiling,
        }

    accounting = usage_record(response, key)
    choices = response.get("choices") or []
    choice = choices[0] if choices else {}
    finish_reason = choice.get("finish_reason") or accounting.pop("meta_finish_reason", None)
    record = {
        "ordinal": ordinal,
        "request_id": row["request_id"],
        "anon_id": row["anon_id"],
        "reasoning": row["reasoning"],
        "attempt": attempt,
        "response_received": True,
        **accounting,
        "finish_reason": finish_reason,
        "latency_seconds": round(time.perf_counter() - started, 4),
        "schema_valid": False,
        "request_ceiling_usd": ceiling,
    }
    known_cost = record.get("cost_usd")
    record["accounted_upper_bound_usd"] = float(known_cost) if known_cost is not None else ceiling

    try:
        if not choices:
            raise RuntimeError("OpenRouter response has no choices")
        content = (choice.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenRouter response content is not a non-empty string")
        parsed = json.loads(content)
        validate_response(parsed)
    except json.JSONDecodeError as exc:
        record["error"] = f"schema_or_json:{type(exc).__name__}"
        return {"attempt_record": record, "parsed": None}
    except ValueError as exc:
        record["error"] = f"schema_or_json:{type(exc).__name__}"
        return {"attempt_record": record, "parsed": None}
    except Exception as exc:
        record["error"] = f"request:{type(exc).__name__}:{str(exc)[:220]}"
        return {"attempt_record": record, "parsed": None}

    record["schema_valid"] = True
    return {"attempt_record": record, "parsed": parsed}


def normalize_attempt_result(result: dict) -> tuple[dict, dict | None]:
    if "attempt_record" in result:
        return result["attempt_record"], result.get("parsed")
    return result, None


def write_checkpoint(outdir: Path, attempts: list[dict], successes: dict[str, dict], raw: dict[str, dict], key: str, summary_extra: dict) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    attempt_sorted = sorted(attempts, key=lambda r: (int(r["ordinal"]), int(r["attempt"])))
    success_sorted = sorted(successes.values(), key=lambda r: int(r["ordinal"]))
    raw_sorted = [raw[k] for k in sorted(raw, key=lambda rid: int(successes[rid]["ordinal"]))]
    (outdir / "attempt_history.json").write_text(json.dumps(attempt_sorted, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "production_requests.json").write_text(json.dumps(success_sorted, indent=2, sort_keys=True), encoding="utf-8")
    encrypt_raw(raw_sorted, outdir / "raw_results.enc.b64", key)
    (outdir / "progress.json").write_text(json.dumps(summary_extra, indent=2, sort_keys=True), encoding="utf-8")


def run(spend_cap: float, workdir: Path) -> dict:
    if os.getenv("RPF_ENABLE_STUDY1") != "YES_I_ACCEPT_STUDY1_COST":
        raise RuntimeError("Study 1 authorization environment variable is missing")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    cfg = load_json(CONFIG)
    pilot_cfg = load_json(PILOT_CONFIG)
    schema = load_json(SCHEMA)
    study_cap = float(cfg["study_1"]["study_budget_cap_usd"])
    if spend_cap > study_cap + 1e-12:
        raise RuntimeError(f"Requested spend cap {spend_cap:.6f} exceeds frozen Study 1 cap {study_cap:.6f}")

    rows, freeze_manifest = reconstruct_and_verify(workdir)
    if len(rows) != 3000 or len({r["anon_id"] for r in rows}) != 1000:
        raise RuntimeError("Production reconstruction is not exactly 1000 respondents / 3000 requests")
    if {r["reasoning"] for r in rows} != {"off", "low", "medium"}:
        raise RuntimeError("Production reconstruction has unexpected treatment arms")

    single_pass_ceiling = sum(request_ceiling_cost(r, cfg) for r in rows)
    if single_pass_ceiling > spend_cap + 1e-12:
        raise RuntimeError(
            f"Frozen one-attempt production ceiling {single_pass_ceiling:.6f} exceeds spend cap {spend_cap:.6f}"
        )

    concurrency = int(cfg["run_policy"].get("concurrency") or 1)
    if concurrency < 1 or concurrency > 16:
        raise RuntimeError("Production concurrency must be between 1 and 16")

    reasoning_exclude = bool(pilot_cfg.get("reasoning_exclude_from_response", True))
    max_attempts = int(cfg["run_policy"].get("max_retries") or 1)
    max_attempts = max(1, min(3, max_attempts))
    outdir = workdir / "study1_output"
    attempts: list[dict] = []
    successes: dict[str, dict] = {}
    raw: dict[str, dict] = {}
    row_by_id = {r["request_id"]: r for r in rows}
    ordinal_by_id = {r["request_id"]: i for i, r in enumerate(rows, start=1)}

    print(json.dumps({
        "status": "STUDY1_START",
        "respondents": 1000,
        "requests": 3000,
        "conditions": ["off", "low", "medium"],
        "provider_order": cfg["run_policy"].get("provider_order"),
        "allow_provider_fallbacks": bool(cfg["run_policy"].get("allow_provider_fallbacks")),
        "spend_cap_usd": spend_cap,
        "single_pass_provider_ceiling_usd": round(single_pass_ceiling, 6),
        "concurrency": concurrency,
        "freeze_requests_sha256": freeze_manifest["hashes"]["requests_jsonl_sha256"],
    }, indent=2, sort_keys=True))

    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        future_map = {
            pool.submit(one_attempt, row, cfg, schema, reasoning_exclude, key, i, 1): row
            for i, row in enumerate(rows, start=1)
        }
        for future in concurrent.futures.as_completed(future_map):
            row = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                ceiling = request_ceiling_cost(row, cfg)
                result = {
                    "ordinal": ordinal_by_id[row["request_id"]],
                    "request_id": row["request_id"],
                    "anon_id": row["anon_id"],
                    "reasoning": row["reasoning"],
                    "attempt": 1,
                    "response_received": False,
                    "schema_valid": False,
                    "error": f"worker:{type(exc).__name__}:{str(exc)[:220]}",
                    "cost_usd": None,
                    "accounted_upper_bound_usd": ceiling,
                    "request_ceiling_usd": ceiling,
                }
            rec, parsed = normalize_attempt_result(result)
            attempts.append(rec)
            if rec.get("schema_valid") and parsed is not None:
                rid = row["request_id"]
                successes[rid] = {
                    "ordinal": rec["ordinal"],
                    "request_id": rid,
                    "reasoning": row["reasoning"],
                    "generation_id": rec.get("generation_id"),
                    "provider_name": rec.get("provider_name"),
                    "model_returned": rec.get("model_returned"),
                    "finish_reason": rec.get("finish_reason"),
                    "prompt_tokens": rec.get("prompt_tokens", 0),
                    "completion_tokens": rec.get("completion_tokens", 0),
                    "reasoning_tokens": rec.get("reasoning_tokens", 0),
                    "cost_usd": rec.get("cost_usd"),
                    "latency_seconds": rec.get("latency_seconds"),
                    "schema_valid": True,
                    "attempts": 1,
                }
                raw[rid] = {
                    "request_id": rid,
                    "anon_id": row["anon_id"],
                    "reasoning": row["reasoning"],
                    "generation_id": rec.get("generation_id"),
                    "response": parsed,
                }
            completed += 1
            if completed % 50 == 0 or completed == len(rows):
                accounted = sum(float(a.get("accounted_upper_bound_usd") or 0.0) for a in attempts)
                with PRINT_LOCK:
                    print(json.dumps({
                        "phase": "first_pass",
                        "completed": completed,
                        "schema_valid": len(successes),
                        "failures_so_far": completed - len(successes),
                        "accounted_upper_bound_usd": round(accounted, 6),
                    }, sort_keys=True), flush=True)
            if completed % 250 == 0:
                accounted = sum(float(a.get("accounted_upper_bound_usd") or 0.0) for a in attempts)
                write_checkpoint(outdir, attempts, successes, raw, key, {
                    "phase": "first_pass",
                    "completed": completed,
                    "schema_valid": len(successes),
                    "accounted_upper_bound_usd": round(accounted, 8),
                })

    failed_ids = [r["request_id"] for r in rows if r["request_id"] not in successes]
    repair_attempts_sent = 0
    budget_blocked_repairs = 0

    for attempt_no in range(2, max_attempts + 1):
        if not failed_ids:
            break
        next_failed: list[str] = []
        for rid in failed_ids:
            row = row_by_id[rid]
            accounted_before = sum(float(a.get("accounted_upper_bound_usd") or 0.0) for a in attempts)
            ceiling = request_ceiling_cost(row, cfg)
            if accounted_before + ceiling > spend_cap + 1e-12:
                budget_blocked_repairs += 1
                next_failed.append(rid)
                continue
            result = one_attempt(row, cfg, schema, reasoning_exclude, key, ordinal_by_id[rid], attempt_no)
            rec, parsed = normalize_attempt_result(result)
            attempts.append(rec)
            repair_attempts_sent += 1
            if rec.get("schema_valid") and parsed is not None:
                successes[rid] = {
                    "ordinal": rec["ordinal"],
                    "request_id": rid,
                    "reasoning": row["reasoning"],
                    "generation_id": rec.get("generation_id"),
                    "provider_name": rec.get("provider_name"),
                    "model_returned": rec.get("model_returned"),
                    "finish_reason": rec.get("finish_reason"),
                    "prompt_tokens": rec.get("prompt_tokens", 0),
                    "completion_tokens": rec.get("completion_tokens", 0),
                    "reasoning_tokens": rec.get("reasoning_tokens", 0),
                    "cost_usd": rec.get("cost_usd"),
                    "latency_seconds": rec.get("latency_seconds"),
                    "schema_valid": True,
                    "attempts": attempt_no,
                }
                raw[rid] = {
                    "request_id": rid,
                    "anon_id": row["anon_id"],
                    "reasoning": row["reasoning"],
                    "generation_id": rec.get("generation_id"),
                    "response": parsed,
                }
            else:
                next_failed.append(rid)
        failed_ids = next_failed
        accounted = sum(float(a.get("accounted_upper_bound_usd") or 0.0) for a in attempts)
        write_checkpoint(outdir, attempts, successes, raw, key, {
            "phase": f"repair_{attempt_no}",
            "schema_valid": len(successes),
            "remaining_failures": len(failed_ids),
            "accounted_upper_bound_usd": round(accounted, 8),
        })

    response_attempts = [a for a in attempts if a.get("response_received")]
    known_costs = [float(a["cost_usd"]) for a in response_attempts if a.get("cost_usd") is not None]
    accounted_upper = sum(float(a.get("accounted_upper_bound_usd") or 0.0) for a in attempts)
    parse_failures = sum(1 for a in attempts if str(a.get("error", "")).startswith("schema_or_json:"))
    conditions_valid = {
        c: sum(1 for r in successes.values() if r["reasoning"] == c)
        for c in ("off", "low", "medium")
    }
    summary = {
        "study": "CAMS reasoning population fidelity Study 1",
        "respondents": 1000,
        "requests_planned": 3000,
        "requests_schema_valid": len(successes),
        "all_schema_valid": len(successes) == 3000 and not failed_ids,
        "remaining_failures": len(failed_ids),
        "failed_request_ids_sha256": hashlib.sha256("\n".join(sorted(failed_ids)).encode()).hexdigest() if failed_ids else None,
        "parse_failure_attempts": parse_failures,
        "total_attempts_sent": len(attempts),
        "repair_attempts_sent": repair_attempts_sent,
        "budget_blocked_repairs": budget_blocked_repairs,
        "spend_cap_usd": spend_cap,
        "single_pass_provider_ceiling_usd": round(single_pass_ceiling, 6),
        "accounted_upper_bound_usd": round(accounted_upper, 8),
        "known_realized_cost_usd": round(sum(known_costs), 8) if known_costs else None,
        "prompt_tokens_all_received_attempts": sum(int(a.get("prompt_tokens") or 0) for a in response_attempts),
        "completion_tokens_all_received_attempts": sum(int(a.get("completion_tokens") or 0) for a in response_attempts),
        "reasoning_tokens_all_received_attempts": sum(int(a.get("reasoning_tokens") or 0) for a in response_attempts),
        "finish_reasons": sorted({str(a.get("finish_reason")) for a in response_attempts if a.get("finish_reason") is not None}),
        "providers": sorted({str(a.get("provider_name")) for a in response_attempts if a.get("provider_name")}),
        "models_returned": sorted({str(a.get("model_returned")) for a in response_attempts if a.get("model_returned")}),
        "condition_valid_counts": conditions_valid,
        "provider_order": cfg["run_policy"].get("provider_order") or [],
        "allow_provider_fallbacks": bool(cfg["run_policy"].get("allow_provider_fallbacks")),
        "provider_data_collection": cfg["run_policy"].get("provider_data_collection"),
        "freeze_requests_sha256": freeze_manifest["hashes"]["requests_jsonl_sha256"],
        "freeze_request_id_set_sha256": freeze_manifest["hashes"]["request_id_set_sha256"],
        "human_truth_loaded_for_scoring": False,
        "substantive_outputs_inspected_during_run": False,
        "raw_results_storage": "AES-GCM encrypted artifact only",
    }

    write_checkpoint(outdir, attempts, successes, raw, key, summary)
    (outdir / "study1_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)

    if accounted_upper > spend_cap + 1e-9:
        raise RuntimeError("Production accounted upper bound exceeded hard spend cap")
    if not summary["all_schema_valid"]:
        raise SystemExit(2)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spend-cap", type=float, default=7.8)
    ap.add_argument("--workdir", default="/tmp/rpf_study1")
    args = ap.parse_args()
    run(args.spend_cap, Path(args.workdir))


if __name__ == "__main__":
    main()
