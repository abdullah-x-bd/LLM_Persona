from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core import validate_response
from paid_pilot import (
    BASE, CONFIG, PILOT_CONFIG, SCHEMA,
    build_payload, encrypt_raw, load_json, projected_ceiling_cost,
    reconstruct_and_verify, request_json, select_pilot, usage_record,
)


def run(n_respondents: int, spend_cap: float, workdir: Path) -> dict:
    if os.getenv("RPF_ENABLE_PILOT") != "YES_I_ACCEPT_PILOT_COST":
        raise RuntimeError("Engineering pilot authorization environment variable is missing")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    cfg = load_json(CONFIG)
    pilot_cfg = load_json(PILOT_CONFIG)
    if n_respondents != int(pilot_cfg["full_pilot_respondents"]):
        raise RuntimeError("Full-scan runner is restricted to the frozen engineering pilot size")
    max_attempts = int(pilot_cfg["max_attempts_per_request"])
    rows, freeze_manifest = reconstruct_and_verify(workdir)
    selected = select_pilot(rows, n_respondents, pilot_cfg["selection_seed_label"])
    ceiling_projection = projected_ceiling_cost(selected, cfg, max_attempts)
    if ceiling_projection > spend_cap:
        raise RuntimeError(f"Pilot worst-case projection {ceiling_projection:.6f} exceeds cap {spend_cap:.6f}")

    schema = load_json(SCHEMA)
    attempts = []
    final_rows = []
    raw_rows = []
    actual_cost_known = 0.0
    parse_failures = 0

    for index, row in enumerate(selected, start=1):
        payload = build_payload(row, cfg, schema, bool(pilot_cfg["reasoning_exclude_from_response"]))
        succeeded = False
        last_error = "unknown"
        final_attempt = 0
        for attempt in range(1, max_attempts + 1):
            final_attempt = attempt
            started = time.perf_counter()
            try:
                response = request_json(f"{BASE}/chat/completions", key, payload, timeout=150)
            except Exception as exc:
                last_error = f"request:{type(exc).__name__}:{str(exc)[:200]}"
                attempts.append({
                    "ordinal": index, "request_id": row["request_id"], "reasoning": row["reasoning"],
                    "attempt": attempt, "response_received": False, "schema_valid": False,
                    "error": last_error, "latency_seconds": round(time.perf_counter() - started, 4),
                })
                if attempt < max_attempts:
                    time.sleep(0.5 * attempt)
                    continue
                break

            accounting = usage_record(response, key)
            if accounting.get("cost_usd") is not None:
                actual_cost_known += float(accounting["cost_usd"])
            if actual_cost_known > spend_cap:
                raise RuntimeError(f"Known realized pilot cost {actual_cost_known:.6f} exceeded hard cap {spend_cap:.6f}")

            choices = response.get("choices") or []
            choice = choices[0] if choices else {}
            finish_reason = choice.get("finish_reason") or accounting.pop("meta_finish_reason", None)
            rec = {
                "ordinal": index, "request_id": row["request_id"], "reasoning": row["reasoning"],
                "attempt": attempt, "response_received": True, **accounting,
                "finish_reason": finish_reason,
                "latency_seconds": round(time.perf_counter() - started, 4), "schema_valid": False,
            }
            try:
                if not choices:
                    raise RuntimeError("OpenRouter response has no choices")
                content = (choice.get("message") or {}).get("content")
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("OpenRouter response content is not a non-empty string")
                parsed = json.loads(content)
                validate_response(parsed)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = f"schema_or_json:{type(exc).__name__}"
                rec["error"] = last_error
                attempts.append(rec)
                if attempt < max_attempts:
                    time.sleep(0.5 * attempt)
                    continue
                parse_failures += 1
                break
            except Exception as exc:
                last_error = f"request:{type(exc).__name__}:{str(exc)[:200]}"
                rec["error"] = last_error
                attempts.append(rec)
                if attempt < max_attempts:
                    time.sleep(0.5 * attempt)
                    continue
                break

            rec["schema_valid"] = True
            attempts.append(rec)
            final_rows.append({
                "ordinal": index, "request_id": row["request_id"], "reasoning": row["reasoning"],
                "generation_id": rec.get("generation_id"), "provider_name": rec.get("provider_name"),
                "model_returned": rec.get("model_returned"), "finish_reason": finish_reason,
                "prompt_tokens": rec.get("prompt_tokens", 0), "completion_tokens": rec.get("completion_tokens", 0),
                "reasoning_tokens": rec.get("reasoning_tokens", 0), "cost_usd": rec.get("cost_usd"),
                "latency_seconds": rec.get("latency_seconds"), "schema_valid": True, "attempts": attempt,
            })
            raw_rows.append({
                "request_id": row["request_id"], "anon_id": row["anon_id"], "reasoning": row["reasoning"],
                "generation_id": rec.get("generation_id"), "response": parsed,
            })
            succeeded = True
            break

        if not succeeded:
            final_rows.append({
                "ordinal": index, "request_id": row["request_id"], "reasoning": row["reasoning"],
                "schema_valid": False, "attempts": final_attempt, "error": last_error,
            })
        if index % 10 == 0:
            print(json.dumps({"pilot_progress": index, "valid": sum(1 for r in final_rows if r.get("schema_valid"))}), flush=True)

    outdir = workdir / "pilot_output"
    outdir.mkdir(parents=True, exist_ok=True)
    encrypt_raw(raw_rows, outdir / "raw_results.enc.b64", key)
    valid = [r for r in final_rows if r.get("schema_valid")]
    failures = [r for r in final_rows if not r.get("schema_valid")]
    received = [r for r in attempts if r.get("response_received")]
    known_costs = [float(r["cost_usd"]) for r in received if r.get("cost_usd") is not None]
    condition_valid = {c: sum(1 for r in valid if r["reasoning"] == c) for c in ("off", "low", "medium")}
    summary = {
        "pilot_type": "engineering_pilot_fullscan",
        "respondents_requested": n_respondents,
        "requests_planned": n_respondents * 3,
        "requests_schema_valid": len(valid),
        "failures": len(failures),
        "parse_failures": parse_failures,
        "all_schema_valid": len(valid) == n_respondents * 3 and not failures and parse_failures == 0,
        "condition_valid_counts": condition_valid,
        "max_attempts_per_request": max_attempts,
        "total_attempts_sent": len(attempts),
        "retry_count": max(0, len(attempts) - n_respondents * 3),
        "spend_cap_usd": spend_cap,
        "worst_case_all_attempts_provider_ceiling_projection_usd": round(ceiling_projection, 6),
        "known_realized_cost_usd": round(sum(known_costs), 8) if known_costs else None,
        "prompt_tokens_all_responses": sum(int(r.get("prompt_tokens") or 0) for r in received),
        "completion_tokens_all_responses": sum(int(r.get("completion_tokens") or 0) for r in received),
        "reasoning_tokens_all_responses": sum(int(r.get("reasoning_tokens") or 0) for r in received),
        "finish_reasons": sorted({str(r.get("finish_reason")) for r in received if r.get("finish_reason") is not None}),
        "providers": sorted({str(r.get("provider_name")) for r in received if r.get("provider_name")}),
        "provider_order": cfg["run_policy"].get("provider_order") or [],
        "allow_provider_fallbacks": bool(cfg["run_policy"]["allow_provider_fallbacks"]),
        "models_returned": sorted({str(r.get("model_returned")) for r in received if r.get("model_returned")}),
        "freeze_requests_sha256": freeze_manifest["hashes"]["requests_jsonl_sha256"],
        "freeze_request_id_set_sha256": freeze_manifest["hashes"]["request_id_set_sha256"],
        "human_truth_loaded_for_scoring": False,
        "substantive_outputs_inspected": False,
        "raw_results_storage": "AES-GCM encrypted artifact only",
    }
    (outdir / "engineering_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "engineering_requests.json").write_text(json.dumps(final_rows, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "attempt_history.json").write_text(json.dumps(attempts, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    if not summary["all_schema_valid"]:
        raise SystemExit(2)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--respondents", type=int, default=20)
    ap.add_argument("--spend-cap", type=float, default=0.47)
    ap.add_argument("--workdir", default="/tmp/rpf_pilot20")
    args = ap.parse_args()
    run(args.respondents, args.spend_cap, Path(args.workdir))


if __name__ == "__main__":
    main()
