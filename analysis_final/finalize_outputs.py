from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

SOURCE_PROVENANCE = {
    "luna": {
        "model": "openai/gpt-5.6-luna",
        "production_run_id": 33284028509,
        "raw_aggregate_artifact_id": 9723896566,
        "respondents": 1000,
        "conditions": ["thin", "rich"],
    },
    "claude": {
        "model": "anthropic/claude-sonnet-5",
        "production_run_id": 33286721946,
        "raw_shards": 20,
        "respondents": 250,
        "conditions": ["thin", "rich"],
    },
    "qwen": {
        "model": "qwen/qwen3.8-27b",
        "artifact_id": 9750263228,
        "respondents": 1000,
        "conditions": ["off", "low", "medium"],
    },
    "deepseek_s01": {
        "model": "deepseek/deepseek-v4-flash-0731",
        "provider": "OpenInference FP8",
        "production_run_id": 33406819430,
        "artifact_id": 9763493454,
        "respondents": 1000,
        "conditions": ["rich_off", "rich_high"],
    },
    "deepseek_s03": {
        "model": "deepseek/deepseek-v4-flash-0731",
        "provider": "OpenInference FP8",
        "production_run_id": 33406819430,
        "artifact_id": 9765135867,
        "respondents": 1000,
        "conditions": ["thin_off", "thin_high"],
    },
    "supervised_baselines": {
        "workflow_run_id": 33415197392,
        "artifact_id": 9766982262,
        "respondents": 1000,
        "outer_folds": 10,
    },
}

FILE_MAP = {
    "unified_contrasts.csv": "contrasts.csv",
    "unified_outcome_metrics.csv": "outcome_metrics.csv",
    "unified_outcome_effects.csv": "outcome_effects.csv",
    "unified_joint_metrics.csv": "joint_metrics.csv",
    "unified_pattern_distribution.csv": "pattern_distribution.csv",
    "unified_subgroup_metrics.csv": "subgroup_metrics.csv",
    "unified_age_reasoning_effects.csv": "age_reasoning_effects.csv",
    "unified_probability_tail.csv": "probability_tail.csv",
    "evidence_matrix.csv": "evidence_matrix.csv",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_cell_metrics(indir: Path, out: Path) -> None:
    cell = pd.read_csv(indir / "unified_cell_metrics.csv")
    joint = pd.read_csv(indir / "unified_joint_metrics.csv")
    joint = joint[joint["cell"] != "human"].copy()
    keep = [c for c in ["cell", "entropy_bits", "joint_tv", "joint_js", "correlation_rmse"] if c in joint.columns]
    joint = joint[keep]
    merged = cell.merge(joint, on="cell", how="left", suffixes=("_cell", "_joint"))

    def coalesce(target: str, *candidates: str) -> None:
        s = pd.Series(index=merged.index, dtype=float)
        for name in candidates:
            if name in merged.columns:
                s = s.combine_first(pd.to_numeric(merged[name], errors="coerce"))
        merged[target] = s

    coalesce("joint_tv", "joint_tv_joint", "joint_tv_cell")
    coalesce("joint_js", "joint_js_joint", "joint_js_cell")
    coalesce("entropy_bits", "entropy_bits_joint", "hard_pattern_entropy_bits")
    coalesce("correlation_rmse", "correlation_rmse_joint", "hard_correlation_rmse")

    drop = [c for c in merged.columns if c.endswith("_cell") or c.endswith("_joint")]
    merged = merged.drop(columns=drop, errors="ignore")
    merged.to_csv(out, index=False)


def main() -> None:
    ap = argparse.ArgumentParser(description="Create the durable publication-safe aggregate result package.")
    ap.add_argument("--indir", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--workflow-run-id", required=True)
    ap.add_argument("--analysis-sha", required=True)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    source_summary = json.loads((args.indir / "summary.json").read_text(encoding="utf-8"))
    if source_summary.get("status") != "COMPLETE_FINAL_UNIFIED_CAMS_ANALYSIS":
        raise AssertionError(source_summary)
    if source_summary.get("paid_inference_performed") is not False:
        raise AssertionError("The harmonized source did not certify zero paid inference")
    if source_summary.get("respondent_level_plaintext_emitted") is not False:
        raise AssertionError("The harmonized source did not certify the data firewall")

    make_cell_metrics(args.indir, args.outdir / "cell_metrics.csv")
    for src, dst in FILE_MAP.items():
        shutil.copyfile(args.indir / src, args.outdir / dst)

    contrasts = pd.read_csv(args.outdir / "contrasts.csv")
    for contrast in ["luna_rich_minus_thin", "claude_rich_minus_thin"]:
        rows = contrasts[(contrasts["contrast"] == contrast) & contrasts["metric"].isin([
            "individual_brier", "log_loss", "hard_accuracy", "probability_prevalence_mae", "hard_prevalence_mae"
        ])]
        if len(rows) != 5 or rows[["ci_low", "ci_high"]].isna().any().any():
            raise AssertionError(f"Legacy harmonization incomplete for {contrast}")
        if not rows["bootstrap_reps"].eq(10000).all():
            raise AssertionError(f"Unexpected bootstrap count for {contrast}")

    summary = {
        **source_summary,
        "status": "MANUSCRIPT_READY_FOUR_FAMILY_ZERO_INFERENCE_SYNTHESIS",
        "canonical_analysis": "analysis_final/unified_analysis.py",
        "harmonization_workflow_run_id": int(args.workflow_run_id),
        "analysis_commit_sha": args.analysis_sha,
        "legacy_point_estimates_replaced_by_common_engine": True,
        "durable_outputs_are_aggregate_only": True,
        "source_provenance": SOURCE_PROVENANCE,
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    files = {}
    for path in sorted(args.outdir.iterdir()):
        if path.name == "MANIFEST.json" or not path.is_file():
            continue
        if path.suffix not in {".csv", ".json"}:
            raise AssertionError(f"Unexpected publication-package file type: {path.name}")
        files[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}

    manifest = {
        "status": "FINAL_PUBLICATION_SAFE_AGGREGATE_PACKAGE",
        "created_by_workflow_run_id": int(args.workflow_run_id),
        "analysis_commit_sha": args.analysis_sha,
        "bootstrap_reps": 10000,
        "bootstrap_seed": 3108202691,
        "paid_inference_performed": False,
        "respondent_level_plaintext_in_package": False,
        "source_provenance": SOURCE_PROVENANCE,
        "files": files,
    }
    (args.outdir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "files": len(files), "workflow_run_id": int(args.workflow_run_id)}, indent=2))


if __name__ == "__main__":
    main()
