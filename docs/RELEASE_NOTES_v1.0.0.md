# v1.0.0 — Frozen synthetic-population fidelity research artifact

Version 1.0.0 is the first stable research-artifact release for **Better synthetic individuals do not make better synthetic populations**.

## Included in this release

- canonical four-family analysis across Luna, Claude, Qwen, and DeepSeek;
- 11 completed LLM cells evaluated under one harmonized metric implementation;
- 10,000 paired respondent bootstrap replicates for supported paired contrasts;
- cross-fitted supervised reference models;
- aggregate-only result tables with SHA-256 manifests;
- eight R/ggplot2 figures in PDF, SVG, and 600-dpi PNG;
- frozen S01-S05 study registry;
- provenance, scientific-boundary, privacy, and licensing documentation;
- machine QA checks for result integrity, figure integrity, documentation, licensing, and privacy boundaries.

## Central result

Improving individual-level synthetic-respondent fidelity does not guarantee improving population-level fidelity.

Across the completed experiments, persona information and inference-time reasoning can improve respondent-level prediction while population prevalence, hard categorical totals, joint response structure, subgroup fidelity, or probability tails move differently. The direction depends on model family and on the population estimand being evaluated.

The claim is a non-guarantee. It does not imply that individual improvement must make population reconstruction worse.

## Frozen evidence boundary

Included in the truth-linked evidence package:

- Luna thin versus rich, 1,000 paired respondents;
- Claude thin versus rich, 250 paired respondents;
- Qwen off / low / medium reasoning, 1,000 paired respondents;
- DeepSeek S01 rich/off versus rich/high, 1,000 paired respondents;
- DeepSeek S03 thin/rich × off/high factorial, 1,000 respondents;
- 10-fold cross-fitted supervised reference models.

Excluded from truth-linked accuracy claims:

- S02 and S05, archived unrun prospective studies;
- S04, scientifically blocked because matched PLFS truth is unavailable;
- CMS and PLFS synthetic-output branches without the matched truth assets required for truth-linked accuracy validation.

## Reproducibility and privacy

The durable release package contains aggregate statistics and rendered figures. Historical respondent-level generation outputs remain encrypted. CAMS outcome truth is excluded from generation and enters only during post-generation analysis.

The final result and figure packages are checksum-manifested. The final harmonization workflow performs no paid LLM inference.

## Canonical locations

- `analysis_final/results/` — aggregate final result package
- `analysis_final/figures/` — final figure package
- `analysis_final/unified_analysis.py` — canonical cross-study engine
- `analysis_final/final_qa.py` — final integrity/privacy gate
- `docs/REPO_WIDE_RESULTS_SYNTHESIS.md` — empirical synthesis
- `docs/FINAL_PROVENANCE.md` — authoritative provenance
- `docs/SCIENTIFIC_FREEZE.md` — frozen scientific boundary
- `studies/registry.json` — machine-readable study boundary

## Licensing

- Software code: MIT License in `LICENSE`.
- Original documentation, publication figures, aggregate publication result tables, and derived aggregate summaries: Creative Commons Attribution 4.0 International in `LICENSE-CONTENT.md`.

These licenses do not relicense Government of India CAMS microdata, encrypted respondent-level artifacts, model-provider outputs, or third-party/restricted material.

## Citation

Machine-readable citation metadata are provided in `CITATION.cff`.

```bibtex
@software{abdullah_x_llm_persona_2026,
  author  = {Abdullah X},
  title   = {Better synthetic individuals do not make better synthetic populations: research artifact},
  year    = {2026},
  version = {1.0.0},
  url     = {https://github.com/abdullah-x-bd/LLM_Persona}
}
```
