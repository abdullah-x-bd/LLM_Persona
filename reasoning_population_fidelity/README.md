# Reasoning-Induced Distortion in Synthetic Populations

Working project title: **Does Thinking Make Synthetic People Less Human? Reasoning, Demographic Overdetermination, and Uncertainty in LLM Population Simulation**

## Status

The primary CAMS reasoning experiment is complete.

- 1,000 frozen CAMS respondents
- 3 reasoning conditions: off, low, medium
- 3,000 / 3,000 final schema-valid responses
- model: `qwen/qwen3.8-27b`
- provider: AkashML, pinned without fallbacks
- human truth withheld throughout generation
- final truth-linked aggregate analysis completed with the frozen 10,000-replicate paired bootstrap

The original USD 10.30 line in early planning documents was the initial engineering budget for this experiment, not a standing repository-wide budget. Recovery work later required an explicitly documented operational extension. Historical run and recovery details are retained in the engineering changelog rather than rewritten.

## Core result

The main result is a micro/macro divergence. Increasing reasoning improved respondent-level proper probabilistic scores, including Brier score and log loss, but did not translate into better categorical synthetic-population fidelity. In the full prespecified analysis, medium reasoning also worsened probability-prevalence MAE, although that macro probability effect is sensitive to the length-failure tail. Hard prevalence degradation and individual probabilistic improvement are substantially more robust.

The analysis also identified joint-distribution compression and a strong underrepresentation of a common phone-first digital phenotype. See the final analysis and robustness code under `src/` and the repo-wide synthesis under `docs/`.

## Folder structure

- `config/` frozen experiment settings and model parameters
- `prompts/` frozen prompt schema
- `src/` generation, recovery, final analysis, robustness, and diagnostics
- `outputs/` committed safe manifests and freeze records
- `docs/` design and engineering provenance

Large respondent-level production artifacts remain in encrypted GitHub Actions artifacts rather than version control.

## Reproducibility rules

- Never store API keys in the repository.
- Preserve raw model outputs before parsing or aggregation.
- Use deterministic request identifiers and frozen request hashes.
- Record model, provider, parameters, prompt version, token counts, finish reason, latency, retries, and cost for paid calls.
- Keep human truth inaccessible to generation code.
- Keep confirmatory and exploratory analyses clearly separated.
- Record post-freeze engineering deviations rather than silently rewriting history.

## Follow-up experiments

The five confirmatory follow-up studies motivated by this result now live under `studies/`. They share a common zero-cost preflight, paid runner, privacy policy, and experiment registry.
