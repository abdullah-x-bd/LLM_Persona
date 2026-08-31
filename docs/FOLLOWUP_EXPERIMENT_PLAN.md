# Follow-up confirmatory experiment plan

## Umbrella claim under test

Improving an LLM's respondent-level probabilistic predictions does not imply improved synthetic-population fidelity. Individual prediction, aggregate prevalence, categorical prevalence, subgroup gaps, and joint population structure are distinct estimands and can move in different directions.

## S01 Second-model reasoning replication

Population: the existing 1,000 frozen CAMS respondents.

Model: `openai/gpt-oss-120b`.

Design: rich persona, paired reasoning off versus medium.

Primary outcomes: survey-weighted individual Brier and probability-prevalence MAE.

Key secondary outcomes: hard prevalence MAE, hard accuracy, log loss, calibration, response entropy, TV/JS distance, subgroup errors.

Interpretation: a replication of better Brier with no corresponding macro improvement would rule out an explanation specific to Qwen's reasoning implementation.

## S02 Length-safe Qwen replication

Population: the same 1,000 frozen CAMS respondents.

Model: `qwen/qwen3.8-27b`.

Design: rich persona, paired off versus medium reasoning, with 3,200 maximum completion tokens for medium.

Primary purpose: remove the major technical ambiguity created by length-limited attempts in the first Qwen run. The realized length-failure rate must be reported and the label "length-safe" should be withdrawn if the planned tolerance is not achieved.

## S03 Persona × reasoning factorial

Population: the same 1,000 frozen CAMS respondents.

Model: `openai/gpt-oss-120b`.

Cells: thin/off, thin/medium, rich/off, rich/medium.

Only thin/off and thin/medium require new inference. Rich/off and rich/medium are exactly S01.

Primary estimand: difference-in-differences between the reasoning effect under thin and rich personas.

Mechanism hypothesis to freeze prospectively: reasoning will depend more heavily on learned population priors when persona information is sparse, producing a different macro-fidelity effect under thin personas.

## S04 PLFS cross-domain reasoning replication

Population: 1,000 deterministically selected respondents from the frozen PLFS 2023–24 persona bundle.

Model: `openai/gpt-oss-120b`.

Outcomes: labour-force participation, employment, unemployment, self-employment, regular salaried employment, casual labour.

Hard prerequisite: recover a separate matched PLFS truth bundle before any inference. The repository currently lacks this asset.

## S05 Fresh preregistered holdout

Population: 500 CAMS respondents excluded from all prior empirical work and from hypothesis formation.

Cells:

1. Qwen thin/off
2. Qwen rich/off
3. Qwen rich/medium
4. GPT-OSS rich/off

This compact design simultaneously retests persona enrichment, reasoning, model identity, and joint-distribution compression on an untouched sample.

Hard prerequisite: freeze and hash new encrypted codes and truth bundles and prove respondent-ID disjointness from the original 1,000-person sample before any model output is generated.

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
- paired respondent bootstrap confidence intervals.

For reasoning studies, the primary comparison must remain paired at respondent level. For S03 the factorial interaction must be estimated directly rather than inferred from separate significance tests.

## Cost policy

The numerical values in `studies/registry.json` are planning prices only. The authoritative pre-spend number is produced by `studies/common/openrouter_preflight.py`, which reconstructs the exact request set, estimates conservative input tokens from the actual prompts, reads the live pinned endpoint prices, sums the full hard completion caps, and compares that number with both the registered study cap and the current key balance.

A paid launch is prohibited if the live hard single-pass ceiling exceeds the registered cap or available key credit.

## No-spend rule for incomplete evidence chains

S04 and S05 deliberately fail readiness checks while their truth assets are absent. This is not an engineering defect. It is a scientific guardrail against paying for synthetic data that cannot subsequently answer the preregistered human-fidelity question.
