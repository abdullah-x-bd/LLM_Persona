# S03 Persona × reasoning factorial

**Question:** Does reasoning interact with how much factual respondent information the model receives?

## Frozen design

Population: the same 1,000 frozen CAMS respondents used in S01.

Model: `deepseek/deepseek-v4-flash-0731`, AkashML only, fallbacks disabled, provider data collection `deny`.

The complete 2 × 2 design is:

- thin persona, reasoning off
- thin persona, reasoning high
- rich persona, reasoning off
- rich persona, reasoning high

Only the two thin cells are new paid inference in S03. The rich/off and rich/high cells are the exact S01 outputs and must be reused, not regenerated.

DeepSeek uses `high` because live preflight verified supported efforts `low`, `high`, and `max`. The earlier GPT-OSS candidate was rejected before paid inference because its reasoning is currently mandatory on OpenRouter and therefore cannot support an off arm.

## Primary estimand

The main confirmatory estimand is the persona × reasoning interaction, calculated as the paired difference-in-differences rather than inferred from separate significance tests. It is evaluated for individual Brier, probability-prevalence MAE, hard prevalence MAE, and hard accuracy, with joint-distribution and subgroup metrics as secondary analyses.

Mechanism hypothesis frozen prospectively: reasoning may rely more strongly on learned population priors when factual persona information is sparse, so the reasoning effect may differ between thin and rich profiles.

## Cost and readiness

The validated live AkashML hard single-pass ceiling for the 2,000 new thin-cell requests was **$0.430298** on 31 August 2026. Registered S03 cap: **$0.85**. S01 costs are not counted again because its rich cells are reused.

Static and live zero-cost preflight passed. Paid execution still requires a fresh live preflight plus literal manual authorization.
