# S02 Length-safe Qwen reasoning replication

**Question:** Does the original Qwen result survive when completion truncation is engineered to be negligible?

## Frozen design

Population: all 1,000 frozen CAMS respondents.

Model: `qwen/qwen3.8-27b`, pinned to AkashML with fallbacks disabled and provider data collection set to `deny`.

Persona: rich CAMS persona.

Paired arms:

- `rich_off`: reasoning disabled, 256 maximum completion tokens.
- `rich_medium`: medium reasoning, 3,200 maximum completion tokens.

The 3,200-token medium cap is more than double the original Study 1 medium cap of 1,430 and is intended to make reasoning truncation a negligible design feature. The study must not be described as length-safe unless the realized first-pass and all-attempt `finish_reason=length` rates satisfy the prespecified tolerance.

## Confirmatory outcomes

Primary contrast: `rich_medium - rich_off`, paired by respondent.

Co-primary outcomes are survey-weighted individual Brier and probability-prevalence MAE. Secondary outcomes include hard prevalence MAE, hard accuracy, log loss, calibration-in-the-large, per-outcome errors, joint-response entropy, TV/JS distance, subgroup fidelity, latency, token use, and length-failure frequency.

Human truth is loaded only after generation by the aggregate analysis stage.

## Cost and readiness

On 31 August 2026 the zero-cost live preflight verified Qwen medium reasoning, structured output, `max_tokens`, AkashML `akashml/fp8`, no fallback, and live prices of approximately $0.35/M input and $2.55/M output. The resulting **worst-case single-pass ceiling was $9.256217** for 2,000 requests. Registered study cap: **$11.25**.

This ceiling assumes every medium request consumes all 3,200 completion tokens. It is not an expected-spend forecast. Because this is the expensive follow-up, a paid launch should occur only after an engineering micro-pilot demonstrates valid JSON, low truncation, stable routing, and acceptable latency with the exact production payload.
