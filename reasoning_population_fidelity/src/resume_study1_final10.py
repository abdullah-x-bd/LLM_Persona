from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path

import resume_study1 as rs

FROZEN_STUDY_CAP_USD = 7.80
PRIOR_RECOVERY_CAP_USD = 8.75
FINAL_RECOVERY_CAP_USD = 9.20
PROJECT_HARD_CAP_USD = 9.50
EXPECTED_SEED_VALID = 2990
EXPECTED_MISSING = 10
EXPECTED_SEED_COUNTS = {"off": 1000, "low": 994, "medium": 996}
MAX_RECOVERY_CYCLES = 4

ORIGINAL_LOAD_JSON = rs.load_json


def patched_load_json(path):
    cfg = ORIGINAL_LOAD_JSON(path)
    if Path(path) == Path(rs.CONFIG):
        cfg = copy.deepcopy(cfg)
        frozen = float(cfg["study_1"]["study_budget_cap_usd"])
        project_cap = float(cfg["hard_spend_cap_usd"])
        frozen_retries = int(cfg["run_policy"]["max_retries"])
        if abs(frozen - FROZEN_STUDY_CAP_USD) > 1e-9:
            raise RuntimeError(f"Unexpected frozen Study 1 cap: {frozen}")
        if abs(project_cap - PROJECT_HARD_CAP_USD) > 1e-9:
            raise RuntimeError(f"Unexpected project hard cap: {project_cap}")
        if frozen_retries != 3:
            raise RuntimeError(f"Unexpected frozen per-cycle max_retries: {frozen_retries}")
        if not (PRIOR_RECOVERY_CAP_USD < FINAL_RECOVERY_CAP_USD <= project_cap):
            raise RuntimeError("Final recovery cap must remain within project hard cap")
        cfg["study_1"]["study_budget_cap_usd"] = FINAL_RECOVERY_CAP_USD
    return cfg


def load_cycle_result(cycle_output: Path) -> dict:
    p = cycle_output / "study1_summary.json"
    if not p.exists():
        raise RuntimeError(f"Recovery cycle did not write a durable summary: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


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

    # Scientific treatment stays frozen. We only repeat the existing frozen
    # three-attempt operational recovery cycle. SystemExit(2) from rs.run means
    # "incomplete but checkpoint written", so it must be consumed as the seed
    # for the next cycle rather than terminating this wrapper.
    rs.load_json = patched_load_json
    rs.RESUME_CONCURRENCY = 10
    rs.BATCH_SIZE = 10

    note = {
        "status": "POST_INTERIM_FINAL10_REPEATED_OPERATIONAL_RECOVERY",
        "reason": "The 10 remaining frozen requests have repeated finish_reason=length failures under the frozen completion limits. Continue identical requests without changing treatment/generation settings.",
        "seed_valid_requests": EXPECTED_SEED_VALID,
        "missing_requests_at_start": EXPECTED_MISSING,
        "missing_condition_counts_at_start": {"off": 0, "low": 6, "medium": 4},
        "frozen_study_budget_cap_usd": FROZEN_STUDY_CAP_USD,
        "prior_operational_recovery_cap_usd": PRIOR_RECOVERY_CAP_USD,
        "final_operational_recovery_cap_usd": FINAL_RECOVERY_CAP_USD,
        "project_hard_spend_cap_usd": PROJECT_HARD_CAP_USD,
        "changes_to_scientific_treatment": False,
        "treatment_or_generation_settings_changed": False,
        "token_caps_changed": False,
        "prompt_or_schema_changed": False,
        "provider_changed": False,
        "analysis_plan_changed": False,
        "operational_retry_protocol_extended_post_interim": True,
        "frozen_max_retries_per_cycle": 3,
        "max_additional_recovery_cycles": MAX_RECOVERY_CYCLES,
        "resume_concurrency": rs.RESUME_CONCURRENCY,
        "resume_batch_size": rs.BATCH_SIZE,
        "interim_outcomes_seen_before_recovery": True,
        "wrapper_bug_fixed_after_failed_run_33370754219": True,
        "purpose": "Collect only the final 10 missing request IDs from the existing frozen 3000-request Study 1 set.",
    }
    print(json.dumps(note, indent=2, sort_keys=True), flush=True)

    current_seed = args.seed_dir
    last_output: Path | None = None
    result: dict | None = None
    cycles_run = 0
    final_out = args.workdir / "study1_resume_output"

    for cycle in range(1, MAX_RECOVERY_CYCLES + 1):
        cycle_workdir = args.workdir / f"cycle_{cycle}"
        cycle_output = cycle_workdir / "study1_resume_output"
        print(json.dumps({"status": "FINAL10_CYCLE_START", "cycle": cycle, "seed_dir": str(current_seed)}, sort_keys=True), flush=True)

        exit_code = 0
        try:
            result = rs.run(current_seed, cycle_workdir, False)
        except SystemExit as exc:
            exit_code = int(exc.code or 0)
            if exit_code not in (2, 3):
                raise
            result = load_cycle_result(cycle_output)

        cycles_run = cycle
        last_output = cycle_output

        # Keep a top-level durable copy after EVERY cycle, so the workflow upload
        # still has the newest checkpoint even if a later cycle encounters an
        # unexpected failure.
        if final_out.exists():
            shutil.rmtree(final_out)
        shutil.copytree(last_output, final_out)
        note["cycles_run"] = cycles_run
        note["final_requests_schema_valid"] = int(result.get("requests_schema_valid", 0))
        note["final_remaining_failures"] = int(result.get("remaining_failures", 3000))
        note["last_cycle_exit_code"] = exit_code
        (final_out / "final10_recovery_note.json").write_text(json.dumps(note, indent=2, sort_keys=True), encoding="utf-8")

        print(json.dumps({
            "status": "FINAL10_CYCLE_END",
            "cycle": cycle,
            "cycle_exit_code": exit_code,
            "requests_schema_valid": result.get("requests_schema_valid"),
            "remaining_failures": result.get("remaining_failures"),
            "combined_realized_or_guard_cost_usd": result.get("combined_realized_or_guard_cost_usd"),
        }, sort_keys=True), flush=True)

        if result.get("all_schema_valid"):
            break
        if exit_code == 3 or result.get("stop_reason"):
            break
        current_seed = last_output

    if last_output is None or result is None:
        raise RuntimeError("No final recovery cycle executed")

    if not result.get("all_schema_valid"):
        raise SystemExit(2)
    if float(result.get("combined_realized_or_guard_cost_usd", 999)) > FINAL_RECOVERY_CAP_USD + 1e-12:
        raise SystemExit(3)
    print("STUDY1_FINAL10_RECOVERY_PASS", flush=True)


if __name__ == "__main__":
    main()
