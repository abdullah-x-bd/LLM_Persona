# GitHub Actions workflow guide

This directory intentionally preserves historical production, repair, recovery, and analysis workflows. The repository used checkpoint-aware cloud inference, so deleting old workflows would erase useful provenance about how paid outputs were recovered.

## Canonical current workflows

For the five new confirmatory studies use:

- `study_suite_preflight.yml` for zero-cost request/data/model/provider/budget checks;
- `study_suite_paid.yml` for an explicitly confirmed manual paid launch.

For the original Qwen reasoning project, workflows beginning `reasoning_population_` belong to `reasoning_population_fidelity/` and should be interpreted together with that folder's changelog and frozen analysis plan.

## Historical workflow families

- `production_luna.yml` and CAMS Claude workflows belong to the original persona study.
- `cms_*` and `plfs_*` workflows belong to the multisurvey robustness program.
- Gemini repair workflows are historical engineering records. Gemini inference was retired after repeated reliability problems and should not be restarted casually.
- repair/recovery workflows may contain the scientifically valid completed checkpoint even when an earlier parent production workflow concluded with failure.

## Paid-run rule

Never make a workflow paid merely by pushing code. New paid workflows must be `workflow_dispatch` only, require a literal confirmation string, run the zero-cost preflight first, use an explicit spend cap, disable provider fallbacks, and upload encrypted respondent-level outputs.

Never rerun a full paid workflow to repair a small missing subset if a recoverable checkpoint or encrypted artifact exists.
