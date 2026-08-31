# LLM Population Simulation Fidelity

**Working umbrella result:** *Better synthetic individuals do not necessarily make better synthetic populations.*

This repository is a multi-study audit of large-language-model population simulation against real Government of India survey respondents. The project began with a matched-persona CAMS experiment and now tests three distinct design levers: how much respondent information the model receives, which model generates the synthetic respondent, and how much inference-time reasoning the model performs.

The central methodological question is no longer whether one LLM can predict one survey well. It is whether respondent-level plausibility, probability calibration, aggregate prevalence, subgroup fidelity, and the joint structure of a synthetic population move together. The accumulated evidence says they often do not.

## Research program

### 1. CAMS persona-information experiments

Source: MoSPI/NSSO Comprehensive Annual Modular Survey 2022–23.

Matched real respondents are represented with either thin or rich non-target persona information. Digital-use outcomes are withheld from the model and evaluated only after model responses are frozen. Luna is the large production model in the original branch; Claude provides a matched robustness sample.

### 2. Multi-model and multi-survey robustness

The repository also contains completed model-output infrastructure for CMS Telecom 2025 and PLFS 2023–24. These branches are valuable for cross-model population-prior and distributional comparisons. The current repository does **not** contain separate CMS/PLFS truth bundles, so they must not be described as truth-linked fidelity validations until those matched truth assets are restored.

### 3. Reasoning population fidelity

`reasoning_population_fidelity/` contains the paired Qwen3.8-27B reasoning experiment on 1,000 CAMS respondents under reasoning off, low, and medium. Generation was separated from human truth, requests were frozen before production, and the final analysis reports individual, aggregate, calibration, subgroup, and joint-distribution metrics.

### 4. Confirmatory follow-up suite

`studies/` contains five post-synthesis experiments designed to challenge the emerging result rather than merely add more exploratory metrics:

- **S01** second-model reasoning replication with DeepSeek V4 Flash 0731;
- **S02** length-safe Qwen reasoning replication with much larger completion headroom;
- **S03** 2 × 2 persona-richness × reasoning factorial, reusing S01 rich cells rather than paying for them twice;
- **S04** PLFS cross-domain reasoning replication, blocked until matched PLFS truth is restored;
- **S05** untouched CAMS holdout confirmation, blocked until a genuinely disjoint holdout is frozen.

No follow-up paid inference runs merely because code is pushed. The suite has a zero-cost metadata/request/cost gate and a separate manual paid workflow that requires a literal confirmation string and an explicit spend cap.

## Canonical repository layout

```text
LLM_Persona/
├── README.md
├── docs/
│   ├── REPO_MAP.md
│   ├── REPO_WIDE_RESULTS_SYNTHESIS.md
│   ├── FOLLOWUP_EXPERIMENT_PLAN.md
│   ├── research_design.md
│   └── data_audit.md
├── studies/
│   ├── README.md
│   ├── registry.json
│   ├── common/
│   └── S01...S05/
├── reasoning_population_fidelity/
├── src/
├── config/
├── data/
│   └── encrypted/
├── .github/
│   └── workflows/
└── run/
```

See `docs/REPO_MAP.md` before adding new study code. Historical repair/recovery workflows are intentionally retained for reproducibility and provenance; their presence does not make them the canonical launch path.

## Evaluation hierarchy

The project treats synthetic-population fidelity as a vector of estimands rather than one score. Truth-linked studies report, where applicable:

- survey-weighted individual Brier score;
- probability-prevalence MAE;
- hard prevalence MAE;
- hard-response accuracy;
- log loss and calibration-in-the-large;
- outcome-specific errors;
- response-pattern entropy;
- total-variation and Jensen–Shannon distance from the human joint distribution;
- prespecified subgroup errors;
- paired respondent bootstrap uncertainty.

A setting is therefore not called “better” merely because one individual-level metric improves.

## Data and leakage policy

Target outcomes must never enter persona construction. Generation workflows do not load human truth. Respondent-level model outputs are encrypted before upload. API keys are never committed. Public Git history may contain encrypted reproducibility bundles, code, request hashes, safe run metadata, and aggregate results.

CAMS currently has separate encrypted persona-code and truth bundles. CMS and PLFS currently have persona-code bundles but no separate truth bundle in the repository.

## Provider and spending policy

Production studies pin one provider endpoint rather than silently switching inference backends. Follow-up studies currently require AkashML, disable provider fallback, request provider data collection `deny`, and recompute live OpenRouter prices immediately before any paid launch.

The authoritative cost is the live hard single-pass ceiling generated by the preflight workflow, not a price copied into documentation. Registered study caps are deliberately higher than the live ceiling to leave limited retry headroom while still enforcing a hard maximum.

## Current status

The original CAMS persona study, cross-model robustness work, and Qwen reasoning experiment have generated substantive results. The new confirmatory suite is coded and guarded. S01–S03 have passed zero-cost request/model/provider/price checks; S04 and S05 remain deliberately blocked on missing scientific assets rather than being allowed to consume inference budget prematurely.

For the current empirical synthesis, read `docs/REPO_WIDE_RESULTS_SYNTHESIS.md`. For the five next experiments, read `docs/FOLLOWUP_EXPERIMENT_PLAN.md` and `studies/README.md`.
