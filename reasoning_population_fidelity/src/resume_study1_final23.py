from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import resume_study1 as rs

FROZEN_STUDY_CAP_USD = 7.80
PRIOR_RECOVERY_CAP_USD = 8.50
FINAL_RECOVERY_CAP_USD = 8.75
PROJECT_HARD_CAP_USD = 9.50
EXPECTED_SEED_VALID = 2977
EXPECTED_MISSING = 23
EXPECTED_SEED_COUNTS = {"off": 1000, "low": 982, "medium": 995}


def patched_load_json(path):
    cfg = ORIGINAL_LOAD_JSON(path)
    if Path(path) == Path(rs.CONFIG):
        cfg = copy.deepcopy(cfg)
        frozen = float(cfg["study_1"]["study_budget_cap_usd"])
        project_cap = float(cfg["hard_spend_cap_usd"])
        if abs(frozen - FROZEN_STUDY_CAP_USD) > 1e-9:
            raise RuntimeError(f"Unexpected frozen Study 1 cap: {frozen}")
        if abs(project_cap - PROJECT_HARD_CAP_USD) > 1e-9:
            raise RuntimeError(f"Unexpected project hard cap: {project_cap}")
        if not (PRIOR_RECOVERY_CAP_USD < FINAL_RECOVERY_CAP_USD <= project_cap):
            raise RuntimeError("Final recovery cap must exceed prior recovery cap and remain within project hard cap")
        cfg["study_1"]["study_budget_cap_usd"] = FINAL_RECOVERY_CAP_USD
    return cfg


ORIGINAL_LOAD_JSON = rs.load_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-dir", required=True, type=Path)
    ap.add_argument("--workdir", required=True, type=Path)
    args = ap.parse_args()

    seed_summary = json.loads((args.seed_dir / "study1_summary.json").read_text(encoding="utf-8"))
    if seed_summary.get("requests_schema_valid") != EXPECTED_SEED_VALID:
        raise RuntimeError(f"Expected {EXPECTED_SEED_VALID} seed successes, got {seed_summary.get('requests_schema_valid')}")
    if seed_summary.get("remaining_failures") != EXPECTED_MISSING:
        raise RuntimeError(f"Expected {EXPECTED_MISSING} missing requests, got {seed_summary.get('remaining_failures')}")
    if seed_summary.get("condition_valid_counts") != EXPECTED_SEED_COUNTS:
        raise RuntimeError(f"Unexpected seed condition counts: {seed_summary.get('condition_valid_counts')}")

    # Final operational completion pass only. Scientific treatment and generation
    # settings remain frozen. Lower concurrency/batch size is an infrastructure
    # reliability change intended to avoid the provider failures seen previously.
    rs.load_json = patched_load_json
    rs.RESUME_CONCURRENCY = 2
    rs.BATCH_SIZE = 6

    note = {
        "status": "POST_INTERIM_FINAL23_OPERATIONAL_COMPLETION_RECOVERY",
        "reason": "The prior completion recovery preserved 2977/3000 valid frozen Study 1 requests, leaving only 23 transient/schema failures.",
        "seed_valid_requests": EXPECTED_SEED_VALID,
        "missing_requests_at_start": EXPECTED_MISSING,
        "missing_condition_counts_at_start": {"off": 0, "low": 18, "medium": 5},
        "frozen_study_budget_cap_usd": FROZEN_STUDY_CAP_USD,
        "prior_operational_recovery_cap_usd": PRIOR_RECOVERY_CAP_USD,
        "final_operational_recovery_cap_usd": FINAL_RECOVERY_CAP_USD,
        "project_hard_spend_cap_usd": PROJECT_HARD_CAP_USD,
        "changes_to_scientific_design": False,
        "treatment_or_generation_settings_changed": False,
        "analysis_plan_changed": False,
        "provider_changed": False,
        "prompt_or_schema_changed": False,
        "operational_concurrency_changed": True,
        "resume_concurrency": rs.RESUME_CONCURRENCY,
        "resume_batch_size": rs.BATCH_SIZE,
        "interim_outcomes_seen_before_recovery": True,
        "purpose": "Collect only the 23 missing request IDs from the existing frozen 3000-request Study 1 set.",
    }
    print(json.dumps(note, indent=2, sort_keys=True), flush=True)

    outdir = args.workdir / "study1_resume_output"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "final23_recovery_note.json").write_text(json.dumps(note, indent=2, sort_keys=True), encoding="utf-8")

    try:
        result = rs.run(args.seed_dir, args.workdir, False)
    finally:
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "final23_recovery_note.json").write_text(json.dumps(note, indent=2, sort_keys=True), encoding="utf-8")

    if not result.get("all_schema_valid"):
        raise SystemExit(2)
    if float(result.get("combined_realized_or_guard_cost_usd", 999)) > FINAL_RECOVERY_CAP_USD + 1e-12:
        raise SystemExit(3)
    print("STUDY1_FINAL23_RECOVERY_PASS", flush=True)


if __name__ == "__main__":
    main()
