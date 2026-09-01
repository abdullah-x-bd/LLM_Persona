# Research artifact provenance

This document records the authoritative inputs and zero-inference analysis chain for version 1.0.0 of the research artifact.

The durable result and figure packages are committed under `analysis_final/results/` and `analysis_final/figures/`. Their `MANIFEST.json` files contain file-level SHA-256 checksums and provide the machine-readable integrity record for the published package.

## Analysis identity

| Item | Value |
|---|---|
| Canonical common engine | `analysis_final/unified_analysis.py` |
| Harmonization workflow | `.github/workflows/final_unified_analysis.yml` |
| Harmonization run | `33459614973` |
| Analysis source commit recorded by final package | `cca2318ae59edb607f6050f2093ac4698a094cf6` |
| Bootstrap replicates | 10,000 |
| Bootstrap seed | `3108202691` |
| LLM cells in common engine | 11 |
| CAMS truth respondents | 1,000 |
| Claude subset | 250 respondents |
| Paid inference in final harmonization | none |
| Respondent-level plaintext in durable result package | none |

The harmonization run passed the zero-inference source gate, authoritative-artifact recovery gate, four-family common-engine analysis, aggregate privacy/integrity gate, result-package commit, and aggregate artifact upload.

## Authoritative completed LLM inputs

### Luna

- Model: `openai/gpt-5.6-luna`
- Authoritative successful production run: `33284028509`
- Authoritative encrypted combined raw artifact: `9723896566`
- Respondents: 1,000
- Conditions: thin, rich
- Completed respondent-condition outputs: 2,000

The harmonization workflow decrypts this completed encrypted aggregate only into transient CI storage. The decrypted JSONL is neither committed nor uploaded as a durable artifact.

### Claude

- Model: `anthropic/claude-sonnet-5`
- Authoritative production run: `33286721946`
- Authoritative completed shards: `cams-claude-0` through `cams-claude-19`
- Shards: 20
- Respondents: 250
- Conditions: thin, rich
- Completed respondent-condition outputs: 500

The harmonization workflow reconstructs the 20 encrypted shards transiently and verifies 250 distinct respondents and 500 distinct respondent-condition pairs before analysis.

### Qwen

- Model: `qwen/qwen3.8-27b`
- Authoritative encrypted artifact used by the common engine: `9750263228`
- Respondents: 1,000
- Conditions: off, low, medium
- Completed LLM cells: 3

The original Qwen production, recovery, frozen analysis plan, and robustness history are retained under `reasoning_population_fidelity/` and the corresponding `reasoning_population_*` workflows.

### DeepSeek S01

- Model: `deepseek/deepseek-v4-flash-0731`
- Provider: OpenInference FP8
- Production/recovery run recorded in the frozen study registry: `33406819430`
- Authoritative artifact: `9763493454`
- Respondents: 1,000
- Conditions: rich/off, rich/high

### DeepSeek S03

- Model: `deepseek/deepseek-v4-flash-0731`
- Provider: OpenInference FP8
- Production/recovery run recorded in the frozen study registry: `33406819430`
- Authoritative artifact: `9765135867`
- Respondents: 1,000
- New conditions: thin/off, thin/high
- Reused S01 conditions: rich/off, rich/high

S01 and S03 generation used provider fallback disabled, provider data collection set to `deny`, and excluded CAMS truth from generation. CAMS truth enters only after generation outputs are frozen.

## Supervised reference provenance

- Workflow: `.github/workflows/final_baselines.yml`
- Successful run: `33415197392`
- Authoritative artifact: `9766982262`
- Respondents: 1,000
- Outer cross-fitting folds: 10
- Bootstrap replicates: 10,000
- Models: weighted prevalence, logistic regression, gradient boosting, random forest
- Paid inference: none
- Respondent-level plaintext emitted by the workflow: no

The supervised comparators are outcome-trained cross-fitted references. They are not information-regime-equivalent substitutes for zero-shot LLM synthetic respondents.

## Four-family harmonization

The common engine evaluates:

- Luna thin and rich;
- Claude thin and rich;
- Qwen off, low, and medium;
- DeepSeek thin/off, thin/high, rich/off, and rich/high.

For paired contrasts supported by respondent-level completed outputs, the common engine runs 10,000 paired respondent bootstrap replicates. Luna and Claude are recomputed under the same implementation used for Qwen and DeepSeek rather than represented only by historical point estimates.

The common engine writes aggregate analysis tables. `analysis_final/finalize_outputs.py` converts those outputs into the durable package and computes file-level SHA-256 checksums.

## Result package

Location: `analysis_final/results/`

Machine status: `FINAL_PUBLICATION_SAFE_AGGREGATE_PACKAGE`

The package contains:

- `cell_metrics.csv`
- `contrasts.csv`
- `evidence_matrix.csv`
- `joint_metrics.csv`
- `outcome_metrics.csv`
- `outcome_effects.csv`
- `pattern_distribution.csv`
- `subgroup_metrics.csv`
- `age_reasoning_effects.csv`
- `probability_tail.csv`
- `summary.json`
- `MANIFEST.json`

`summary.json` records status `MANUSCRIPT_READY_FOUR_FAMILY_ZERO_INFERENCE_SYNTHESIS`, final run `33459614973`, sample integrity, bootstrap configuration, source provenance, and explicit certification that no paid inference occurred and no respondent-level plaintext was emitted into the durable result package.

`analysis_final/results/MANIFEST.json` records the exact SHA-256 and byte size of every durable result file.

## Figure package

- Workflow: `.github/workflows/final_figures.yml`
- Successful run: `33459804925`
- Figure source commit recorded by the package: `e4f0002ab885b6653ea97993a0d36c94a1f32772`
- Input: committed `analysis_final/results/` aggregate package only
- Figures: 8
- Formats per figure: PDF, SVG, PNG
- PNG resolution: 600 dpi
- Plot titles embedded in figures: none

Location: `analysis_final/figures/`

Machine status: `FINAL_PUBLICATION_FIGURE_PACKAGE`

The figure manifest links the figure package to the exact SHA-256 of the source result manifest and records SHA-256 plus byte size for all 24 rendered figure files.

## Encryption-key note

Some historical encrypted result bundles derive their decryption key from the repository's `OPENROUTER_API_KEY` secret because that was the encryption convention used during production. In the zero-inference harmonization workflow, that secret is used only to decrypt completed historical outputs. The final analysis source is explicitly gated against inference endpoints and does not submit new LLM requests.

No API secret is committed to the repository.

## Truth separation and data firewall

Version 1.0.0 preserves the following boundary:

1. model generation was completed without access to CAMS outcome truth;
2. completed respondent-level model outputs were frozen and encrypted;
3. truth is joined only during post-generation analysis;
4. respondent-level plaintext exists only transiently inside CI where needed for reanalysis;
5. durable repository outputs are aggregate statistics and rendered figures;
6. aggregate and figure packages are checksum-manifested.

## Frozen study status

The machine-readable study boundary is `studies/registry.json`:

- S01: complete and analyzed;
- S02: archived unrun;
- S03: complete and analyzed;
- S04: scientifically blocked and excluded because matched PLFS truth is unavailable;
- S05: archived unrun.

Version 1.0.0 contains no additional paid inference beyond the completed experimental evidence described above. Later scientific extensions are versioned separately with their own provenance records.