# Reasoning-Induced Distortion in Synthetic Populations

Working project title: **Does Thinking Make Synthetic People Less Human? Reasoning, Demographic Overdetermination, and Uncertainty in LLM Population Simulation**

## Scope

This folder is an isolated workspace for the new CAMS-grounded synthetic population experiment. All new code, prompts, configs, manifests, outputs, checkpoints, analyses, and paper-supporting artifacts for this study should remain under this directory.

## Core research questions

1. Does increasing inference-time reasoning change the fidelity of LLM synthetic respondents relative to real CAMS respondents?
2. Does reasoning alter population-level prevalence error, subgroup fidelity, response diversity, and demographic dependence?
3. Does cross-model disagreement predict synthetic-human mismatch?
4. Can disagreement-based selective deferral improve the reliability of synthetic population estimates?

## Budget constraint

OpenRouter experimental budget: **USD 10.30**.

No paid run should begin until the complete pipeline has passed local dry runs, schema validation, retry/caching checks, cost estimation, and a small paid pilot.

## Planned structure

- `config/` experiment settings and model parameters
- `data/` local manifests and processed research data references
- `prompts/` frozen prompt templates and schemas
- `src/` experiment and analysis code
- `outputs/` API results, checkpoints, and run metadata
- `analysis/` statistical analyses, tables, and figure-generation code
- `tests/` unit and integration tests
- `docs/` design notes, hypotheses, and preregistration material

## Reproducibility rules

- Never store API keys in the repository.
- Preserve raw model outputs before parsing or aggregation.
- Cache every completed request using a deterministic request identifier.
- Record model, provider, parameters, prompt version, timestamp, token counts, and cost for every call.
- Keep paid and dry-run outputs clearly separated.
- Freeze the primary analysis plan before the full paid run.
