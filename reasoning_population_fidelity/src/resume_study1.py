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
import urllib.request
from collections import defaultdict
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paid_pilot import load_json, reconstruct_and_verify
from production_study1 import (
    AAD,
    CONFIG,
    PILOT_CONFIG,
    SCHEMA,
    encrypt_raw,
    normalize_attempt_result,
    one_attempt,
    request_ceiling_cost,
)

CONDITIONS = ("off", "low", "medium")
EXPECTED_FREEZE = "120cc6bef15e7b2eb8fb2c49c7efa2fab5496b0a429cf34c8d9100b588cf9293"
HISTORICAL_RUN_ID = 33310439944


def decrypt_seed_raw(path: Path, api_key: str) -> list[dict]:
    blob = base64.b64decode(path.read_text(encoding="ascii"))
    if len(blob) < 13:
        raise RuntimeError("Seed raw-results artifact is malformed")
    nonce, ciphertext = blob[:12], blob[12:]
    aes_key = hashlib.sha256(AAD + b"|" + api_key.encode()).digest()
    compressed = AESGCM(aes_key).decrypt(nonce, ciphertext, AAD)
    plaintext = gzip.decompress(compressed).decode("utf-8")
    return [json.loads(line) for line in plaintext.splitlines() if line.strip()]


def remaining_credit_usd(api_key: str) -> float:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/credits",
        headers={"Authorization": "Bearer " + api_key},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode())
    data = payload.get("data") or {}
    total = data.get("total_credits")
    usage = data.get("total_usage")
    if not isinstance(total, (int, float)) or not isinstance(usage, (int, float)):
        raise RuntimeError("OpenRouter /credits did not expose numeric total_credits and total_usage")
    return float(total) - float(usage)


def is_definite_zero_cost_rejection(record: dict) -> bool:
    error = str(record.get("error") or "")
    return (not record.get("response_received")) and "402:" in error


def realized_or_guard_cost(record: dict) -> float:
    cost = record.get("cost_usd")
    if isinstance(cost, (int, float)):
        return float(cost)
    if is_definite_zero_cost_rejection(record):
        return 0.0
    return float(record.get("request_ceiling_usd") or 0.0)


def historical_effective_costs(attempts: list[dict], successes: list[dict]) -> dict[str, float]:
    success_counts = {c: sum(1 for r in successes if r.get("reasoning") == c) for c in CONDITIONS}
    known_costs = defaultdict(float)
    for a in attempts:
        if a.get("reasoning") in CONDITIONS and isinstance(a.get("cost_usd"), (int, float)):
            known_costs[a["reasoning"]] += float(a["cost_usd"])
    out = {}
    for c in CONDITIONS:
        if success_counts[c] <= 0:
            raise RuntimeError(f"No historical successes for treatment {c}")
        out[c] = known_costs[c] / success_counts[c]
    return out


def load_seed(seed_dir: Path, api_key: str) -> tuple[list[dict], list[dict], dict[str, dict], dict]:
    summary = json.loads((seed_dir / "study1_summary.json").read_text(encoding="utf-8"))
    if summary.get("freeze_requests_sha256") != EXPECTED_FREEZE:
        raise RuntimeError("Seed artifact freeze hash does not match frozen Study 1")
    if summary.get("requests_schema_valid") != 963:
        raise RuntimeError("Seed artifact does not contain the expected 963 valid requests")
    successes = json.loads((seed_dir / "production_requests.json").read_text(encoding="utf-8"))
    attempts = json.loads((seed_dir / "attempt_history.json").read_text(encoding="utf-8"))
    raw_rows = decrypt_seed_raw(seed_dir / "raw_results.enc.b64", api_key)
    raw = {r["request_id"]: r for r in raw_rows}
    success_ids = {r["request_id"] for r in successes}
    if len(successes) != 963 or len(success_ids) != 963 or set(raw) != success_ids:
        raise RuntimeError("Seed metadata/raw result ID sets are inconsistent")
    return attempts, successes, raw, summary


def build_success_record(rec: dict, row: dict, attempt_no: int) -> dict:
    return {
        "ordinal": rec["ordinal"],
        "request_id": row["request_id"],
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


def aggregate_summary(attempts: list[dict], successes: dict[str, dict], historical_cost: float, current_run_cost: float, current_credit_start: float, expected_remaining: float) -> dict:
    condition_counts = {c: sum(1 for r in successes.values() if r["reasoning"] == c) for c in CONDITIONS}
    remaining = 3000 - len(successes)
    return {
        "study": "CAMS reasoning population fidelity Study 1 resumed",
        "historical_run_id": HISTORICAL_RUN_ID,
        "freeze_requests_sha256": EXPECTED_FREEZE,
        "requests_planned": 3000,
        "requests_schema_valid": len(successes),
        "remaining_failures": remaining,
        "condition_valid_counts": condition_counts,
        "all_schema_valid": remaining == 0 and condition_counts == {"off": 1000, "low": 1000, "medium": 1000},
        "historical_realized_cost_usd": round(historical_cost, 8),
        "resume_realized_or_guard_cost_usd": round(current_run_cost, 8),
        "combined_realized_or_guard_cost_usd": round(historical_cost + current_run_cost, 8),
        "account_credit_at_resume_start_usd": round(current_credit_start, 8),
        "preflight_expected_remaining_cost_usd": round(expected_remaining, 8),
        "total_attempt_records": len(attempts),
        "provider_order": ["akashml/fp8"],
        "allow_provider_fallbacks": False,
        "provider_data_collection": "deny",
        "human_truth_loaded_for_scoring": False,
        "substantive_outputs_inspected_during_run": False,
        "raw_results_storage": "AES-GCM encrypted artifact only",
    }


def write_resume_checkpoint(outdir: Path, attempts: list[dict], successes: dict[str, dict], raw: dict[str, dict], api_key: str, summary: dict) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    attempt_sorted = sorted(attempts, key=lambda r: (int(r.get("ordinal") or 0), int(r.get("attempt") or 0)))
    success_sorted = sorted(successes.values(), key=lambda r: int(r["ordinal"]))
    raw_sorted = [raw[r["request_id"]] for r in success_sorted]
    (outdir / "attempt_history.json").write_text(json.dumps(attempt_sorted, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "production_requests.json").write_text(json.dumps(success_sorted, indent=2, sort_keys=True), encoding="utf-8")
    encrypt_raw(raw_sorted, outdir / "raw_results.enc.b64", api_key)
    (outdir / "study1_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "progress.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def run(seed_dir: Path, workdir: Path, preflight_only: bool) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    if not preflight_only and os.getenv("RPF_ENABLE_STUDY1_RESUME") != "YES_I_ACCEPT_STUDY1_RESUME_COST":
        raise RuntimeError("Study 1 resume authorization environment variable is missing")

    cfg = load_json(CONFIG)
    pilot_cfg = load_json(PILOT_CONFIG)
    schema = load_json(SCHEMA)
    rows, freeze_manifest = reconstruct_and_verify(workdir)
    if freeze_manifest["hashes"]["requests_jsonl_sha256"] != EXPECTED_FREEZE:
        raise RuntimeError("Reconstructed request set does not match frozen Study 1")
    if len(rows) != 3000:
        raise RuntimeError("Reconstructed Study 1 request count is not 3000")

    attempts, seed_successes, raw, seed_summary = load_seed(seed_dir, api_key)
    successes = {r["request_id"]: r for r in seed_successes}
    row_by_id = {r["request_id"]: r for r in rows}
    if not set(successes).issubset(row_by_id):
        raise RuntimeError("Seed successes are not a subset of the frozen request IDs")

    missing = [r for r in rows if r["request_id"] not in successes]
    missing_counts = {c: sum(1 for r in missing if r["reasoning"] == c) for c in CONDITIONS}
    if missing_counts != {"off": 379, "low": 833, "medium": 825}:
        raise RuntimeError(f"Unexpected missing-treatment counts: {missing_counts}")

    historical_cost = float(seed_summary["known_realized_cost_usd"])
    study_cap = float(cfg["study_1"]["study_budget_cap_usd"])
    remaining_study_budget = study_cap - historical_cost
    effective = historical_effective_costs(attempts, seed_successes)
    expected_remaining = sum(missing_counts[c] * effective[c] for c in CONDITIONS)
    required_credit = min(remaining_study_budget, expected_remaining * 1.04)
    credit = remaining_credit_usd(api_key)

    preflight = {
        "status": "RESUME_PREFLIGHT_PASS" if credit + 1e-12 >= required_credit else "RESUME_PREFLIGHT_BLOCKED_LOW_CREDIT",
        "freeze_requests_sha256": EXPECTED_FREEZE,
        "seed_valid_requests": len(successes),
        "missing_requests": len(missing),
        "missing_condition_counts": missing_counts,
        "historical_realized_cost_usd": round(historical_cost, 8),
        "remaining_study_budget_usd": round(remaining_study_budget, 8),
        "historical_effective_cost_per_success_usd": {k: round(v, 8) for k, v in effective.items()},
        "expected_remaining_cost_usd": round(expected_remaining, 8),
        "required_account_credit_usd": round(required_credit, 8),
        "current_account_credit_usd": round(credit, 8),
        "additional_credit_needed_usd": round(max(0.0, required_credit - credit), 8),
        "resume_concurrency": 2,
        "inference_endpoint_called": False,
    }
    print(json.dumps(preflight, indent=2, sort_keys=True), flush=True)
    if preflight_only:
        return preflight
    if credit + 1e-12 < required_credit:
        raise RuntimeError("Insufficient account credit for a clean resume; no inference was sent")

    concurrency = 2
    reasoning_exclude = bool(pilot_cfg.get("reasoning_exclude_from_response", True))
    max_attempts = max(1, min(3, int(cfg["run_policy"].get("max_retries") or 1)))
    outdir = workdir / "study1_resume_output"
    new_cost = 0.0

    # Preserve frozen ordinal identity from the original request order.
    ordinal_by_id = {r["request_id"]: i for i, r in enumerate(rows, start=1)}
    for r in missing:
        r["_ordinal"] = ordinal_by_id[r["request_id"]]

    # Interleave by original frozen order. Run two at a time to avoid OpenRouter credit reservation spikes.
    pending = list(missing)
    for attempt_no in range(1, max_attempts + 1):
        if not pending:
            break
        next_pending: list[dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            future_map = {}
            for row in pending:
                ceiling = request_ceiling_cost(row, cfg)
                if historical_cost + new_cost + ceiling > study_cap + 1e-12:
                    next_pending.append(row)
                    continue
                fut = pool.submit(one_attempt, row, cfg, schema, reasoning_exclude, api_key, row["_ordinal"], attempt_no)
                future_map[fut] = row
            completed = 0
            for fut in concurrent.futures.as_completed(future_map):
                row = future_map[fut]
                try:
                    result = fut.result()
                except Exception as exc:
                    result = {
                        "ordinal": row["_ordinal"],
                        "request_id": row["request_id"],
                        "anon_id": row["anon_id"],
                        "reasoning": row["reasoning"],
                        "attempt": attempt_no,
                        "response_received": False,
                        "schema_valid": False,
                        "error": f"worker:{type(exc).__name__}:{str(exc)[:220]}",
                        "cost_usd": None,
                        "request_ceiling_usd": request_ceiling_cost(row, cfg),
                    }
                rec, parsed = normalize_attempt_result(result)
                attempts.append(rec)
                new_cost += realized_or_guard_cost(rec)
                if rec.get("schema_valid") and parsed is not None:
                    rid = row["request_id"]
                    successes[rid] = build_success_record(rec, row, attempt_no)
                    raw[rid] = {
                        "request_id": rid,
                        "anon_id": row["anon_id"],
                        "reasoning": row["reasoning"],
                        "generation_id": rec.get("generation_id"),
                        "response": parsed,
                    }
                else:
                    next_pending.append(row)
                completed += 1
                if completed % 50 == 0 or completed == len(future_map):
                    print(json.dumps({
                        "phase": f"resume_attempt_{attempt_no}",
                        "attempted_this_phase": completed,
                        "total_schema_valid": len(successes),
                        "remaining_after_current_results": 3000 - len(successes),
                        "combined_realized_or_guard_cost_usd": round(historical_cost + new_cost, 6),
                    }, sort_keys=True), flush=True)
        pending = [r for r in next_pending if r["request_id"] not in successes]
        summary = aggregate_summary(attempts, successes, historical_cost, new_cost, credit, expected_remaining)
        write_resume_checkpoint(outdir, attempts, successes, raw, api_key, summary)

    summary = aggregate_summary(attempts, successes, historical_cost, new_cost, credit, expected_remaining)
    write_resume_checkpoint(outdir, attempts, successes, raw, api_key, summary)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    if not summary["all_schema_valid"]:
        raise SystemExit(2)
    if summary["combined_realized_or_guard_cost_usd"] > study_cap + 1e-12:
        raise SystemExit(3)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-dir", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    run(args.seed_dir, args.workdir, args.preflight_only)


if __name__ == "__main__":
    main()
