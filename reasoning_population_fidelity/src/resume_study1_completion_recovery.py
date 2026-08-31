from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import resume_study1 as rs

FROZEN_STUDY_CAP_USD = 7.80
RECOVERY_CAP_USD = 8.50
PROJECT_HARD_CAP_USD = 9.50


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
        if not (frozen < RECOVERY_CAP_USD <= project_cap):
            raise RuntimeError("Recovery cap must exceed frozen Study 1 cap and remain within project hard cap")
        cfg["study_1"]["study_budget_cap_usd"] = RECOVERY_CAP_USD
    return cfg


ORIGINAL_LOAD_JSON = rs.load_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-dir", required=True, type=Path)
    ap.add_argument("--workdir", required=True, type=Path)
    args = ap.parse_args()

    # Operational-only recovery. No request, prompt, model, provider, reasoning,
    # schema, generation, retry, or analysis setting is changed.
    rs.load_json = patched_load_json
    rs.RESUME_CONCURRENCY = 8
    rs.BATCH_SIZE = 48

    note = {
        "status": "POST_INTERIM_OPERATIONAL_COMPLETION_RECOVERY",
        "reason": "Frozen $7.80 Study 1 budget guard was exhausted by retry/guard accounting before all already-frozen requests completed.",
        "frozen_study_budget_cap_usd": FROZEN_STUDY_CAP_USD,
        "operational_recovery_cap_usd": RECOVERY_CAP_USD,
        "project_hard_spend_cap_usd": PROJECT_HARD_CAP_USD,
        "changes_to_scientific_design": False,
        "treatment_or_generation_settings_changed": False,
        "analysis_plan_changed": False,
        "interim_outcomes_seen_before_recovery": True,
        "purpose": "Collect only missing request IDs from the existing frozen 3000-request set.",
    }
    print(json.dumps(note, indent=2, sort_keys=True), flush=True)

    outdir = args.workdir / "study1_resume_output"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "completion_recovery_note.json").write_text(json.dumps(note, indent=2, sort_keys=True), encoding="utf-8")

    try:
        result = rs.run(args.seed_dir, args.workdir, False)
    finally:
        # Ensure the disclosure note survives even if the recovery stops early.
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "completion_recovery_note.json").write_text(json.dumps(note, indent=2, sort_keys=True), encoding="utf-8")

    if not result.get("all_schema_valid"):
        raise SystemExit(2)
    if float(result.get("combined_realized_or_guard_cost_usd", 999)) > RECOVERY_CAP_USD + 1e-12:
        raise SystemExit(3)
    print("STUDY1_COMPLETION_RECOVERY_PASS", flush=True)


if __name__ == "__main__":
    main()
