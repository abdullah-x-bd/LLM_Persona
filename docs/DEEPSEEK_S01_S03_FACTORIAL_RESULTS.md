# DeepSeek S01 + S03 factorial results

Status: complete truth-linked analysis. Generation and analysis are complete for 1,000 CAMS respondents in all four cells: thin/off, thin/high, rich/off, rich/high. All 4,000 model outputs were completed before the withheld CAMS truth was loaded. Analysis uses CAMS `analysis_weight`, 10,000 paired respondent bootstrap replicates, and seed `3108202603`. The analysis workflow performed zero paid inference and emitted aggregate results only.

## Cell metrics

| Arm | Brier | Log loss | Hard accuracy | Probability prevalence MAE | Hard prevalence MAE | Mean abs(p-0.5) |
|---|---:|---:|---:|---:|---:|---:|
| thin/off | 0.223894 | 1.117611 | 71.282% | 14.065 pp | 21.374 pp | 0.36936 |
| thin/high | 0.188500 | 0.935309 | 76.421% | 6.222 pp | 9.335 pp | 0.38540 |
| rich/off | 0.204862 | 0.834312 | 73.319% | 12.750 pp | 20.274 pp | 0.36837 |
| rich/high | 0.186902 | 1.253580 | 77.687% | 6.987 pp | 3.600 pp | 0.40008 |

## Primary factorial contrasts

### Individual Brier

- Thin reasoning, high minus off: -0.035394, 95% CI [-0.045299, -0.025248].
- Rich reasoning, high minus off: -0.017959, 95% CI [-0.031007, -0.004898].
- Rich minus thin with reasoning off: -0.019032, 95% CI [-0.027926, -0.010345].
- Rich minus thin with high reasoning: -0.001597, 95% CI [-0.014567, 0.011391].
- Persona x reasoning interaction: +0.017435, 95% CI [+0.003274, +0.031541]. Reasoning improves Brier more when persona information is thin.

### Probability prevalence MAE

- Thin reasoning: -7.844 pp, 95% CI [-8.566, -6.804] pp.
- Rich reasoning: -5.763 pp, 95% CI [-8.314, -3.187] pp.
- Rich minus thin with reasoning off: -1.315 pp, 95% CI [-1.936, -0.712] pp.
- Rich minus thin with high reasoning: +0.765 pp, 95% CI [-1.740, +2.855] pp.
- Persona x reasoning interaction: +2.081 pp, 95% CI [-0.434, +4.245] pp.

### Hard prevalence MAE

- Thin reasoning: -12.038 pp, 95% CI [-13.202, -10.907] pp.
- Rich reasoning: -16.674 pp, 95% CI [-18.171, -13.918] pp.
- Rich minus thin with reasoning off: -1.100 pp, 95% CI [-1.848, -0.334] pp.
- Rich minus thin with high reasoning: -5.735 pp, 95% CI [-7.293, -2.987] pp.
- Persona x reasoning interaction: -4.636 pp, 95% CI [-6.322, -1.720] pp.

### Hard accuracy

- Thin reasoning: +5.139 pp, 95% CI [+3.745, +6.472] pp.
- Rich reasoning: +4.368 pp, 95% CI [+2.637, +6.131] pp.
- Rich minus thin with reasoning off: +2.038 pp, 95% CI [+1.021, +3.053] pp.
- Rich minus thin with high reasoning: +1.267 pp, 95% CI [-0.316, +2.872] pp.
- Persona x reasoning interaction: -0.771 pp, 95% CI [-2.522, +0.964] pp.

### Log loss: major metric reversal

- Thin reasoning improves log loss by -0.182302, 95% CI [-0.30898, -0.05576].
- Rich reasoning worsens log loss by +0.419267, 95% CI [+0.26942, +0.57299].
- Persona x reasoning interaction: +0.601569, 95% CI [+0.41376, +0.78925].

Thus rich/high is better than rich/off on Brier, hard accuracy, probability prevalence MAE, hard prevalence MAE, ECE, and joint population structure, but much worse on log loss.

## Why Brier and log loss disagree

Rich/high becomes substantially more extreme and incurs more rare catastrophic probability errors.

| Diagnostic | rich/off | rich/high |
|---|---:|---:|
| p <= .01 or >= .99 | 10.53% | 30.44% |
| wrong extreme probability | 2.02% | 6.48% |
| exact 0 or 1 | 10.03% | 27.13% |
| item log loss > 5 | 2.00% | 6.22% |
| item log loss > 10 | 2.00% | 6.22% |

DeepSeek high reasoning therefore improves average squared probability error while creating a heavier tail of highly confident mistakes, which log loss penalizes much more strongly.

## Joint population structure

Human weighted response distribution:
- 14 distinct patterns
- entropy 2.4857 bits
- largest archetype 28.72%

| Arm | Distinct patterns | Entropy | TV from human | JS from human | Correlation RMSE | Largest archetype |
|---|---:|---:|---:|---:|---:|---:|
| thin/off | 7 | 1.2834 | 0.6580 | 0.4098 | 0.2761 | 60.50% |
| thin/high | 7 | 2.1764 | 0.2851 | 0.0933 | 0.1285 | 31.83% |
| rich/off | 6 | 1.3068 | 0.6260 | 0.3894 | 0.2738 | 66.71% |
| rich/high | 7 | 2.2979 | 0.1900 | 0.0565 | 0.0841 | 29.08% |

DeepSeek high reasoning massively improves joint population fidelity. Rich/high comes close to the human population in entropy and maximum archetype share, although it still underproduces the human-dominant `110111` phone-first phenotype (13.02% synthetic versus 28.72% human) and overproduces `110110` (25.84% versus 11.81%).

Reasoning also changes the underlying synthetic respondent substantially:
- Thin personas: 48.39% weighted share changes hard six-answer pattern; weighted mean absolute probability change 15.99 pp.
- Rich personas: 62.50% changes hard pattern; weighted mean absolute probability change 21.66 pp.

## Outcome-level residual failure

Rich/high hard prevalence is close to truth for five outcomes, but copy-paste remains a large residual error.

Hard prevalence absolute errors for rich/high:
- computer ability: 0.38 pp
- recent mobile use: 0.19 pp
- mobile ability: 0.81 pp
- recent internet use: 1.30 pp
- internet ability: 3.10 pp
- copy-paste: 15.82 pp

Thus reasoning improves the population dramatically without eliminating the model's distorted latent representation of digital competence.

## Retry sensitivity

First-pass validity rates:
- thin/off 97.8%
- thin/high 82.2%
- rich/off 98.4%
- rich/high 67.9%

There are 553 respondents whose outputs were first-pass valid in all four cells. The core findings persist in this subset:
- thin reasoning Brier: -0.04048, 95% CI [-0.05443, -0.02654]
- rich reasoning Brier: -0.02513, 95% CI [-0.04262, -0.00706]
- thin reasoning probability prevalence MAE: -7.766 pp, 95% CI [-8.804, -6.606] pp
- rich reasoning probability prevalence MAE: -6.701 pp, 95% CI [-10.009, -3.259] pp
- thin reasoning hard prevalence MAE: -12.136 pp, 95% CI [-13.702, -10.605] pp
- rich reasoning hard prevalence MAE: -16.743 pp, 95% CI [-18.757, -13.120] pp
- thin reasoning hard accuracy: +5.928 pp, 95% CI [+4.035, +7.770] pp
- rich reasoning hard accuracy: +4.743 pp, 95% CI [+2.354, +7.086] pp
- thin reasoning log loss: -0.24394, 95% CI [-0.41432, -0.08442]
- rich reasoning log loss: +0.33209, 95% CI [+0.12742, +0.54287]

The main findings are therefore not artifacts of retry-only respondents.

## Age heterogeneity: a cross-model clue

DeepSeek high reasoning has strongly age-dependent effects under rich personas.

### Rich high minus rich off

| Age | Brier change | 95% CI | Probability prevalence MAE change | 95% CI | Hard prevalence MAE change | 95% CI | Hard accuracy change | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15-24 | +0.0219 | [-0.0035,+0.0483] | +1.70 pp | [-0.90,+4.62] | -3.42 pp | [-7.77,+0.93] | -2.75 pp | [-5.98,+0.41] |
| 25-34 | +0.0236 | [+0.0008,+0.0469] | +3.20 pp | [-0.90,+5.92] | -5.75 pp | [-10.69,-0.08] | -2.31 pp | [-5.45,+0.83] |
| 35-44 | +0.0039 | [-0.0228,+0.0302] | -5.35 pp | [-9.17,-0.81] | -14.74 pp | [-16.50,-9.65] | +1.23 pp | [-2.27,+4.66] |
| 45-59 | -0.0623 | [-0.0929,-0.0318] | -17.35 pp | [-19.80,-13.57] | -22.48 pp | [-26.06,-18.82] | +11.79 pp | [+7.88,+15.70] |
| 60+ | -0.1159 | [-0.1536,-0.0771] | -26.90 pp | [-29.52,-21.85] | -30.83 pp | [-34.76,-25.24] | +20.36 pp | [+15.12,+25.59] |

This is not a simple universally significant young-versus-old reversal: for ages 15-24 the rich-reasoning Brier/probability worsening is uncertain, while ages 25-34 show a statistically clear Brier worsening and a clear hard-prevalence improvement. From age 35 onward population-prevalence effects become beneficial, and the improvements are very large and precise for ages 45+.

The direction is nonetheless notable because the earlier Qwen experiment also showed reasoning worsening probability-population fidelity among younger respondents and improving it among older respondents. This cross-model age pattern should be treated as a secondary/exploratory replication unless it was prospectively specified for DeepSeek.

## Interpretation for the umbrella paper

The DeepSeek experiment directly rejects any simple claim that reasoning itself generally damages synthetic population fidelity. With DeepSeek, high reasoning dramatically improves individual Brier, hard accuracy, marginal prevalence fidelity, and joint population structure. This is the opposite of the earlier Qwen population-level result.

The stronger cross-study conclusion is therefore:

> Improvements in individual synthetic-person fidelity do not reliably determine population fidelity. The mapping from individual improvement to population improvement is model-, metric-, persona-, and subgroup-dependent.

The result also strengthens a second conclusion:

> Synthetic-population fidelity is not scalar. Brier, log loss, hard accuracy, marginal prevalence, joint-distribution fidelity, and subgroup fidelity can disagree sharply even within the same model and treatment.

The exact paper title `Better synthetic individuals do not make better synthetic populations` is memorable, but it should be interpreted as a non-guarantee rather than an absolute empirical law. A literal universal reading is falsified by the DeepSeek experiment, where better individual Brier coincides with substantially better population fidelity on several endpoints.
