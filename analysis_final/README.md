# Final zero-inference analysis

This directory is the canonical pre-manuscript analysis layer for **Better synthetic individuals do not make better synthetic populations**.

No file in this layer performs paid LLM inference.

## Components

- `baselines.py` fits supervised reference models with 10-fold out-of-fold prediction, internal tuning, survey weights, and 10,000 respondent bootstraps.
- `final_unified.py` is the canonical cross-study synthesis. It decrypts already-completed Qwen and DeepSeek outputs, joins withheld CAMS truth only after generation, recomputes harmonized metrics, and estimates paired interactions.
- `unified_analysis.py` contains reusable harmonization, bootstrap, subgroup, joint-distribution, and probability-tail utilities.
- `figures.R` produces the publication figure suite in PDF, SVG, and 450-dpi PNG.

## Supervised comparators

The final baseline set is:

1. survey-weighted prevalence predictor;
2. tuned regularized logistic regression;
3. tuned gradient boosting;
4. random forest.

These are **cross-fitted supervised comparators**. They use outcome-labeled training respondents within each fold, so they are not information-regime-equivalent to zero-shot LLM synthetic respondents. Their role is to show what ordinary tabular prediction can achieve on the same covariates and held-out respondents.

## Frozen legacy metrics

Luna and Claude persona-study point estimates are carried from their original frozen truth-linked analyses. Qwen and DeepSeek are re-read from the authoritative encrypted production artifacts and recomputed under one harmonized implementation. Study-specific preregistered analyses remain authoritative for their original primary claims.

## Outputs

The final unified artifact contains cell metrics, paired contrasts, outcome effects, subgroup metrics, age-specific reasoning effects, joint population structure, response-pattern distributions, probability-tail diagnostics, and the compact evidence matrix.

The figure workflow consumes only those aggregate files. It does not access respondent-level data or any API inference endpoint.
