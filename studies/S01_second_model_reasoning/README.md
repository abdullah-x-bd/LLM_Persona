# S01 Second-model reasoning replication

**Question:** Does the reasoning-induced micro/macro divergence replicate outside Qwen?

## Frozen design

Population: the existing 1,000 frozen CAMS respondents.

Model: `deepseek/deepseek-v4-flash-0731`.

Provider: AkashML only, currently pinned to `akashml/fp8`, with fallbacks disabled and provider data collection set to `deny`.

Persona: rich CAMS persona.

Paired arms:

- `rich_off`: reasoning disabled, maximum completion 256 tokens.
- `rich_high`: DeepSeek high reasoning, maximum completion 1,800 tokens.

DeepSeek uses `high` rather than `medium` because the zero-cost OpenRouter gate verified that its supported reasoning efforts are `low`, `high`, and `max`. The earlier candidate `openai/gpt-oss-120b` was rejected before paid inference because current OpenRouter metadata marks reasoning as mandatory, invalidating a genuine off arm.

## Confirmatory outcomes

Primary outcomes are survey-weighted individual Brier and probability-prevalence MAE. Key secondary outcomes are hard prevalence MAE, hard accuracy, log loss, calibration-in-the-large, joint response entropy, TV/JS distance from the human joint distribution, and prespecified subgroup errors.

Primary contrast: `rich_high - rich_off`, paired by respondent.

Human truth is never loaded during generation. The existing encrypted CAMS truth bundle is loaded only by post-generation aggregate analysis.

## Cost and readiness

The validated live AkashML hard single-pass ceiling on 31 August 2026 was **$0.452429** for all 2,000 requests. The registered study cap is **$0.90**. The hard ceiling assumes every request consumes its full completion allowance and is therefore not an expected-spend forecast.

Zero-cost static and live preflight passed. A paid launch still requires the manual workflow confirmation and a fresh live preflight immediately before inference.

The two rich arms generated here are reused exactly by S03 and must not be regenerated for the factorial study.
