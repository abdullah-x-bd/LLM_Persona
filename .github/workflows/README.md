# GitHub Actions workflow guide

Historical production, repair, recovery, and provider-engineering workflows are intentionally retained as provenance. They should not be interpreted as a queue of experiments still to run.

## Canonical manuscript-stage workflows

The current manuscript phase is zero-inference only:

- `final_baselines.yml` fits the cross-fitted supervised reference models with 10-fold out-of-fold prediction and 10,000 bootstraps.
- `final_unified_analysis.yml` recovers the already-completed Luna and Claude outputs transiently, reads the authoritative completed Qwen and DeepSeek artifacts, runs the common four-family metric engine with 10,000 paired bootstraps, and commits only the aggregate publication-safe result package.
- `final_figures.yml` consumes only `analysis_final/results/`, generates the title-free R/ggplot2 publication suite in PDF, SVG, and 600-dpi PNG, validates checksums, and freezes the figure package in the repository.
- `final_qa.yml` runs the final result, figure, documentation, study-status, checksum, and privacy gate.

These workflows do not perform paid LLM inference.

## Historical evidence families

- `production_luna.yml` and `cams_*` belong to the original CAMS persona work and Claude robustness work.
- workflows beginning `reasoning_population_` preserve the completed Qwen reasoning study and its recovery/robustness history.
- `followup_*`, `finalize_s01_then_s03_fast.yml`, and DeepSeek diagnostic workflows preserve the completed S01/S03 production and analysis chain.
- `cms_*` and `plfs_*` belong to multisurvey robustness work. They are not truth-linked current-paper evidence without matched truth assets.
- Gemini workflows are historical engineering records and are not current-paper fidelity evidence.
- `study_suite_*` preserves the prospective S01-S05 framework. S01 and S03 are complete; S02 and S05 are archived unrun; S04 is scientifically blocked.

## Paid-run rule

No additional paid inference is planned for the current manuscript. The presence of historical paid workflows is provenance, not authorization to rerun them.

If a future reviewer-driven extension genuinely requires new inference, it should be implemented as a new explicitly justified workflow with a frozen request set, an explicit spend cap, disabled provider fallbacks, encrypted respondent outputs, truth-separated generation, and recovery from checkpoints rather than whole-run repetition.
