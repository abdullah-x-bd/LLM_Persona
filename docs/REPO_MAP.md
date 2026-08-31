# Canonical repository map

The repository began as one CAMS persona-validation experiment and grew into a multi-study program. This document is the canonical navigation layer. It is intentionally non-destructive: older scripts and workflows are retained for provenance, while new work should follow the structure below.

## Canonical top-level structure

```text
LLM_Persona/
├── README.md                         # project-level entry point
├── docs/                             # cross-study design, audit, synthesis, roadmap
├── studies/                          # new confirmatory follow-up suite
│   ├── registry.json                 # machine-readable frozen study registry
│   ├── common/                       # shared builder, preflight, paid runner, analysis
│   └── S01...S05/                    # study-specific documentation
├── reasoning_population_fidelity/    # completed/continuing Qwen reasoning study
├── src/                              # original CAMS + multisurvey production infrastructure
├── data/                             # documentation and encrypted reproducibility bundles
├── config/                           # original study response schemas/configs
├── .github/workflows/                # historical and current Actions workflows
└── run/                              # small trigger/provenance records
```

## Evidence families

### A. Original CAMS persona study

Primary locations: `src/`, `config/`, `docs/research_design.md`, CAMS encrypted bundles in `data/encrypted/`.

Purpose: thin-versus-rich matched personas and truth-linked CAMS fidelity. This branch contains the original Luna production infrastructure and later Claude robustness work.

### B. Multi-model / multi-survey robustness

Primary locations: `src/multisurvey_*`, `src/analyze_crossmodel.py`, CMS/PLFS workflows, CMS and PLFS encrypted code bundles.

Purpose: model-choice and domain robustness across CMS Telecom 2025 and PLFS 2023–24. The current repository does not contain separate CMS/PLFS truth bundles, so these branches should not be described as truth-linked fidelity validations unless those truth assets are restored.

### C. Reasoning population fidelity

Primary location: `reasoning_population_fidelity/`.

Purpose: paired reasoning-off/low/medium CAMS experiment with Qwen3.8-27B, truth-separated generation, frozen analysis plan, production recovery, final analysis, and robustness diagnostics.

### D. Confirmatory follow-up suite

Primary location: `studies/`.

Purpose: five post-synthesis experiments designed to test whether the emerging micro/macro fidelity result survives model-family, truncation, persona-information, domain, and untouched-holdout challenges.

## Workflow policy

The `.github/workflows/` directory contains many historical repair and recovery workflows because production inference required checkpoint-safe recovery. They are retained as a provenance record. A workflow filename existing in that directory does not mean it is the current canonical launch path.

For new work:

- use the study suite workflows for S01–S05;
- use existing reasoning-population workflows only for the original Qwen study and its artifacts;
- do not revive retired Gemini repair workflows without a new scientific justification;
- never rerun a whole paid workflow merely to recover a small missing subset when an encrypted checkpoint exists.

## Data policy

Public Git history may contain encrypted reproducibility bundles, never API keys or plaintext respondent rows. CAMS has separate encrypted persona-code and truth bundles. CMS/PLFS currently expose persona-code bundles only. Generation must not decrypt truth. Analysis may decrypt truth only after model outputs are frozen.

## Documentation hierarchy

1. `README.md` gives the current whole-project status and headline.
2. `docs/REPO_MAP.md` explains where everything lives.
3. `docs/REPO_WIDE_RESULTS_SYNTHESIS.md` records the current empirical synthesis.
4. `docs/FOLLOWUP_EXPERIMENT_PLAN.md` records the five new experiments and cost logic.
5. `studies/README.md` explains how to operate the confirmatory suite.
6. Study-specific READMEs record the exact scientific purpose and launch blocks.
7. Historical design documents remain authoritative for the study they originally froze, but do not override later study-specific frozen plans.
