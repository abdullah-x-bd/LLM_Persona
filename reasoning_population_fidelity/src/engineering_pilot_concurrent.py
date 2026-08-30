from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paid_pilot import CONFIG, PILOT_CONFIG, SCHEMA, encrypt_raw, load_json, projected_ceiling_cost, reconstruct_and_verify, select_pilot
from production_study1 import normalize_attempt_result, one_attempt


def run(n_respondents: int, spend_cap: float, workdir: Path) -> dict:
    if os.getenv("RPF_ENABLE_PILOT") != "YES_I_ACCEPT_PILOT_COST":
        raise RuntimeError("Engineering pilot authorization environment variable is missing")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    cfg = load_json(CONFIG)
    pilot_cfg = load_json(PILOT_CONFIG)
    schema = load_json(SCHEMA)
    if n_respondents != int(pilot_cfg["full_pilot_respondents"]):
        raise RuntimeError("Concurrent engineering gate is restricted to the frozen 20 respondent pilot")

    rows, freeze_manifest = reconstruct_and_verify(workdir)
    selected = select_pilot(rows, n_respondents, pilot_cfg["selection_seed_label"])
    max_attempts = int(pilot_cfg["max_attempts_per_request"])
    ceiling_projection = projected_ceiling_cost(selected, cfg, max_attempts)
    if ceiling_projection > spend_cap:
        raise RuntimeError(f"Pilot worst-case projection {ceiling_projection:.6f} exceeds cap {spend_cap:.6f}")

    reasoning_exclude = bool(pilot_cfg["reasoning_exclude_from_response"])
    concurrency = int(cfg["run_policy"].get("concurrency") or 1)
    concurrency = max(1, min(8, concurrency))
    row_by_id = {r["request_id"]: r for r in selected}
    ordinal_by_id = {r["request_id"]: i for i, r in enumerate(selected, start=1)}
    attempts: list[dict] = []
    successes: dict[str, dict] = {}
    raw: dict[str, dict] = {}

    pending = [r["request_id"] for r in selected]
    for attempt_no in range(1, max_attempts + 1):
        if not pending:
            break
        current = list(pending)
        pending = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            fmap = {
                pool.submit(
                    one_attempt,
                    row_by_id[rid], cfg, schema, reasoning_exclude, key,
                    ordinal_by_id[rid], attempt_no,
                ): rid
                for rid in current
            }
            for future in concurrent.futures.as_completed(fmap):
                rid = fmap[future]
                row = row_by_id[rid]
                try:
                    result = future.result()
                    rec, parsed = normalize_attempt_result(result)
                except Exception as exc:
                    rec = {
                        "ordinal": ordinal_by_id[rid], "request_id": rid, "anon_id": row["anon_id"],
                        "reasoning": row["reasoning"], "attempt": attempt_no,
                        "response_received": False, "schema_valid": False,
                        "error": f"worker:{type(exc).__name__}:{str(exc)[:220]}",
                    }
                    parsed = None
                attempts.append(rec)
                if rec.get("schema_valid") and parsed is not None:
                    successes[rid] = {
                        "ordinal": rec["ordinal"], "request_id": rid, "reasoning": row["reasoning"],
                        "generation_id": rec.get("generation_id"), "provider_name": rec.get("provider_name"),
                        "model_returned": rec.get("model_returned"), "finish_reason": rec.get("finish_reason"),
                        "prompt_tokens": rec.get("prompt_tokens", 0), "completion_tokens": rec.get("completion_tokens", 0),
                        "reasoning_tokens": rec.get("reasoning_tokens", 0), "cost_usd": rec.get("cost_usd"),
                        "latency_seconds": rec.get("latency_seconds"), "schema_valid": True, "attempts": attempt_no,
                    }
                    raw[rid] = {
                        "request_id": rid, "anon_id": row["anon_id"], "reasoning": row["reasoning"],
                        "generation_id": rec.get("generation_id"), "response": parsed,
                    }
                else:
                    pending.append(rid)
        print(json.dumps({
            "attempt_round": attempt_no,
            "schema_valid": len(successes),
            "remaining": len(pending),
            "attempts_sent": len(attempts),
        }, sort_keys=True), flush=True)

    outdir = workdir / "pilot_output"
    outdir.mkdir(parents=True, exist_ok=True)
    attempt_sorted = sorted(attempts, key=lambda r: (int(r["ordinal"]), int(r.get("attempt") or 0)))
    success_sorted = sorted(successes.values(), key=lambda r: int(r["ordinal"]))
    raw_sorted = [raw[r["request_id"]] for r in success_sorted]
    encrypt_raw(raw_sorted, outdir / "raw_results.enc.b64", key)

    received = [a for a in attempts if a.get("response_received")]
    known_costs = [float(a["cost_usd"]) for a in received if a.get("cost_usd") is not None]
    parse_failures = sum(1 for a in attempts if str(a.get("error", "")).startswith("schema_or_json:"))
    condition_valid = {c: sum(1 for r in successes.values() if r["reasoning"] == c) for c in ("off", "low", "medium")}
    summary = {
        "pilot_type": "engineering_pilot_concurrent",
        "respondents_requested": n_respondents,
        "requests_planned": n_respondents * 3,
        "requests_schema_valid": len(successes),
        "failures": len(pending),
        "parse_failures": parse_failures,
        "all_schema_valid": len(successes) == n_respondents * 3 and not pending,
        "condition_valid_counts": condition_valid,
        "concurrency": concurrency,
        "max_attempts_per_request": max_attempts,
        "total_attempts_sent": len(attempts),
        "retry_count": max(0, len(attempts) - n_respondents * 3),
        "spend_cap_usd": spend_cap,
        "worst_case_all_attempts_provider_ceiling_projection_usd": round(ceiling_projection, 6),
        "known_realized_cost_usd": round(sum(known_costs), 8) if known_costs else None,
        "prompt_tokens_all_responses": sum(int(a.get("prompt_tokens") or 0) for a in received),
        "completion_tokens_all_responses": sum(int(a.get("completion_tokens") or 0) for a in received),
        "reasoning_tokens_all_responses": sum(int(a.get("reasoning_tokens") or 0) for a in received),
        "finish_reasons": sorted({str(a.get("finish_reason")) for a in received if a.get("finish_reason") is not None}),
        "providers": sorted({str(a.get("provider_name")) for a in received if a.get("provider_name")}),
        "models_returned": sorted({str(a.get("model_returned")) for a in received if a.get("model_returned")}),
        "provider_order": cfg["run_policy"].get("provider_order") or [],
        "allow_provider_fallbacks": bool(cfg["run_policy"]["allow_provider_fallbacks"]),
        "freeze_requests_sha256": freeze_manifest["hashes"]["requests_jsonl_sha256"],
        "freeze_request_id_set_sha256": freeze_manifest["hashes"]["request_id_set_sha256"],
        "human_truth_loaded_for_scoring": False,
        "substantive_outputs_inspected": False,
        "raw_results_storage": "AES-GCM encrypted artifact only",
    }
    (outdir / "engineering_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "engineering_requests.json").write_text(json.dumps(success_sorted, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "attempt_history.json").write_text(json.dumps(attempt_sorted, indent=2, sort_keys=True), encoding="utf-8")
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
