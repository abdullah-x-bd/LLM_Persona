# GitHub Actions workflow guide

Historical production, repair, recovery, and provider-engineering workflows are intentionally retained as provenance. They should not be interpreted as a queue of experiments still to run.

## Canonical current workflows

The current manuscript phase is zero-inference only:

- `final_baselines.yml` fits cross-fitted supervised comparators.
- `final_unified_analysis.yml` reconstructs the completed Qwen and DeepSeek outputs, joins CAMS truth after generation, and runs the harmonized 10,000-bootstrap synthesis.
- `final_figures.yml` consumes aggregate unified outputs and generates the R/ggplot2 publication figure suite.

The completed DeepSeek production/recovery chain is preserved in `followup_*` and `finalize_s01_then_s03_fast.yml`. The completed Qwen chain is preserved in workflows beginning `reasoning_population_`.

## Historical families

- `production_luna.yml` and `cams_*` belong to the original CAMS persona work.
- `cms_*` and `plfs_*` belong to multisurvey robustness work.
- Gemini workflows are historical engineering records and are not current-paper evidence.
- `study_suite_*` preserves the prospective S01-S05 launch framework. S01 and S03 are complete; S02/S05 are archived unrun; S04 remains scientifically blocked.

## Paid-run rule

No additional paid inference is planned for the current manuscript. If a future extension or reviewer request requires inference, it must use a manual guarded workflow, explicit spend cap, frozen request set, disabled fallbacks, encrypted respondent outputs, and truth-separated generation. Never rerun a full paid workflow to repair a recoverable subset.
