# Final zero-inference analysis

This directory is the canonical analysis layer for **Better synthetic individuals do not make better synthetic populations**.

No file in this layer performs paid LLM inference.

## Canonical components

- `baselines.py` fits the supervised reference models with 10-fold out-of-fold prediction, internal tuning, survey weights, and 10,000 respondent bootstraps.
- `unified_analysis.py` is the canonical four-family cross-study metric engine. It evaluates completed Luna, Claude, Qwen, and DeepSeek outputs under one implementation and estimates paired contrasts, interactions, subgroup effects, joint-distribution metrics, and probability-tail diagnostics.
- `recover_legacy.py` decrypts the completed Luna aggregate transiently inside CI so the original Luna outputs can enter the common engine. Plaintext is not committed or uploaded as a final artifact.
- `finalize_outputs.py` converts common-engine output into the durable aggregate-only result package and generates SHA-256 provenance.
- `figures.R` produces the title-free figure suite in PDF, SVG, and 600-dpi PNG.
- `final_qa.py` checks repository integrity, privacy, documentation, licensing, results, and figures.
- `final_unified.py` is retained as historical provenance for the earlier Qwen/DeepSeek-centered synthesis. It is not the canonical four-family engine.

## Canonical outputs

`results/` is the durable aggregate result package. It contains:

- `cell_metrics.csv`
- `contrasts.csv`
- `evidence_matrix.csv`
- `joint_metrics.csv`
- `outcome_metrics.csv`
- `outcome_effects.csv`
- `pattern_distribution.csv`
- `subgroup_metrics.csv`
- `age_reasoning_effects.csv`
- `probability_tail.csv`
- `summary.json`
- `MANIFEST.json`

The result package contains aggregate statistics only. It contains no respondent-level plaintext and no raw generation outputs.

`figures/` contains eight figures, each in PDF, SVG, and 600-dpi PNG, plus a figure index and checksum manifest.

## Four-family harmonization

The canonical synthesis reads the authoritative completed outputs for all four LLM families:

- Luna: 1,000 respondents in thin and rich conditions;
- Claude: 250 respondents in thin and rich conditions;
- Qwen: 1,000 respondents in off, low, and medium reasoning conditions;
- DeepSeek: 1,000 respondents in thin/off, thin/high, rich/off, and rich/high cells.

Primary cross-study contrasts use 10,000 paired respondent bootstrap replicates where paired respondent-level outputs are available. Luna and Claude are recomputed under the same metric engine used for Qwen and DeepSeek.

The original study-specific frozen analyses remain authoritative for their prospectively defined primary claims. The common-engine layer is authoritative for harmonized cross-study comparisons and figures.

## Supervised comparators

The supervised reference set contains:

1. survey-weighted prevalence predictor;
2. logistic regression;
3. gradient boosting;
4. random forest.

These are **cross-fitted supervised comparators**. They use outcome-labeled training respondents within each fold, so they are not information-regime-equivalent to zero-shot LLM synthetic respondents. Their role is to provide reference points on the same held-out respondents and to show that different validation objectives can rank methods differently.

## Data firewall

Historical respondent-level generation outputs remain encrypted in their original Actions artifacts. The final harmonization workflow decrypts completed outputs only transiently in CI, after generation, and emits only aggregate files. CAMS truth is joined only during analysis. No final workflow calls an LLM inference endpoint.

## Reproducibility entry points

- `results/summary.json` — machine-readable final status
- `results/contrasts.csv` — paired effects and confidence intervals
- `results/MANIFEST.json` — result-package integrity
- `figures/` — final figure package
- `../docs/REPO_WIDE_RESULTS_SYNTHESIS.md` — empirical synthesis
- `../docs/FINAL_PROVENANCE.md` — authoritative provenance
- `../docs/SCIENTIFIC_FREEZE.md` — frozen scientific boundary

Run `python analysis_final/final_qa.py` from the repository root to verify the committed package.
