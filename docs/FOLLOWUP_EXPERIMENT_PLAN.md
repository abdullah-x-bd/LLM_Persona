# Follow-up confirmatory experiment plan

## Umbrella claim under test

Improving an LLM's respondent-level probabilistic predictions does not imply improved synthetic-population fidelity. Individual prediction, aggregate prevalence, categorical prevalence, subgroup gaps, and joint population structure are distinct estimands and can move in different directions.

## Model-selection provenance

The first zero-cost follow-up gate considered `openai/gpt-oss-120b` for the second-model studies because of its low price. Current OpenRouter metadata marked reasoning as mandatory, which makes a genuine reasoning-off arm impossible. No paid inference had been performed. The second-model studies were therefore prospectively changed to `deepseek/deepseek-v4-flash-0731` before any follow-up results existed.

The corrected zero-cost gate verified that DeepSeek reasoning is optional, the pinned AkashML endpoint supports structured output, `max_tokens`, and reasoning, and DeepSeek supports `high` effort. DeepSeek studies therefore compare `off` versus `high`. Qwen studies retain `off` versus `medium` because those are the validated Qwen conditions.

## S01 Second-model reasoning replication

Population: the existing 1,000 frozen CAMS respondents.

Model: `deepseek/deepseek-v4-flash-0731`.

Design: rich persona, paired reasoning off versus high. Completion caps are 256 off and 1,800 high.

Primary outcomes: survey-weighted individual Brier and probability-prevalence MAE.

Key secondary outcomes: hard prevalence MAE, hard accuracy, log loss, calibration-in-the-large, response entropy, TV/JS distance, subgroup errors, token use, latency, and finish reasons.

Interpretation: replication of the micro/macro divergence in another model family would rule out an explanation specific to Qwen's reasoning implementation.

Validated live hard single-pass ceiling on 31 August 2026: **$0.452429**. Registered cap: **$0.90**.

## S02 Length-safe Qwen replication

Population: the same 1,000 frozen CAMS respondents.

Model: `qwen/qwen3.8-27b`.

Design: rich persona, paired off versus medium reasoning, with 3,200 maximum completion tokens for medium and 256 for off.

Primary purpose: remove the major technical ambiguity created by length-limited attempts in the first Qwen run. The realized length-failure rate must be reported and the label `length-safe` withdrawn if the prespecified tolerance is not achieved.

Validated live hard single-pass ceiling on 31 August 2026: **$9.256217**. Registered cap: **$11.25**. This is a full-token worst case, not an expected cost.

## S03 Persona × reasoning factorial

Population: the same 1,000 frozen CAMS respondents.

Model: `deepseek/deepseek-v4-flash-0731`.

Cells: thin/off, thin/high, rich/off, rich/high.

Only thin/off and thin/high require new inference. Rich/off and rich/high are exactly S01 and must be reused rather than regenerated.

Primary estimand: paired difference-in-differences between the reasoning effect under thin and rich personas.

Mechanism hypothesis frozen prospectively: reasoning may depend more heavily on learned population priors when persona information is sparse, producing a different macro-fidelity effect under thin personas.

Validated live hard single-pass ceiling for the two new thin cells: **$0.430298**. Registered cap: **$0.85**.

## S04 PLFS cross-domain reasoning replication

Population: 1,000 deterministically selected respondents from the frozen PLFS 2023–24 persona bundle.

Model: `deepseek/deepseek-v4-flash-0731`.

Design: rich persona, paired reasoning off versus high.

Outcomes: labour-force participation, employment, unemployment, self-employment, regular salaried employment, casual labour.

Hard prerequisite: recover a separate matched PLFS truth bundle before production inference. The repository currently lacks this asset. Engineering-only proxy calls using existing PLFS personas may test schema, routing, latency, reasoning behavior, and cost but are discarded and do not count as S04 observations.

## S05 Fresh preregistered holdout

Population: 500 CAMS respondents excluded from all prior empirical work and from hypothesis formation.

Cells:

1. Qwen thin/off
2. Qwen rich/off
3. Qwen rich/medium with 3,200-token headroom
4. DeepSeek rich/off

This compact design simultaneously retests persona enrichment, reasoning, model identity, and joint-distribution compression on an untouched sample.

Hard prerequisite: freeze and hash new encrypted codes and truth bundles and prove respondent-ID disjointness from the original 1,000-person sample before scientific inference. Engineering-only proxy calls may use existing CAMS personas to test the exact model/provider/schema plumbing, but proxy outputs must be discarded and can never enter S05 analysis.

## Shared confirmatory analysis

Every truth-linked study should report at minimum:

- weighted individual Brier score;
- probability-prevalence MAE across the six outcomes;
- hard prevalence MAE;
- hard response accuracy;
- log loss;
- calibration-in-the-large;
- per-outcome prevalence error;
- response-pattern entropy;
- total variation and Jensen-Shannon distance from the human joint response distribution;
- subgroup errors for prespecified gender, rural/urban, and age groups where the source survey supports them;
- paired respondent bootstrap confidence intervals;
- first-pass and all-attempt finish-reason, retry, latency, reasoning-token, and completion-token diagnostics.

For reasoning studies, the primary comparison remains paired at respondent level. For S03 the factorial interaction is estimated directly rather than inferred from separate significance tests.

## Engineering micro-pilot requirement

Before any production launch, the exact payload path must pass a paid micro-pilot covering every treatment arm. The micro-pilot must verify:

1. model and endpoint identity;
2. provider fallback remains disabled;
3. structured JSON schema validity;
4. the intended reasoning state/effort is accepted;
5. completion and reasoning token accounting is returned;
6. finish reason is not unexpectedly `length`;
7. latency is recorded;
8. no human truth is loaded;
9. retry behavior is deterministic and bounded;
10. the measured cost is below both the pilot cap and the projected production ceiling.

The pilot is an engineering test only. Its model outputs are not inspected substantively and are not included in scientific analyses.

## Cost policy

The numerical values in `studies/registry.json` are planning values. The authoritative pre-spend number is produced by `studies/common/openrouter_preflight.py`, which reconstructs the exact request set, estimates conservative input tokens from actual prompts, reads live pinned-endpoint prices, sums the hard completion caps, and compares the number with the registered study cap.

A production launch is prohibited if the live hard single-pass ceiling exceeds its registered cap. The ordinary inference key currently has no per-key OpenRouter limit, so `/api/v1/key` cannot reveal the account-wide prepaid balance. Account credit must therefore also be checked separately before expensive runs.

## No-spend rule for incomplete evidence chains

S04 and S05 deliberately fail scientific readiness while their truth/holdout assets are absent. This is a scientific guardrail against paying for synthetic data that cannot answer the preregistered human-fidelity question. Their engineering proxy pilots do not alter this block.
