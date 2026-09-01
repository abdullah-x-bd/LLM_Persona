# v1.0.0 — Frozen synthetic-population fidelity research artifact

This is the first stable research-artifact release for **Better synthetic individuals do not make better synthetic populations**.

## What this release contains

- the canonical four-family common analysis engine across Luna, Claude, Qwen, and DeepSeek;
- 11 completed LLM cells evaluated under one harmonized metric implementation;
- 10,000 paired respondent bootstrap replicates for supported paired contrasts;
- cross-fitted supervised reference models;
- aggregate-only final result tables with SHA-256 manifests;
- eight final R/ggplot2 publication figures in PDF, SVG, and 600-dpi PNG;
- the frozen S01-S05 study registry;
- final provenance, scientific-boundary, and privacy documentation;
- a machine QA gate for result integrity, figure integrity, documentation, and privacy boundaries.

## Central result

Improving individual-level synthetic-respondent fidelity does not guarantee improving population-level fidelity.

Across the completed experiments, persona information and inference-time reasoning can improve respondent-level prediction while population prevalence, hard categorical totals, joint response structure, subgroup fidelity, or probability tails move differently. The direction of the effect depends on model family and on the population estimand being evaluated.

This is a non-guarantee rather than a claim that individual improvement must make population reconstruction worse.

## Frozen evidence boundary

Included in the truth-linked evidence package:

- Luna thin versus rich, 1,000 paired respondents;
- Claude thin versus rich, 250 paired respondents;
- Qwen off / low / medium reasoning, 1,000 paired respondents;
- DeepSeek S01 rich/off versus rich/high, 1,000 paired respondents;
- DeepSeek S03 thin/rich × off/high factorial, 1,000 respondents;
- 10-fold cross-fitted supervised reference models.

Not promoted into the frozen truth-linked evidence package:

- S02 and S05, which remain archived unrun prospective studies;
- S04, which is scientifically blocked because matched PLFS truth is unavailable;
- CMS and PLFS synthetic-output branches that lack the matched truth assets required for final truth-linked accuracy claims.

## Reproducibility and privacy

The durable release package contains aggregate statistics and rendered figures only. Historical respondent-level generation outputs remain encrypted. CAMS outcome truth is excluded from generation and enters only during post-generation analysis.

The final result and figure packages are checksum-manifested. No paid LLM inference is performed by the final harmonization workflow.

## Canonical locations

- `analysis_final/results/` — aggregate final result package
- `analysis_final/figures/` — final figure package
- `analysis_final/unified_analysis.py` — canonical cross-study engine
- `analysis_final/final_qa.py` — final integrity/privacy gate
- `docs/REPO_WIDE_RESULTS_SYNTHESIS.md` — full empirical synthesis
- `docs/FINAL_PROVENANCE.md` — authoritative provenance
- `studies/registry.json` — frozen study boundary

## Citation

See `CITATION.cff` for machine-readable citation metadata.

After the companion article receives a final bibliographic record, the repository citation metadata should be updated to make the published article the preferred citation while preserving this tagged research artifact.
