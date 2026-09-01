from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis_final" / "results"
FIGURES = ROOT / "analysis_final" / "figures"

EXPECTED_RESULT_FILES = {
    "MANIFEST.json",
    "summary.json",
    "cell_metrics.csv",
    "contrasts.csv",
    "evidence_matrix.csv",
    "joint_metrics.csv",
    "outcome_metrics.csv",
    "outcome_effects.csv",
    "pattern_distribution.csv",
    "subgroup_metrics.csv",
    "age_reasoning_effects.csv",
    "probability_tail.csv",
}

FIGURE_NAMES = [
    "fig01_micro_macro",
    "fig02_reasoning_reversal",
    "fig03_deepseek_factorial",
    "fig04_age_gradient",
    "fig05_population_fingerprint",
    "fig06_fidelity_landscape",
    "fig07_overconfidence",
    "fig08_outcome_effects",
]

REQUIRED_DOCS = [
    "README.md",
    "CITATION.cff",
    "analysis_final/README.md",
    "docs/PRE_MANUSCRIPT_AUDIT.md",
    "docs/FINAL_PROVENANCE.md",
    "docs/REPO_MAP.md",
    "docs/REPO_WIDE_RESULTS_SYNTHESIS.md",
    "docs/RELEASE_NOTES_v1.0.0.md",
    "docs/RELEASE_CHECKLIST.md",
    "studies/README.md",
    "studies/registry.json",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_results() -> None:
    actual = {p.name for p in RESULTS.iterdir() if p.is_file()}
    missing = EXPECTED_RESULT_FILES - actual
    if missing:
        raise AssertionError(f"Missing canonical aggregate outputs: {sorted(missing)}")

    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "MANUSCRIPT_READY_FOUR_FAMILY_ZERO_INFERENCE_SYNTHESIS", summary
    assert summary["paid_inference_performed"] is False
    assert summary["respondent_level_plaintext_emitted"] is False
    assert summary["legacy_point_estimates_replaced_by_common_engine"] is True

    manifest = json.loads((RESULTS / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "FINAL_PUBLICATION_SAFE_AGGREGATE_PACKAGE", manifest
    assert manifest["paid_inference_performed"] is False
    assert manifest["respondent_level_plaintext_in_package"] is False
    for name, meta in manifest["files"].items():
        path = RESULTS / name
        assert path.exists(), name
        assert path.stat().st_size == int(meta["bytes"]), name
        assert sha256(path) == meta["sha256"], name

    cells = pd.read_csv(RESULTS / "cell_metrics.csv")
    assert len(cells) == 15, len(cells)
    llm = cells[cells["method_class"].eq("LLM")]
    assert len(llm) == 11, len(llm)
    for col in ["joint_tv", "joint_js", "entropy_bits", "correlation_rmse"]:
        assert llm[col].notna().all(), (col, llm[llm[col].isna()]["cell"].tolist())

    contrasts = pd.read_csv(RESULTS / "contrasts.csv")
    required = {
        "luna_rich_minus_thin",
        "claude_rich_minus_thin",
        "qwen_medium_minus_off",
        "deepseek_rich_high_minus_off",
        "deepseek_persona_x_reasoning_interaction",
        "deepseek_minus_qwen_reasoning_effect",
    }
    assert required <= set(contrasts["contrast"])
    for name in ["luna_rich_minus_thin", "claude_rich_minus_thin"]:
        x = contrasts[contrasts["contrast"].eq(name)]
        assert len(x) == 5
        assert x[["ci_low", "ci_high"]].notna().all().all()
        assert x["bootstrap_reps"].eq(10000).all()


def check_figures() -> None:
    assert FIGURES.is_dir(), "analysis_final/figures is missing"
    for name in FIGURE_NAMES:
        for ext in ["pdf", "svg", "png"]:
            path = FIGURES / f"{name}.{ext}"
            assert path.exists(), str(path)
            assert path.stat().st_size > 1000, str(path)
    index = (FIGURES / "FIGURE_INDEX.txt").read_text(encoding="utf-8").splitlines()
    assert index == FIGURE_NAMES, index
    manifest_path = FIGURES / "MANIFEST.json"
    assert manifest_path.exists(), str(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "FINAL_PUBLICATION_FIGURE_PACKAGE", manifest
    assert manifest["png_dpi"] == 600
    for name, meta in manifest["files"].items():
        path = FIGURES / name
        assert path.exists(), name
        assert path.stat().st_size == int(meta["bytes"]), name
        assert sha256(path) == meta["sha256"], name

    src = (ROOT / "analysis_final" / "figures.R").read_text(encoding="utf-8")
    assert "dpi = 600" in src
    assert not re.search(r"\bggtitle\s*\(", src)
    assert "plot.title = element_blank()" in src


def check_docs() -> None:
    for rel in REQUIRED_DOCS:
        assert (ROOT / rel).exists(), rel
    registry = json.loads((ROOT / "studies" / "registry.json").read_text(encoding="utf-8"))
    studies = registry["studies"]
    assert studies["S01_second_model_reasoning"]["status"] == "COMPLETE_AND_ANALYZED"
    assert studies["S03_persona_reasoning_factorial"]["status"] == "COMPLETE_AND_ANALYZED"
    assert studies["S02_length_safe_reasoning"]["status"].startswith("ARCHIVED_UNRUN")
    assert studies["S04_plfs_reasoning_replication"]["status"].startswith("SCIENTIFICALLY_BLOCKED")
    assert studies["S05_fresh_holdout_confirmation"]["status"].startswith("ARCHIVED_UNRUN")

    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "CITATION.cff" in root_readme
    assert "docs/PRE_MANUSCRIPT_AUDIT.md" in root_readme
    assert "docs/RELEASE_NOTES_v1.0.0.md" in root_readme
    assert "docs/RELEASE_CHECKLIST.md" in root_readme
    assert "analysis_final/results" in root_readme
    assert "analysis_final/figures" in root_readme

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "cff-version: 1.2.0" in citation
    assert "version: 1.0.0" in citation
    assert "repository-code:" in citation


def check_privacy() -> None:
    forbidden = []
    for base in [RESULTS, FIGURES]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            lower = path.name.lower()
            if path.suffix.lower() in {".jsonl", ".b64", ".enc"} or "raw_results" in lower or "respondent" in lower:
                forbidden.append(str(path.relative_to(ROOT)))
    assert not forbidden, forbidden


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-figures", action="store_true")
    args = ap.parse_args()
    check_results()
    if not args.skip_figures:
        check_figures()
    check_docs()
    check_privacy()
    print("FINAL_REPO_QA_PASS")


if __name__ == "__main__":
    main()
