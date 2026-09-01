# Better synthetic individuals do not make better synthetic populations

This repository contains a multi-study audit of LLM population simulation against real Government of India survey respondents. The empirical program for the current paper is now frozen. No additional paid inference is planned for the manuscript unless a specific reviewer-driven need emerges.

The central result is methodological: **individual predictive fidelity is not a sufficient or reliable proxy for population fidelity**. Persona information, model identity, and inference-time reasoning can improve respondent-level prediction while changing population prevalence, subgroup structure, joint response patterns, calibration, or confidence in different directions.

## Completed truth-linked CAMS evidence

| Study | Model | Design | n | Status |
|---|---|---|---:|---|
| Persona information | GPT-5.6 Luna | thin vs rich | 1,000 paired | complete |
| Persona robustness | Claude Sonnet 5 | thin vs rich | 250 paired | complete |
| Reasoning | Qwen3.8-27B | off / low / medium | 1,000 paired | complete |
| S01 reasoning replication | DeepSeek V4 Flash 0731 | rich off vs high | 1,000 paired | complete |
| S03 factorial | DeepSeek V4 Flash 0731 | persona × reasoning | 1,000, four cells | complete |

The DeepSeek S01/S03 generation used OpenInference FP8, provider fallback disabled, provider data collection set to `deny`, and no human truth during generation. Qwen and DeepSeek respondent-level outputs remain encrypted; truth is loaded only in post-generation analysis.

## Current paper boundary

- **S01** complete and analyzed.
- **S03** complete and analyzed.
- **S02** archived as an unrun prospective length-safe replication. It is not needed for the current paper.
- **S04** remains scientifically blocked because the matched PLFS truth bundle is absent. It is excluded from the current truth-linked paper evidence.
- **S05** archived as an unrun prospective fresh-holdout extension. It is not needed for the current paper.

CMS and PLFS synthetic-output branches remain useful for cross-model instability and provenance, but the current repository does not contain their matched truth bundles. They must not be described as truth-linked accuracy validations.

## Final zero-inference analysis

`analysis_final/` is the canonical manuscript-preparation layer. It contains:

- 10-fold cross-fitted supervised reference models with internal tuning;
- 10,000 respondent bootstraps;
- a harmonized Qwen/DeepSeek raw-output reanalysis;
- a paired model × reasoning interaction test on the same 1,000 CAMS respondents;
- subgroup, age-gradient, joint-distribution, archetype, and confidence-tail diagnostics;
- publication figures generated in R/ggplot2.

The supervised models are **cross-fitted supervised comparators**, not information-regime-equivalent substitutes for zero-shot synthetic respondents.

## Evaluation hierarchy

Population fidelity is treated as a vector, not a single score. The repository evaluates:

- survey-weighted Brier score and log loss;
- hard-response accuracy;
- probability and hard prevalence MAE;
- calibration and probability extremeness;
- subgroup fidelity;
- six-outcome response-pattern entropy;
- total-variation and Jensen-Shannon distance;
- hard-response correlation structure;
- model- and reasoning-dependent probability tails.

## Repository map

```text
LLM_Persona/
├── README.md
├── analysis_final/              # canonical pre-manuscript analysis + R figures
├── docs/                        # design, synthesis, provenance, final audit
├── studies/                     # S01-S05 frozen designs and status
├── reasoning_population_fidelity/ # completed Qwen reasoning study
├── src/                         # original CAMS/CMS/PLFS runtime and analysis
├── data/encrypted/              # encrypted reproducibility assets
└── .github/workflows/           # historical provenance + final zero-inference workflows
```

Start with `docs/PRE_MANUSCRIPT_AUDIT.md`, `docs/REPO_WIDE_RESULTS_SYNTHESIS.md`, and `analysis_final/README.md` when preparing the paper.

Historical production, repair, and recovery workflows are intentionally retained as provenance. Their presence does not imply that additional inference should be launched.
