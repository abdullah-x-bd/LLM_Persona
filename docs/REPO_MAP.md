# Canonical frozen repository map

This repository began as one CAMS persona-validation experiment and grew into a multi-study program. The empirical boundary for the stable research artifact is frozen. Historical production, recovery, provider, and prospective-study files are retained for provenance, but they are not a queue of unfinished experiments.

## Canonical top-level structure

```text
LLM_Persona/
├── README.md                           # public research-artifact landing page
├── CITATION.cff                        # machine-readable citation metadata
├── requirements.txt                    # Python dependency floor for historical/runtime code
├── analysis_final/                    # canonical final zero-inference analysis layer
│   ├── results/                       # durable aggregate-only publication results
│   ├── figures/                       # final PDF/SVG/600-dpi PNG figure package
│   ├── baselines.py                   # cross-fitted supervised references
│   ├── unified_analysis.py            # canonical four-family common metric engine
│   ├── recover_legacy.py              # transient Luna recovery for CI analysis only
│   ├── finalize_outputs.py            # aggregate packager and checksums
│   ├── figures.R                      # title-free R/ggplot figure generation
│   └── final_qa.py                    # final repo integrity/privacy gate
├── docs/                              # synthesis, provenance, audit, release metadata, historical design
│   ├── RELEASE_NOTES_v1.0.0.md
│   └── RELEASE_CHECKLIST.md
├── studies/                           # frozen S01-S05 follow-up records
├── reasoning_population_fidelity/     # completed Qwen reasoning study
├── src/                               # original CAMS/CMS/PLFS runtime and analysis infrastructure
├── data/encrypted/                    # encrypted reproducibility assets only
├── config/                            # original response schemas/configuration
├── .github/workflows/                 # historical provenance plus final zero-inference workflows
└── run/                               # historical trigger/provenance records
```

## Canonical publication layer

For the stable research artifact, start in `analysis_final/`.

The durable source of publication numbers is `analysis_final/results/`. The durable source of rendered publication figures is `analysis_final/figures/`. Both directories contain checksum manifests.

The canonical cross-study engine is `analysis_final/unified_analysis.py`. It reconstructs the completed Luna, Claude, Qwen, and DeepSeek evidence under one metric implementation. `analysis_final/final_unified.py` is retained as provenance for an earlier Qwen/DeepSeek-centered synthesis and should not be treated as the final common engine.

## Evidence families

### A. Original CAMS persona study

Primary historical locations: `src/`, `config/`, `docs/research_design.md`, and the encrypted CAMS bundles in `data/encrypted/`.

Final role: Luna thin-versus-rich evidence on 1,000 paired respondents. The authoritative completed raw output is recovered only transiently in the final zero-inference workflow and is represented durably by aggregate files in `analysis_final/results/`.

### B. Claude persona robustness

Primary historical workflow: `cams_claude_analysis.yml` and the completed Claude shard artifacts.

Final role: thin-versus-rich robustness evidence on the frozen 250-respondent subset. The final common engine recomputes its metrics and paired 10,000-bootstrap contrasts rather than carrying only legacy point estimates.

### C. Qwen reasoning population fidelity

Primary historical location: `reasoning_population_fidelity/`.

Final role: completed paired off/low/medium reasoning experiment on 1,000 CAMS respondents, including the frozen analysis plan, production recovery, final analysis, robustness diagnostics, and the common-engine medium-minus-off comparison.

### D. DeepSeek follow-up studies

Primary location: `studies/` and `docs/DEEPSEEK_S01_S03_FACTORIAL_RESULTS.md`.

Final role:

- S01: complete rich/off-versus-rich/high reasoning replication on 1,000 respondents.
- S03: complete thin/rich × off/high factorial, reusing the exact S01 rich cells.
- S02: archived unrun prospective design.
- S04: scientifically blocked and excluded because no matched PLFS truth asset is available.
- S05: archived unrun prospective design.

The `studies/` directory is therefore a frozen provenance layer, not a current launch plan.

### E. CMS and PLFS robustness branches

Primary locations: `src/multisurvey_*`, `src/analyze_crossmodel.py`, and historical CMS/PLFS workflows.

These branches contain useful synthetic-output and engineering evidence, but the repository does not contain the matched truth assets required for final truth-linked accuracy validation. They must not be promoted into the frozen truth-linked fidelity evidence.

## Workflow policy

Most files under `.github/workflows/` are historical production, repair, recovery, or provider-engineering records. Their presence does not mean they should be rerun.

The final publication-stage workflows are zero-inference only:

- `final_baselines.yml`
- `final_unified_analysis.yml`
- `final_figures.yml`
- `final_qa.yml`

No additional paid inference is part of the frozen artifact. A reviewer-driven or later extension should receive a new explicit scientific justification, frozen request set, provenance record, and version.

## Data policy

Public Git history may contain encrypted reproducibility bundles, never API keys or final respondent-level plaintext outputs. Generation and truth remain separated. Completed respondent-level generation outputs are decrypted only transiently during authorized post-generation analysis. The durable package under `analysis_final/results/` contains aggregate statistics only.

`analysis_final/figures/` is generated only from the committed aggregate result package and never reads respondent-level data.

## Documentation hierarchy

1. `README.md` is the public research-artifact entry point.
2. `docs/REPO_WIDE_RESULTS_SYNTHESIS.md` is the final empirical synthesis.
3. `docs/FINAL_PROVENANCE.md` records authoritative runs, artifacts, seeds, privacy guarantees, and final packages.
4. `analysis_final/README.md` explains the canonical analysis layer.
5. `studies/registry.json` is the machine-readable frozen study-status record.
6. `docs/PRE_MANUSCRIPT_AUDIT.md` is the historical scientific freeze audit.
7. `docs/RELEASE_NOTES_v1.0.0.md` and `docs/RELEASE_CHECKLIST.md` contain the stable-release metadata and manual release procedure.
8. Historical plans and design documents remain authoritative for the study state they originally froze, but do not override the final evidence boundary above.
