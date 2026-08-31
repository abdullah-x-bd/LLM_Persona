from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for p in (HERE, ROOT / "reasoning_population_fidelity" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from openrouter_preflight import choose_endpoint, get_json, BASE
from paid_runner import one, encrypt_rows
from suite_core import (
    SCHEMA,
    build_requests,
    build_cams_prompt,
    build_plfs_prompt,
    cams_persona,
    cams_rows,
    load_registry,
    plfs_persona,
    plfs_rows,
    stable_select,
)

STUDIES = [
    "S01_second_model_reasoning",
    "S02_length_safe_reasoning",
    "S03_persona_reasoning_factorial",
    "S04_plfs_reasoning_replication",
    "S05_fresh_holdout_confirmation",
]
PILOT_RESPONDENTS = 2
GLOBAL_HARD_CAP_USD = 0.15
CONCURRENCY = 8


def proxy_requests(study_id: str, n: int) -> list[dict]:
    """Build engineering-only requests for blocked studies without reading truth.

    S04 uses existing PLFS persona-code rows. S05 uses existing CAMS rows as a
    plumbing proxy for the not-yet-created fresh holdout. Returned rows are
    explicitly tagged and can never be passed off as scientific observations.
    """
    reg = load_registry()
    study = reg["studies"][study_id]
    if study_id == "S04_plfs_reasoning_replication":
        base = stable_select(plfs_rows(), n, 9910401)
        persona_fn = lambda r, c: plfs_persona(r)
        prompt_fn = build_plfs_prompt
        proxy_source = "existing_plfs_codes_engineering_only"
    elif study_id == "S05_fresh_holdout_confirmation":
        base = stable_select(cams_rows(), n, 9910501)
        persona_fn = lambda r, c: cams_persona(r, c)
        prompt_fn = build_cams_prompt
        proxy_source = "existing_cams_codes_not_holdout_engineering_only"
    else:
        raise ValueError(study_id)

    out = []
    schema_hash = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    for raw in base:
        for arm in study["arms"]:
            persona = persona_fn(raw, arm["persona"])
            prompt = prompt_fn(persona)
            row = {
                "study_id": study_id,
                "anon_id": raw["anon_id"],
                "arm_id": arm["id"],
                "persona_condition": arm["persona"],
                "model_key": arm["model"],
                "model": reg["models"][arm["model"]]["id"],
                "reasoning": arm["reasoning"],
                "max_completion_tokens": int(arm["max_completion_tokens"]),
                "prompt": prompt,
                "schema_sha256": schema_hash,
                "engineering_proxy": True,
                "proxy_source": proxy_source,
            }
            rid_payload = {
                "engineering_micropilot": 1,
                "study_id": study_id,
                "anon_id": raw["anon_id"],
                "arm_id": arm["id"],
                "model": row["model"],
                "reasoning": row["reasoning"],
                "max_completion_tokens": row["max_completion_tokens"],
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "schema_sha256": schema_hash,
            }
            row["request_id"] = hashlib.sha256(json.dumps(rid_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            out.append(row)
    return out


def real_pilot_requests(study_id: str, n: int) -> list[dict]:
    rows = build_requests(study_id)
    ids = sorted({r["anon_id"] for r in rows}, key=lambda x: hashlib.sha256(f"micropilot-v1|{study_id}|{x}".encode()).hexdigest())[:n]
    keep = set(ids)
    selected = [dict(r, engineering_proxy=False) for r in rows if r["anon_id"] in keep]
    expected = n * len(load_registry()["studies"][study_id]["arms"])
    if len(selected) != expected:
        raise AssertionError((study_id, len(selected), expected))
    return selected


def ceiling(row: dict, ep: dict) -> float:
    prompt_tokens = max(1, (len(row["prompt"]) + 2) // 3)
    return prompt_tokens / 1e6 * float(ep["input_per_m"]) + int(row["max_completion_tokens"]) / 1e6 * float(ep["output_per_m"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="/tmp/followup_micropilot")
    ap.add_argument("--hard-cap", type=float, default=GLOBAL_HARD_CAP_USD)
    args = ap.parse_args()
    if os.getenv("ENABLE_ENGINEERING_MICROPILOT") != "YES_ENGINEERING_ONLY":
        raise RuntimeError("Engineering micropilot authorization missing")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    if args.hard_cap > GLOBAL_HARD_CAP_USD + 1e-12:
        raise RuntimeError("Micropilot cap may not exceed $0.15")

    reg = load_registry()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    all_rows = []
    for sid in STUDIES:
        if sid in {"S04_plfs_reasoning_replication", "S05_fresh_holdout_confirmation"}:
            rows = proxy_requests(sid, PILOT_RESPONDENTS)
        else:
            rows = real_pilot_requests(sid, PILOT_RESPONDENTS)
        all_rows.extend(rows)

    if len(all_rows) != 24:
        raise AssertionError(f"Expected 24 total engineering calls, found {len(all_rows)}")
    if len({r["request_id"] for r in all_rows}) != 24:
        raise AssertionError("Duplicate micropilot request IDs")

    provider_name = reg["privacy"]["provider_name"]
    model_keys = sorted({r["model_key"] for r in all_rows})
    eps = {mk: choose_endpoint(reg["models"][mk]["id"], key, provider_name) for mk in model_keys}
    for mk, ep in eps.items():
        params = set(ep.get("supported_parameters") or [])
        required = {"max_tokens", "response_format"}
        if not required.issubset(params):
            raise RuntimeError(f"{mk} endpoint missing {sorted(required-params)}")
        if any(r["model_key"] == mk and r["reasoning"] != "off" for r in all_rows) and "reasoning" not in params:
            raise RuntimeError(f"{mk} endpoint lacks reasoning")
        if ep.get("status") not in (None, 0):
            raise RuntimeError(f"Endpoint unhealthy before pilot: {mk} {ep.get('status')}")

    hard_ceiling = sum(ceiling(r, eps[r["model_key"]]) for r in all_rows)
    if hard_ceiling > args.hard_cap + 1e-12:
        raise RuntimeError(f"24-call hard ceiling ${hard_ceiling:.6f} exceeds pilot cap ${args.hard_cap:.6f}")

    print(json.dumps({
        "status": "ENGINEERING_MICROPILOT_START",
        "scientific_data": False,
        "substantive_outputs_to_inspect": False,
        "studies": STUDIES,
        "respondents_per_study": PILOT_RESPONDENTS,
        "requests": len(all_rows),
        "concurrency": CONCURRENCY,
        "provider": provider_name,
        "endpoints": {k: {"tag": v["tag"], "name": v["name"], "input_per_m": v["input_per_m"], "output_per_m": v["output_per_m"]} for k, v in eps.items()},
        "hard_ceiling_usd": round(hard_ceiling, 6),
        "hard_cap_usd": args.hard_cap,
        "truth_loaded": False,
    }, indent=2, sort_keys=True))

    attempts = []
    valid = {}
    raw = {}
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        future_map = {pool.submit(one, r, schema, eps[r["model_key"]], key, 1): r for r in all_rows}
        for fut in concurrent.futures.as_completed(future_map):
            row = future_map[fut]
            rec, parsed = fut.result()
            rec["study_id"] = row["study_id"]
            rec["engineering_proxy"] = bool(row.get("engineering_proxy"))
            attempts.append(rec)
            if parsed is not None:
                valid[row["request_id"]] = rec
                raw[row["request_id"]] = {
                    "request_id": row["request_id"],
                    "study_id": row["study_id"],
                    "anon_id": row["anon_id"],
                    "arm_id": row["arm_id"],
                    "engineering_proxy": bool(row.get("engineering_proxy")),
                    "response": parsed,
                }

    # One bounded sequential retry for any failures. This tests retry plumbing without creating a retry storm.
    missing = [r for r in all_rows if r["request_id"] not in valid]
    for row in missing:
        spent = sum(float(a.get("accounted_upper_bound_usd") or 0) for a in attempts)
        c = ceiling(row, eps[row["model_key"]])
        if spent + c > args.hard_cap + 1e-12:
            break
        rec, parsed = one(row, schema, eps[row["model_key"]], key, 2)
        rec["study_id"] = row["study_id"]
        rec["engineering_proxy"] = bool(row.get("engineering_proxy"))
        attempts.append(rec)
        if parsed is not None:
            valid[row["request_id"]] = rec
            raw[row["request_id"]] = {
                "request_id": row["request_id"],
                "study_id": row["study_id"],
                "anon_id": row["anon_id"],
                "arm_id": row["arm_id"],
                "engineering_proxy": bool(row.get("engineering_proxy")),
                "response": parsed,
            }

    by_study = {}
    by_arm = defaultdict(lambda: {"planned": 0, "valid": 0, "attempts": 0, "length_finishes": 0, "latencies": [], "reasoning_tokens": [], "completion_tokens": [], "known_costs": []})
    for row in all_rows:
        by_arm[(row["study_id"], row["arm_id"])]["planned"] += 1
    for a in attempts:
        key2 = (a["study_id"], a["arm_id"])
        x = by_arm[key2]
        x["attempts"] += 1
        if a.get("finish_reason") == "length": x["length_finishes"] += 1
        if a.get("latency_seconds") is not None: x["latencies"].append(float(a["latency_seconds"]))
        if a.get("reasoning_tokens") is not None: x["reasoning_tokens"].append(int(a.get("reasoning_tokens") or 0))
        if a.get("completion_tokens") is not None: x["completion_tokens"].append(int(a.get("completion_tokens") or 0))
        if a.get("cost_usd") is not None: x["known_costs"].append(float(a["cost_usd"]))
    for rid, rec in valid.items():
        by_arm[(rec["study_id"], rec["arm_id"])]["valid"] += 1

    for sid in STUDIES:
        arms = {}
        for arm in reg["studies"][sid]["arms"]:
            x = by_arm[(sid, arm["id"])]
            arms[arm["id"]] = {
                "planned": x["planned"],
                "valid": x["valid"],
                "attempts": x["attempts"],
                "length_finishes": x["length_finishes"],
                "max_latency_seconds": round(max(x["latencies"]), 4) if x["latencies"] else None,
                "mean_latency_seconds": round(sum(x["latencies"]) / len(x["latencies"]), 4) if x["latencies"] else None,
                "max_reasoning_tokens": max(x["reasoning_tokens"]) if x["reasoning_tokens"] else 0,
                "max_completion_tokens_realized": max(x["completion_tokens"]) if x["completion_tokens"] else 0,
                "known_cost_usd": round(sum(x["known_costs"]), 8),
            }
        by_study[sid] = {
            "engineering_proxy": sid in {"S04_plfs_reasoning_replication", "S05_fresh_holdout_confirmation"},
            "arms": arms,
            "all_valid": all(v["valid"] == v["planned"] for v in arms.values()),
        }

    accounted = sum(float(a.get("accounted_upper_bound_usd") or 0) for a in attempts)
    known = sum(float(a.get("cost_usd") or 0) for a in attempts if a.get("cost_usd") is not None)
    unresolved = len(all_rows) - len(valid)
    summary = {
        "status": "PASS" if unresolved == 0 else "FAIL",
        "scientific_data": False,
        "truth_loaded": False,
        "substantive_outputs_inspected": False,
        "requests_planned": len(all_rows),
        "schema_valid": len(valid),
        "unresolved": unresolved,
        "attempts": len(attempts),
        "wall_seconds": round(time.perf_counter() - started, 4),
        "concurrency": CONCURRENCY,
        "hard_ceiling_usd": round(hard_ceiling, 6),
        "hard_cap_usd": args.hard_cap,
        "known_realized_cost_usd": round(known, 8),
        "accounted_upper_bound_usd": round(accounted, 8),
        "provider": provider_name,
        "endpoint_tags": {k: v["tag"] for k, v in eps.items()},
        "allow_fallbacks": False,
        "data_collection": "deny",
        "by_study": by_study,
    }

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "attempts.json").write_text(json.dumps(sorted(attempts, key=lambda x: (x["study_id"], x["request_id"], x["attempt"])), indent=2, sort_keys=True), encoding="utf-8")
    encrypt_rows([raw[k] for k in sorted(raw)], outdir / "raw_results.enc.b64", key, "ENGINEERING_MICROPILOT_V1")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if unresolved:
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
