# Final repo-wide empirical synthesis

## Central result

The completed truth-linked CAMS program supports a precise methodological conclusion:

**Improving synthetic individuals does not guarantee improving synthetic populations.**

Individual predictive fidelity and population fidelity are distinct validation targets. Across Luna, Claude, Qwen, and DeepSeek, interventions that improve respondent-level Brier score or log loss can improve, worsen, or leave uncertain the fidelity of marginal prevalence, categorical population totals, joint response structure, and subgroup patterns. The direction depends on model family, intervention, metric, and subgroup.

This is a non-guarantee, not a universal claim that better individual prediction must damage population reconstruction. DeepSeek is an important counterexample: high reasoning improves individual Brier and several population-level endpoints while simultaneously worsening log loss through a heavier tail of highly confident errors.

## Final evidence set

All values below come from the final common-engine, zero-inference synthesis in `analysis_final/results/`. Original frozen analyses remain authoritative for their preregistered primary claims, while this layer provides a common metric implementation for cross-study comparison.

| Evidence family | Model | Design | Respondents | Final role |
|---|---|---|---:|---|
| Persona information | GPT-5.6 Luna | thin vs rich | 1,000 paired | truth-linked primary evidence |
| Persona robustness | Claude Sonnet 5 | thin vs rich | 250 paired | truth-linked robustness evidence |
| Reasoning | Qwen3.8-27B | off / low / medium | 1,000 paired | truth-linked primary reasoning evidence |
| S01 reasoning replication | DeepSeek V4 Flash 0731 | rich/off vs rich/high | 1,000 paired | truth-linked model-family replication |
| S03 factorial | DeepSeek V4 Flash 0731 | thin/rich × off/high | 1,000 | truth-linked factorial mechanism test |
| Supervised references | prevalence, logistic, gradient boosting, random forest | 10-fold cross-fitted | 1,000 | supervised comparison only |

CMS and PLFS synthetic-output branches remain useful as model-instability and engineering evidence. They are excluded from truth-linked accuracy claims because the repository does not contain the matched truth assets needed for the final paper.

## One common analysis engine

The final synthesis reconstructs all 11 completed LLM cells from the authoritative completed outputs and evaluates them against the same CAMS truth infrastructure. Luna and Claude are no longer represented only by carried-forward point estimates in the canonical package.

The harmonized analysis uses:

- survey weights throughout;
- one metric implementation across all four LLM families;
- log-loss clipping at `1e-6` for harmonized comparisons;
- 10,000 paired respondent bootstrap replicates;
- bootstrap seed `3108202691`;
- aggregate-only durable outputs.

The final harmonization workflow performs no paid LLM inference.

## Persona information

### Luna, rich minus thin

| Metric | Effect | 95% paired bootstrap CI |
|---|---:|---:|
| Individual Brier | -0.01866 | [-0.02418, -0.01333] |
| Log loss | -0.05510 | [-0.07136, -0.03964] |
| Hard accuracy | +0.97 pp | [-0.02, +1.98] pp |
| Probability-prevalence MAE | -0.52 pp | [-2.23, +0.50] pp |
| Hard-prevalence MAE | +3.20 pp | [+2.24, +4.13] pp |

Richer Luna personas clearly improve respondent-level probabilistic prediction. The corresponding change in probability-prevalence MAE is uncertain, while hard categorical population reconstruction becomes significantly worse.

This is the cleanest within-model example of the paper's central non-guarantee: a strong individual-level improvement coexists with a clear deterioration in one population estimand.

### Claude, rich minus thin

| Metric | Effect | 95% paired bootstrap CI |
|---|---:|---:|
| Individual Brier | -0.01457 | [-0.02537, -0.00383] |
| Log loss | -0.03296 | [-0.06139, -0.00487] |
| Hard accuracy | +3.60 pp | [+1.26, +5.93] pp |
| Probability-prevalence MAE | +1.06 pp | [+0.10, +3.23] pp |
| Hard-prevalence MAE | -4.41 pp | [-7.14, -1.36] pp |

Claude shows a different aggregate pattern. Rich personas improve Brier, log loss, hard accuracy, and hard-prevalence MAE, but significantly worsen population prevalence when the population estimate is formed from mean predicted probabilities.

The Luna and Claude comparison therefore rejects a scalar notion of population fidelity. Even the sign of the aggregate effect can depend on how the synthetic responses are represented.

## Reasoning is strongly model-dependent

### Qwen medium reasoning minus off

| Metric | Effect | 95% paired bootstrap CI |
|---|---:|---:|
| Individual Brier | -0.01318 | [-0.01883, -0.00767] |
| Log loss | -0.08562 | [-0.10424, -0.06738] |
| Hard accuracy | -1.77 pp | [-2.64, -0.88] pp |
| Probability-prevalence MAE | +1.02 pp | [+0.33, +1.80] pp |
| Hard-prevalence MAE | +3.71 pp | [+2.89, +4.53] pp |

Qwen reasoning improves both proper respondent-level probability scores, but worsens hard accuracy and both population-prevalence endpoints. It also reduces probability extremeness, so the result is not simply greater confidence producing better-looking individual scores.

### DeepSeek high reasoning minus off under rich personas

| Metric | Effect | 95% paired bootstrap CI |
|---|---:|---:|
| Individual Brier | -0.01796 | [-0.03087, -0.00483] |
| Log loss | +0.41927 | [+0.26528, +0.57485] |
| Hard accuracy | +4.37 pp | [+2.65, +6.07] pp |
| Probability-prevalence MAE | -5.76 pp | [-8.32, -3.27] pp |
| Hard-prevalence MAE | -16.67 pp | [-18.19, -13.98] pp |

DeepSeek produces nearly the opposite population result. High reasoning improves Brier, accuracy, probability prevalence, hard prevalence, and joint population structure, while log loss becomes dramatically worse.

### Direct Qwen-versus-DeepSeek reasoning interaction

Because Qwen and DeepSeek share the same 1,000 CAMS respondents, the difference in reasoning effects is estimated directly rather than inferred from separate confidence intervals. The contrast is:

`(DeepSeek rich/high - rich/off) - (Qwen medium - off)`

| Metric | Difference in reasoning effects | 95% paired bootstrap CI |
|---|---:|---:|
| Individual Brier | -0.00478 | [-0.01917, +0.01011] |
| Log loss | +0.50488 | [+0.35066, +0.66182] |
| Hard accuracy | +6.14 pp | [+4.19, +8.07] pp |
| Probability-prevalence MAE | -6.79 pp | [-9.08, -4.52] pp |
| Hard-prevalence MAE | -20.38 pp | [-22.04, -17.46] pp |

The Brier interaction itself is uncertain, but the consequences of reasoning for log loss, hard accuracy, and both prevalence metrics differ sharply and precisely across the two model families.

The appropriate conclusion is therefore not that reasoning is intrinsically beneficial or harmful. Reasoning changes the synthetic population in a model-dependent way.

## DeepSeek persona × reasoning factorial

The DeepSeek four-cell design separates persona-information effects from reasoning effects.

The factorial interaction is defined as:

`(rich/high - rich/off) - (thin/high - thin/off)`

| Metric | Interaction | 95% paired bootstrap CI |
|---|---:|---:|
| Individual Brier | +0.01743 | [+0.00311, +0.03138] |
| Log loss | +0.60157 | [+0.41454, +0.78497] |
| Hard accuracy | -0.77 pp | [-2.49, +0.98] pp |
| Probability-prevalence MAE | +2.08 pp | [-0.49, +4.17] pp |
| Hard-prevalence MAE | -4.64 pp | [-6.35, -1.77] pp |

Reasoning improves Brier more when persona information is thin. For hard population reconstruction, however, rich persona information complements reasoning: the hard-prevalence improvement from reasoning is significantly larger under rich personas.

The same factorial therefore contains substitution on one validation target and complementarity on another.

## Probability-tail reversal

DeepSeek rich/high illustrates why one proper score cannot stand in for another.

| Diagnostic | Rich/off | Rich/high |
|---|---:|---:|
| Extreme probability share | 10.53% | 30.44% |
| Wrong extreme share | 2.02% | 6.48% |
| Exact 0 or 1 share | 10.03% | 27.13% |
| Item log loss > 5 | 2.00% | 6.22% |
| Item log loss > 10 | 2.00% | 6.22% |

High reasoning lowers average squared probability error but creates a substantially heavier tail of confidently wrong predictions. Brier improves while log loss worsens because log loss assigns much greater penalty to those rare extreme mistakes.

Qwen moves in the opposite confidence direction: medium reasoning reduces both the extreme-probability share and the wrong-extreme share.

## Joint population structure

The real CAMS population contains 14 observed six-outcome hard-response patterns, with weighted entropy of 2.486 bits and a largest-pattern share of 28.72%.

| Cell | Entropy | Joint TV from human | Joint JS | Correlation RMSE |
|---|---:|---:|---:|---:|
| Luna thin | 1.930 | 0.480 | 0.296 | 0.258 |
| Luna rich | 1.784 | 0.548 | 0.344 | 0.246 |
| Claude thin | 1.754 | 0.390 | 0.259 | 0.226 |
| Claude rich | 1.962 | 0.363 | 0.226 | 0.208 |
| Qwen off | 1.965 | 0.395 | 0.232 | 0.212 |
| Qwen medium | 1.892 | 0.417 | 0.238 | 0.240 |
| DeepSeek thin/off | 1.283 | 0.658 | 0.410 | 0.302 |
| DeepSeek thin/high | 2.176 | 0.285 | 0.093 | 0.141 |
| DeepSeek rich/off | 1.307 | 0.626 | 0.389 | 0.300 |
| DeepSeek rich/high | 2.298 | 0.190 | 0.056 | 0.092 |

The joint-distribution result reinforces the cross-model reasoning reversal. Qwen medium reasoning slightly worsens joint TV and correlation structure relative to off. DeepSeek high reasoning sharply improves both thin and rich cells, with rich/high approaching the human entropy and dominant-pattern share much more closely.

The models still make structurally meaningful errors. In particular, the human phone-first digital phenotype is underrepresented even in the strongest DeepSeek cell, so strong marginal performance does not imply full recovery of the latent joint population.

## Age heterogeneity

Age-specific reasoning effects are secondary or exploratory unless prospectively specified in the relevant original study. They are nevertheless notable because related structure appears across model families.

For Qwen, reasoning worsens probability-prevalence fidelity among respondents aged 15-24 and 25-34, is approximately neutral around ages 35-44, and becomes beneficial or near-beneficial in older groups.

For DeepSeek rich personas, high reasoning also performs poorly for younger respondents on some individual or probability endpoints, while population-prevalence effects become increasingly beneficial from age 35 onward and are very large for ages 45+.

This cross-model age pattern is a useful mechanism hypothesis, not a license to convert exploratory subgroup findings into a new primary claim.

## Supervised reference models

The supervised models are 10-fold cross-fitted reference points trained with labeled outcomes. They are not information-regime-equivalent substitutes for zero-shot LLM simulation.

| Model | Brier | Log loss | Hard accuracy | Probability-prevalence MAE | Hard-prevalence MAE | Joint TV |
|---|---:|---:|---:|---:|---:|---:|
| Gradient boosting | 0.12242 | 0.38779 | 82.53% | 0.46 pp | 3.88 pp | 0.168 |
| Logistic regression | 0.12917 | 0.44944 | 81.86% | 0.38 pp | 3.47 pp | 0.138 |
| Random forest | 0.12238 | 0.38607 | 82.55% | 0.08 pp | 8.72 pp | 0.242 |
| Weighted prevalence | 0.18562 | 0.55131 | 71.10% | ~0.00 pp | 28.90 pp | 0.882 |

The baseline comparison makes the same methodological point from another direction. The model with nearly perfect probability-prevalence reproduction can be extremely poor at hard-population and joint-distribution reconstruction. The lowest Brier does not coincide with the best hard-prevalence or joint-TV score.

There is no single universally best synthetic-population model without first specifying the estimand.

## Evidence hierarchy

### Primary and confirmatory evidence

- Luna thin-versus-rich CAMS persona experiment under its frozen design.
- Claude thin-versus-rich matched robustness experiment under its frozen design.
- Qwen off/low/medium reasoning experiment under its frozen analysis plan.
- DeepSeek S01 rich/off-versus-rich/high replication.
- DeepSeek S03 persona × reasoning factorial.

### Cross-study harmonized inference

- common-engine cell metrics across all 11 LLM cells;
- 10,000 paired-bootstrap persona and reasoning contrasts;
- direct Qwen-versus-DeepSeek model × reasoning heterogeneity;
- common joint-distribution metrics;
- cross-fitted supervised reference models.

### Secondary or mechanistic evidence

- age and demographic heterogeneity;
- response-pattern fingerprints;
- probability-tail diagnostics;
- retry and first-pass sensitivity analyses;
- outcome-level residual failure patterns.

### Excluded from truth-linked accuracy claims

- CMS and PLFS branches without matched truth assets in the current repository;
- Gemini/provider-failure branches;
- S02 and S05, which remain unrun prospective designs;
- S04, which is scientifically blocked without matched PLFS truth.

## Final interpretation

The repository supports a multi-axis view of synthetic-population validation. Persona information, inference-time reasoning, and model identity alter not only how much error a synthetic respondent makes, but the structure of that error.

A system can improve individual Brier while worsening population prevalence. It can improve one population representation while worsening another. It can recover marginals while distorting the joint distribution. It can improve average probability error while creating catastrophic tail errors. The direction of these trade-offs can reverse across model families.

The practical implication is simple: **synthetic respondents must be validated against the estimand for which they will actually be used**. Individual prediction metrics alone are insufficient evidence that a synthetic population is fit for population-level inference.
