# Pre-manuscript audit

## Status

**Scientific evidence generation for the current manuscript is frozen.**

The completed truth-linked CAMS evidence, conventional statistical baselines, four-family harmonized analysis, durable aggregate result package, and final R publication figure suite are complete. No additional paid LLM inference is required for the current paper.

The remaining work after this repository freeze is manuscript writing, journal-specific formatting, and any genuinely new analysis requested by reviewers.

## Final evidence boundary

| Component | Final status |
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
| Durable aggregate result package | complete |
| Eight-figure R publication package | complete |
| S02 | archived unrun, excluded from current paper |
| S04 | scientifically blocked, excluded from current paper |
| S05 | archived unrun, excluded from current paper |
| Additional paid inference | not required |

## Final zero-inference analysis checks

### Statistical baselines

- Successful workflow run: `33415197392`
- Artifact: `9766982262`
- Respondents: 1,000
- Outer folds: 10
- Bootstrap replicates: 10,000
- Reference models: weighted prevalence, logistic regression, gradient boosting, random forest
- Paid LLM inference: none
- Respondent-level plaintext emitted by final baseline workflow: no

### Four-family harmonization

- Successful final workflow run: `33459614973`
- Common engine: `analysis_final/unified_analysis.py`
- Analysis source commit recorded by the package: `cca2318ae59edb607f6050f2093ac4698a094cf6`
- Bootstrap replicates: 10,000
- Bootstrap seed: `3108202691`
- LLM cells: 11
- Luna cells: 1,000 respondents each
- Claude cells: 250 respondents each
- Qwen cells: 1,000 respondents each
- DeepSeek cells: 1,000 respondents each
- Paid inference performed: false
- Respondent-level plaintext emitted into durable results: false
- Legacy Luna/Claude point-estimate-only treatment: removed from canonical final package

The final common engine recovers the already-completed Luna and Claude outputs and recomputes their metrics and paired uncertainty under the same implementation used for Qwen and DeepSeek.

## Final scientific checks

### Central claim is correctly scoped

The final evidence supports:

> Improving synthetic individuals does not guarantee improving synthetic populations.

The paper should not claim that individual improvement universally worsens population fidelity. DeepSeek shows that high reasoning can improve Brier, hard accuracy, prevalence fidelity, and joint population structure at the same time, even while log loss becomes much worse because of rare extreme errors.

### Persona information is not scalar

- Luna rich personas significantly improve Brier and log loss but significantly worsen hard-prevalence MAE.
- Claude rich personas significantly improve Brier, log loss, hard accuracy, and hard-prevalence MAE while significantly worsening probability-prevalence MAE.

The aggregate conclusion therefore depends on the target population representation.

### Reasoning is model-dependent

- Qwen medium reasoning improves Brier/log loss but worsens hard accuracy and both prevalence metrics.
- DeepSeek high reasoning under rich personas improves Brier, hard accuracy, probability prevalence, hard prevalence, and joint structure, but substantially worsens log loss.
- The paired DeepSeek-minus-Qwen reasoning interaction is strong for log loss, hard accuracy, probability-prevalence MAE, and hard-prevalence MAE; the Brier interaction crosses zero.

### Persona × reasoning interaction is real but metric-dependent

The DeepSeek factorial shows a significant positive Brier interaction and a significant negative hard-prevalence-MAE interaction. Reasoning substitutes for some missing persona information on individual Brier while rich persona information complements reasoning for hard population reconstruction.

### Joint-distribution validation changes the ranking

Human CAMS has 14 observed hard-response patterns and 2.486 bits of weighted entropy. Qwen reasoning slightly worsens joint TV relative to off, while DeepSeek high reasoning sharply improves joint structure. DeepSeek rich/high reaches joint TV about 0.190, compared with about 0.626 for rich/off.

### Proper scores can disagree sharply

DeepSeek rich/high improves Brier but worsens log loss by about 0.419. Its wrong-extreme probability share rises from about 2.02% to 6.48%. The paper must preserve this tail-risk interpretation rather than describing reasoning as uniformly improving probabilistic fidelity.

### Supervised baselines reinforce estimand dependence

The supervised references do not yield one universally best method. Random forest and gradient boosting are strongest on Brier, logistic regression is strongest among them on hard-prevalence MAE and joint TV, and the weighted-prevalence predictor nearly exactly reproduces probability prevalence while performing very poorly on hard and joint population structure.

The supervised models are labeled-outcome cross-fitted references, not information-regime-equivalent substitutes for zero-shot LLM simulation.

## Durable result package

Canonical location: `analysis_final/results/`

Expected files:

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

The result package is aggregate-only and checksum-manifested. It is committed to the repository so the manuscript does not depend on expiring GitHub Actions artifacts.

## Final figure package

Successful workflow run: `33459804925`

Canonical location: `analysis_final/figures/`

The package contains eight figures:

1. `fig01_micro_macro`
2. `fig02_reasoning_reversal`
3. `fig03_deepseek_factorial`
4. `fig04_age_gradient`
5. `fig05_population_fingerprint`
6. `fig06_fidelity_landscape`
7. `fig07_overconfidence`
8. `fig08_outcome_effects`

Each is committed in PDF, SVG, and 600-dpi PNG. The figure package contains no embedded plot titles and includes a checksum manifest linked to the exact result manifest used for rendering.

The earlier figure-run failure is superseded. The final figure run passed rendering, figure integrity, repo commit, and artifact upload.

## Privacy and reproducibility audit

The final package satisfies the intended data firewall:

- no API keys are committed;
- no respondent-level plaintext result files are committed under the final analysis package;
- no raw LLM output files are committed under `analysis_final/results/` or `analysis_final/figures/`;
- historical raw outputs remain encrypted;
- truth is joined only after generation outputs are frozen;
- final harmonization uses historical encrypted outputs without new inference;
- durable result files have SHA-256 checksums;
- durable figure files have SHA-256 checksums;
- figure inputs are committed aggregate files only.

## Documentation audit

The current manuscript hierarchy is:

- `README.md`
- `docs/PRE_MANUSCRIPT_AUDIT.md`
- `docs/REPO_WIDE_RESULTS_SYNTHESIS.md`
- `docs/FINAL_PROVENANCE.md`
- `docs/REPO_MAP.md`
- `analysis_final/README.md`
- `studies/registry.json`

Historical plans and repair workflows remain in the repository for provenance. They do not represent pending current-paper work.

## Manuscript-use rules

When writing the paper:

1. use `analysis_final/results/` for final common-engine numbers;
2. use original frozen study analyses when reporting a study's preregistered primary result exactly as originally defined;
3. distinguish primary/confirmatory evidence from secondary subgroup or mechanism analyses;
4. describe S02 and S05 as unrun prospective designs if mentioned at all;
5. describe S04 as scientifically blocked/excluded, not as a negative replication;
6. do not describe CMS/PLFS branches as truth-linked accuracy evidence without matched truth assets;
7. describe the title claim as a non-guarantee, not a universal impossibility result;
8. keep supervised baselines clearly labeled as supervised cross-fitted references.

## Final machine gate

`analysis_final/final_qa.py` is the canonical machine-readable freeze test. The final repository QA workflow must pass this gate after the last documentation and figure commits. Once that workflow is green, the repository is technically frozen for manuscript preparation.
