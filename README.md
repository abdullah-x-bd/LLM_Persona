# Better synthetic individuals do not make better synthetic populations

This repository contains a multi-study audit of LLM population simulation against real Government of India CAMS survey respondents. The empirical program for the current manuscript is frozen. The statistical baselines, four-family harmonized analysis, durable aggregate result package, and final R publication figure suite are complete. No additional paid inference is required for the current paper.

The central result is methodological: **improving synthetic individuals does not guarantee improving synthetic populations**. Individual predictive fidelity is not a sufficient proxy for population fidelity. Persona information, model identity, and inference-time reasoning can improve respondent-level prediction while changing population prevalence, hard categorical totals, joint response structure, subgroup patterns, or probability tails in different directions.

This is a non-guarantee, not a universal claim that better individual prediction must make population reconstruction worse. DeepSeek provides an important counterexample in which high reasoning improves Brier and several population endpoints while worsening log loss through a heavier tail of confidently wrong probabilities.

## Frozen truth-linked CAMS evidence

| Study | Model | Design | n | Final status |
|---|---|---|---:|---|
| Persona information | GPT-5.6 Luna | thin vs rich | 1,000 paired | complete |
| Persona robustness | Claude Sonnet 5 | thin vs rich | 250 paired | complete |
| Reasoning | Qwen3.8-27B | off / low / medium | 1,000 paired | complete |
| S01 reasoning replication | DeepSeek V4 Flash 0731 | rich/off vs rich/high | 1,000 paired | complete |
| S03 factorial | DeepSeek V4 Flash 0731 | thin/rich × off/high | 1,000 | complete |
| Supervised references | prevalence, logistic, gradient boosting, random forest | 10-fold cross-fitted | 1,000 | complete |

S01 and S03 generation used OpenInference FP8, provider fallback disabled, provider data collection `deny`, and no CAMS truth during generation. Historical respondent-level outputs remain encrypted; truth enters only during post-generation analysis.

## Headline harmonized findings

- **Luna rich vs thin:** Brier improves by 0.0187, but hard-prevalence MAE worsens by about 3.20 percentage points. The probability-prevalence change is uncertain.
- **Claude rich vs thin:** Brier, log loss, accuracy, and hard-prevalence MAE improve, while probability-prevalence MAE worsens by about 1.06 percentage points.
- **Qwen medium reasoning vs off:** Brier and log loss improve, but hard accuracy falls and probability- and hard-prevalence MAE worsen.
- **DeepSeek high reasoning vs off under rich personas:** Brier, hard accuracy, both prevalence endpoints, and joint population structure improve strongly, while log loss worsens by about 0.419 because extreme wrong probabilities become much more common.
- **Direct model × reasoning test:** DeepSeek and Qwen reasoning effects differ strongly on log loss, accuracy, probability-prevalence MAE, and hard-prevalence MAE. The Brier interaction itself crosses zero.
- **DeepSeek factorial:** reasoning improves individual Brier more under thin personas, while rich persona information significantly complements reasoning for hard population reconstruction.
- **Supervised references:** the best model depends on the estimand. No single comparator is best on Brier, marginal prevalence, hard prevalence, and joint-distribution fidelity simultaneously.

The final detailed synthesis is in `docs/REPO_WIDE_RESULTS_SYNTHESIS.md`.

## Canonical manuscript package

`analysis_final/` is the final zero-inference analysis layer.

Use these committed directories as the durable manuscript sources:

- `analysis_final/results/` for the final aggregate-only four-family analysis tables and checksum manifest;
- `analysis_final/figures/` for the eight final figures in PDF, SVG, and 600-dpi PNG plus checksum manifest.

The canonical cross-study engine is `analysis_final/unified_analysis.py`. It reconstructs all 11 completed LLM cells from the authoritative completed outputs and uses one common metric implementation with 10,000 paired respondent bootstrap replicates.

The supervised models are **cross-fitted supervised comparators**, not information-regime-equivalent substitutes for zero-shot synthetic respondents.

## Final figure suite

The validated R/ggplot2 package contains:

1. micro-versus-macro fidelity map;
2. Qwen-versus-DeepSeek reasoning reversal;
3. DeepSeek persona × reasoning factorial;
4. age-gradient reasoning effects;
5. joint-population response-pattern fingerprint;
6. individual-versus-joint fidelity landscape with supervised references;
7. DeepSeek confidence-tail trade-off;
8. outcome-level reasoning-effect heatmap.

The final figure workflow run `33459804925` passed rendering, integrity checks, repository freeze, and artifact upload. The figures contain no embedded plot titles.

## Current paper boundary

- **S01** complete and analyzed.
- **S03** complete and analyzed.
- **S02** archived as an unrun prospective length-safe replication and excluded from the current paper.
- **S04** scientifically blocked because the matched PLFS truth asset is absent and excluded from current truth-linked evidence.
- **S05** archived as an unrun prospective fresh-holdout extension and excluded from the current paper.

CMS and PLFS synthetic-output branches remain useful for provenance and model-instability analyses, but they must not be described as truth-linked accuracy validations without matched truth assets.

Historical paid, repair, recovery, and provider-engineering workflows are intentionally retained as provenance. Their presence does not imply that more inference should be launched.

## Evaluation hierarchy

Population fidelity is treated as a vector rather than a single score. The final package evaluates:

- survey-weighted Brier score and log loss;
- hard-response accuracy;
- probability- and hard-prevalence MAE;
- probability extremeness and catastrophic tails;
- subgroup and age fidelity;
- six-outcome response-pattern entropy;
- total-variation and Jensen-Shannon distance;
- hard-response correlation structure;
- outcome-level treatment effects.

## Repository map

```text
LLM_Persona/
├── README.md
├── analysis_final/
│   ├── results/                 # canonical aggregate manuscript results
│   ├── figures/                 # final PDF/SVG/600-dpi PNG figures
│   └── final analysis + QA code
├── docs/                        # final synthesis, provenance, audit, historical design
├── studies/                     # frozen S01-S05 records and machine registry
├── reasoning_population_fidelity/ # completed Qwen reasoning study
├── src/                         # historical CAMS/CMS/PLFS runtime and analysis
├── data/encrypted/              # encrypted reproducibility assets
└── .github/workflows/           # historical provenance + final zero-inference workflows
```

For manuscript preparation, start with:

- `docs/PRE_MANUSCRIPT_AUDIT.md`
- `docs/REPO_WIDE_RESULTS_SYNTHESIS.md`
- `docs/FINAL_PROVENANCE.md`
- `analysis_final/README.md`
- `analysis_final/results/summary.json`
- `analysis_final/results/contrasts.csv`
- `analysis_final/figures/`

The repository is intended to be treated as a frozen evidence package after the final machine QA workflow passes. Any future reviewer-driven extension should be recorded as new work rather than silently changing the current manuscript evidence boundary.
