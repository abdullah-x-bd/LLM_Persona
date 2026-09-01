# Repository map

This repository began as a CAMS persona-validation experiment and developed into a multi-study program on synthetic-population fidelity. Version 1.0.0 freezes the truth-linked empirical boundary. Historical production, recovery, provider, and prospective-study files are retained for provenance.

## Top-level structure

```text
LLM_Persona/
├── README.md                           # public research-artifact landing page
├── CITATION.cff                        # machine-readable citation metadata
├── LICENSE                             # MIT license for software code
├── LICENSE-CONTENT.md                  # CC BY 4.0 for original research content
├── requirements.txt
├── analysis_final/                     # canonical zero-inference analysis layer
│   ├── results/                        # durable aggregate-only results
│   ├── figures/                        # PDF/SVG/600-dpi PNG figure package
│   ├── baselines.py                    # cross-fitted supervised references
│   ├── unified_analysis.py             # canonical four-family common metric engine
│   ├── recover_legacy.py               # transient Luna recovery for CI analysis
│   ├── finalize_outputs.py             # aggregate packager and checksums
│   ├── figures.R                       # title-free R/ggplot figure generation
│   └── final_qa.py                     # repository integrity/privacy gate
├── docs/
│   ├── REPO_WIDE_RESULTS_SYNTHESIS.md
│   ├── FINAL_PROVENANCE.md
│   ├── SCIENTIFIC_FREEZE.md
│   ├── RELEASE_NOTES_v1.0.0.md
│   └── RELEASE_v1.0.0.md
├── studies/                            # frozen S01-S05 follow-up records
├── reasoning_population_fidelity/     # completed Qwen reasoning study
├── src/                                # original runtime and analysis infrastructure
├── data/encrypted/                     # encrypted reproducibility assets
├── config/                             # response schemas/configuration
├── .github/workflows/                  # historical and final workflows
└── run/                                # historical trigger/provenance records
```

## Canonical analysis layer

`analysis_final/` contains the stable research outputs.

The source of harmonized numerical results is `analysis_final/results/`. The source of rendered figures is `analysis_final/figures/`. Both directories contain checksum manifests.

The canonical cross-study engine is `analysis_final/unified_analysis.py`. It reconstructs the completed Luna, Claude, Qwen, and DeepSeek evidence under one metric implementation. `analysis_final/final_unified.py` is retained as provenance for an earlier Qwen/DeepSeek-centered synthesis and is not the canonical four-family engine.

## Evidence families

### A. Original CAMS persona study

Primary historical locations: `src/`, `config/`, `docs/research_design.md`, and the encrypted CAMS bundles in `data/encrypted/`.

Role in version 1.0.0: Luna thin-versus-rich evidence on 1,000 paired respondents. The completed raw output is recovered only transiently in the zero-inference workflow and is represented durably by aggregate files in `analysis_final/results/`.

### B. Claude persona robustness

Primary historical workflow: `cams_claude_analysis.yml` and the completed Claude shard artifacts.

Role in version 1.0.0: thin-versus-rich robustness evidence on the frozen 250-respondent subset. The common engine recomputes its metrics and paired 10,000-bootstrap contrasts.

### C. Qwen reasoning population fidelity

Primary historical location: `reasoning_population_fidelity/`.

Role in version 1.0.0: completed paired off/low/medium reasoning experiment on 1,000 CAMS respondents, including the frozen analysis plan, production recovery, final analysis, robustness diagnostics, and the common-engine medium-minus-off comparison.

### D. DeepSeek follow-up studies

Primary location: `studies/` and `docs/DEEPSEEK_S01_S03_FACTORIAL_RESULTS.md`.

- S01: complete rich/off-versus-rich/high reasoning replication on 1,000 respondents.
- S03: complete thin/rich × off/high factorial, reusing the S01 rich cells.
- S02: archived unrun prospective design.
- S04: scientifically blocked and excluded because no matched PLFS truth asset is available.
- S05: archived unrun prospective design.

The `studies/` directory records the frozen study history and evidentiary boundary.

### E. CMS and PLFS robustness branches

Primary locations: `src/multisurvey_*`, `src/analyze_crossmodel.py`, and historical CMS/PLFS workflows.

These branches contain synthetic-output and engineering evidence, but the repository does not contain the matched truth assets required for truth-linked accuracy validation. They are excluded from the version 1.0.0 truth-linked fidelity claims.

## Workflow boundary

Most files under `.github/workflows/` are historical production, repair, recovery, or provider-engineering records.

The final zero-inference workflows are:

- `final_baselines.yml`
- `final_unified_analysis.yml`
- `final_figures.yml`
- `final_qa.yml`

Version 1.0.0 contains no additional paid inference beyond the completed experimental evidence. Scientific extensions are recorded under new versions with separate provenance.

## Data boundary

Generation and CAMS outcome truth remain separated. Completed respondent-level generation outputs are decrypted only transiently during authorized post-generation analysis. The durable package under `analysis_final/results/` contains aggregate statistics only.

`analysis_final/figures/` is generated from the committed aggregate result package and does not read respondent-level data.

## Documentation hierarchy

1. `README.md` — public research-artifact entry point.
2. `docs/REPO_WIDE_RESULTS_SYNTHESIS.md` — empirical synthesis.
3. `docs/FINAL_PROVENANCE.md` — authoritative runs, artifacts, seeds, privacy guarantees, and package provenance.
4. `analysis_final/README.md` — canonical analysis layer.
5. `studies/registry.json` — machine-readable study-status record.
6. `docs/SCIENTIFIC_FREEZE.md` — frozen scientific boundary.
7. `docs/RELEASE_NOTES_v1.0.0.md` — GitHub release notes.
8. `docs/RELEASE_v1.0.0.md` — stable release record.
9. Historical plans and design documents — provenance for the study state they originally froze.
