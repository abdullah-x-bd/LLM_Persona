# Frozen Study 1 analysis plan, version 3

Frozen before the full Study 1 production run for the reasoning-population-fidelity experiment.

Version 3 replaces the version-2 `off / low / xhigh` treatment with `off / low / medium` solely because paid engineering canaries demonstrated an operational incompatibility with the `xhigh` arm. In three canary attempts, `off` and `low` returned schema-valid structured responses while `xhigh` repeatedly failed to return a usable final structured response under completion ceilings compatible with the frozen Study 1 budget. No human CAMS truth was loaded for scoring, no predictive-performance metric was calculated, and no substantive model outputs were inspected to make this change. This is therefore an engineering and budget-feasibility correction under the pre-specified pilot firewall, not a result-driven treatment change.

Qwen3.8 27B exposes enabled reasoning efforts `xhigh`, `medium`, and `low`, while reasoning itself can be disabled. The final feasible treatment is therefore `off / low / medium`.

## Experimental unit and design

The analysis uses the same frozen 1,000 CAMS respondents in every reasoning condition. Each respondent receives the same persona, the same six survey questions, the same response schema, the same model, and the same deterministic generation settings. The only intended treatment variation is reasoning configuration: thinking disabled (`off`), enabled at `low`, or enabled at `medium`.

Each respondent therefore contributes three paired model responses. Human CAMS outcomes remain withheld from every model request and are joined only for analysis after response collection.

## Outcomes

The six prespecified binary outcomes are:

1. mobile_ability
2. mobile_3m
3. computer_ability
4. internet_ability
5. internet_3m
6. copy_paste

Each model response supplies both a hard yes/no answer and `probability_yes` in [0,1].

## Co-primary fidelity measures

### 1. Survey-weighted population prevalence MAE

For outcome j, let H_j be the survey-weighted human prevalence among the frozen 1,000 respondents. For reasoning condition c, let P_cj be the survey-weighted mean of the model's `probability_yes` values.

For each condition:

`population_probability_MAE_c = mean_j |P_cj - H_j|`

The reported scale is percentage points. Each of the six outcomes receives equal weight in the final mean.

The primary reasoning contrast is `medium - off`. A negative difference means the higher feasible reasoning treatment improved population fidelity. `low - off` and `medium - low` are prespecified secondary contrasts.

### 2. Individual probabilistic Brier score

For respondent i, outcome j, and reasoning condition c:

`Brier_ijc = (p_ijc - y_ij)^2`

The condition-level score is the survey-weighted mean over respondents and equal-weight mean over the six outcomes. Lower is better.

The primary reasoning contrast is again `medium - off`, with `low - off` and `medium - low` secondary.

## Secondary measures

1. Survey-weighted prevalence MAE using hard yes/no model answers.
2. Outcome-specific probability prevalence errors for all six outcomes.
3. Outcome-specific Brier scores.
4. Weighted hard-answer accuracy.
5. Weighted log loss after clipping probabilities to [0.001, 0.999].
6. Calibration-in-the-large, defined as weighted mean predicted probability minus weighted human prevalence.
7. Response-vector diversity across the 64 possible six-answer binary vectors.
8. Distributional distance between the weighted human and synthetic six-answer response-vector distributions, using total variation distance and Jensen-Shannon divergence.

## Subgroup analyses

Subgroup analyses are secondary and use only subgroup variables already present in the frozen truth bundle:

- sector: rural, urban
- gender: male, female
- age group: 15-24, 25-34, 35-44, 45-59, 60+

For each condition and subgroup, calculate probability-prevalence MAE across the six outcomes. Also calculate whether the synthetic subgroup gap reproduces the corresponding human subgroup gap for each outcome.

No new subgroup will be promoted to a primary analysis after model outputs are observed.

## Demographic overdetermination analysis

For each outcome and condition, quantify how strongly model probabilities vary across the prespecified sector, gender, and age groups, then compare those synthetic between-group differences with the observed human differences. The key quantity is excess synthetic gap magnitude relative to the human gap. This analysis is secondary and descriptive.

## Uncertainty

Use a paired respondent-cluster bootstrap with 10,000 replicates and seed `30082026`. A bootstrap replicate resamples respondents with replacement and carries all three reasoning-condition responses plus the respondent's six human outcomes and survey weight together.

Report percentile 95% bootstrap confidence intervals for condition-level metrics and paired contrasts. The main interpretation emphasizes effect sizes and confidence intervals rather than dichotomous significance labels.

## Missing or invalid model responses

The engineering pilot must achieve zero schema-validation failures before the full run is authorized.

During the full run, failed API requests are retried according to the frozen retry policy. A request is complete only when it yields a schema-valid response. The primary analysis requires all 3,000 unique respondent-condition requests. If provider failure prevents complete collection within the hard budget cap, report the achieved coverage and do not silently impute missing model outputs.

## Engineering pilot firewall

The paid engineering pilot is used only to inspect API compatibility, schema validity, provider routing, latency, reasoning-token accounting, prompt/completion token usage, retry behavior, and realized cost.

Do not calculate human-vs-model accuracy, prevalence error, Brier score, subgroup performance, or any other substantive outcome during the pilot. Pilot outputs must not be used to modify the prompt, persona, outcomes, reasoning conditions, primary metrics, or analysis direction based on observed predictive performance.

Changes after the pilot are permitted only for demonstrated engineering incompatibilities or budget feasibility. Any such change must be documented before the full run, must trigger a new request/config freeze hash, and must not be motivated by substantive fidelity results.

The move from `xhigh` to `medium` in version 3 is such a documented engineering change. The `xhigh` arm repeatedly exhausted or failed to expose usable final structured content under budget-compatible ceilings. The medium arm was selected because it is the next-highest native reasoning effort supported by the same model and remains compatible with the experiment's hard budget envelope.

## Generation configuration

Study 1 uses:

- model: `qwen/qwen3.8-27b`
- temperature: 0.0
- top_p: 1.0
- strict JSON-schema structured output
- reasoning treatments: off, low, medium
- off treatment: `reasoning.enabled = false`
- low treatment: `reasoning.effort = low`
- medium treatment: `reasoning.effort = medium`
- completion ceilings: 250, 600, 1200 tokens respectively

Reasoning text is excluded from returned pilot/full-run content, while reasoning-token usage remains measurable in provider accounting. Provider routing remains bounded by the frozen maximum price policy and data-collection policy.

## Analysis order after the full run

1. Verify the full-run manifest and all freeze hashes.
2. Verify exactly 3,000 unique successful requests and 1,000 complete respondent triplets.
3. Join model outputs to frozen human truth by anonymous respondent ID.
4. Compute co-primary metrics without subgroup slicing.
5. Compute the primary `medium - off` paired contrasts.
6. Compute the prespecified secondary reasoning contrasts.
7. Compute outcome-level secondary measures.
8. Compute subgroup and demographic-overdetermination analyses.
9. Run the prespecified Study 2 cross-model robustness experiment only if budget remains and Study 1 is complete.
