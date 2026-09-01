# Scientific freeze record

This document records the evidentiary boundary of version 1.0.0 of the research artifact.

The truth-linked CAMS experiments, supervised reference models, four-family harmonized analysis, aggregate result package, and R figure suite are complete. Version 1.0.0 contains no additional paid LLM inference beyond the completed experimental runs documented in the provenance record.

## Evidence boundary

| Component | Status |
|---|---|
| Luna thin vs rich, n=1,000 paired | complete |
| Claude thin vs rich, n=250 paired | complete |
| Qwen off / low / medium, n=1,000 paired | complete |
| DeepSeek S01 rich/off vs rich/high, n=1,000 paired | complete |
| DeepSeek S03 thin/rich × off/high factorial, n=1,000 | complete |
| Supervised 10-fold cross-fitted references | complete |
| Four-family common-engine synthesis | complete |
| 10,000 paired-bootstrap cross-study contrasts | complete |
| Qwen-versus-DeepSeek reasoning interaction | complete |
| DeepSeek persona × reasoning interaction | complete |
| Joint-distribution analysis | complete |
| Age/subgroup and probability-tail diagnostics | complete |
| Aggregate result package | complete |
| Eight-figure R publication package | complete |
| S02 | archived unrun |
| S04 | scientifically blocked and excluded from truth-linked claims |
| S05 | archived unrun |

## Analysis identity

### Statistical references

- Workflow run: `33415197392`
- Artifact: `9766982262`
- Respondents: 1,000
- Outer folds: 10
- Bootstrap replicates: 10,000
- Models: weighted prevalence, logistic regression, gradient boosting, random forest
- Paid LLM inference: none
- Respondent-level plaintext emitted by the final baseline workflow: no

### Four-family harmonization

- Final workflow run: `33459614973`
- Common engine: `analysis_final/unified_analysis.py`
- Analysis source commit recorded by the package: `cca2318ae59edb607f6050f2093ac4698a094cf6`
- Bootstrap replicates: 10,000
- Bootstrap seed: `3108202691`
- LLM cells: 11
- Luna cells: 1,000 respondents each
- Claude cells: 250 respondents each
- Qwen cells: 1,000 respondents each
- DeepSeek cells: 1,000 respondents each
- Paid inference in harmonization: none
- Respondent-level plaintext in durable results: none

The common engine recovers the completed Luna and Claude outputs and recomputes their metrics and paired uncertainty under the same implementation used for Qwen and DeepSeek.

## Scientific interpretation

The evidence supports the following claim:

> Improving synthetic individuals does not guarantee improving synthetic populations.

This is a non-guarantee. It does not imply that individual improvement universally worsens population fidelity. DeepSeek provides a counterexample in which high reasoning improves Brier score, hard accuracy, prevalence fidelity, and joint population structure while log loss worsens because of rare extreme errors.

### Persona information

- Luna rich personas improve Brier and log loss while worsening hard-prevalence MAE.
- Claude rich personas improve Brier, log loss, hard accuracy, and hard-prevalence MAE while worsening probability-prevalence MAE.

The aggregate effect therefore depends on the population representation being evaluated.

### Reasoning

- Qwen medium reasoning improves Brier and log loss while worsening hard accuracy and both prevalence metrics.
- DeepSeek high reasoning under rich personas improves Brier, hard accuracy, probability prevalence, hard prevalence, and joint structure while worsening log loss.
- The paired DeepSeek-minus-Qwen reasoning interaction is strong for log loss, hard accuracy, probability-prevalence MAE, and hard-prevalence MAE; the Brier interaction crosses zero.

Reasoning effects are model-dependent rather than uniformly beneficial or harmful.

### Persona × reasoning interaction

The DeepSeek factorial yields a significant positive Brier interaction and a significant negative hard-prevalence-MAE interaction. Reasoning substitutes for some missing persona information on individual Brier, while rich persona information complements reasoning for hard population reconstruction.

### Joint structure

Human CAMS contains 14 observed six-outcome hard-response patterns and 2.486 bits of weighted entropy. Qwen medium reasoning slightly worsens joint total variation relative to reasoning off, whereas DeepSeek high reasoning sharply improves joint structure. DeepSeek rich/high reaches joint TV of approximately 0.190, compared with approximately 0.626 for rich/off.

### Probability tails

DeepSeek rich/high improves Brier while worsening log loss by approximately 0.419. Its wrong-extreme probability share rises from approximately 2.02% to 6.48%, explaining the divergence between the two proper scoring rules.

### Supervised references

The supervised references also show estimand dependence. Random forest and gradient boosting are strongest on Brier, logistic regression is strongest among them on hard-prevalence MAE and joint TV, and the weighted-prevalence predictor nearly reproduces probability prevalence while performing poorly on hard and joint population structure.

These supervised models are outcome-trained, cross-fitted reference points rather than information-regime-equivalent substitutes for zero-shot LLM simulation.

## Durable packages

Canonical aggregate results are stored in `analysis_final/results/` and include:

- `MANIFEST.json`
- `summary.json`
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

The package is aggregate-only and checksum-manifested.

The figure package is stored in `analysis_final/figures/`. It contains eight figures in PDF, SVG, and 600-dpi PNG, with a checksum manifest linked to the exact result manifest used for rendering.

## Privacy and reproducibility boundary

Version 1.0.0 preserves the following controls:

- no API keys are committed;
- no respondent-level plaintext result files are committed under the final analysis package;
- no raw LLM output files are committed under `analysis_final/results/` or `analysis_final/figures/`;
- historical raw outputs remain encrypted;
- CAMS outcome truth enters only after model generation outputs are frozen;
- final harmonization uses completed encrypted outputs without new inference;
- aggregate result files and figure files have SHA-256 checksums;
- figure generation reads committed aggregate files only.

`analysis_final/final_qa.py` is the machine-readable integrity gate for this frozen artifact.