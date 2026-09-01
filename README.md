# Better synthetic individuals do not make better synthetic populations

[![Final repository QA](https://github.com/abdullah-x-bd/LLM_Persona/actions/workflows/final_qa.yml/badge.svg)](https://github.com/abdullah-x-bd/LLM_Persona/actions/workflows/final_qa.yml)

This repository contains the research artifact for a multi-model study of whether improvements in **individual-level LLM simulation** translate into improvements in **population-level fidelity**.

The central result is a non-guarantee: **improving synthetic individuals does not guarantee improving synthetic populations**. Across persona interventions, inference-time reasoning, multiple model families, and multiple population estimands, individual predictive fidelity and population fidelity can move together or in opposite directions.

The repository includes the completed analysis code, aggregate result tables, R figures, study registry, provenance records, citation metadata, licenses, and machine-readable integrity checks for version 1.0.0.

## Research contribution

Prior work has shown that LLM-generated populations can fail to reproduce real population distributions. This study tests a narrower question directly: **when a controlled intervention makes the same synthetic respondents better at matching their corresponding human respondents, does the reconstructed population also improve?**

The answer depends on the model and the estimand. The same intervention can improve respondent-level Brier score while worsening population prevalence, improve one representation of prevalence while worsening another, or improve average probability error while creating a heavier tail of confidently wrong predictions.

The practical implication is simple: **synthetic respondents must be validated against the population-level quantity for which they will actually be used.** Person-level accuracy alone is not sufficient evidence of population validity.

## Evidence base

The truth-linked empirical program uses the Government of India Comprehensive Annual Modular Survey (CAMS), NSS 79th Round 2022–23.

| Evidence family | Model | Design | Respondents |
|---|---|---|---:|
| Persona information | GPT-5.6 Luna | thin vs rich | 1,000 paired |
| Persona robustness | Claude Sonnet 5 | thin vs rich | 250 paired |
| Reasoning | Qwen3.8-27B | off / low / medium | 1,000 paired |
| Reasoning replication | DeepSeek V4 Flash 0731 | rich/off vs rich/high | 1,000 paired |
| Persona × reasoning factorial | DeepSeek V4 Flash 0731 | thin/rich × off/high | 1,000 |
| Supervised references | prevalence, logistic, gradient boosting, random forest | 10-fold cross-fitted | 1,000 |

The common analysis engine harmonizes **11 completed LLM cells**, uses survey weights throughout, and estimates paired contrasts with **10,000 respondent bootstrap replicates** where paired outputs are available.

## Headline findings

- **Luna rich vs thin:** respondent-level Brier improves by 0.0187, while hard-prevalence MAE worsens by about 3.20 percentage points.
- **Claude rich vs thin:** Brier, log loss, hard accuracy, and hard-prevalence MAE improve, while probability-prevalence MAE worsens by about 1.06 percentage points.
- **Qwen medium reasoning vs off:** Brier and log loss improve, while hard accuracy and both prevalence-error measures worsen.
- **DeepSeek high reasoning vs off under rich personas:** Brier, hard accuracy, both prevalence endpoints, and joint population structure improve, while log loss worsens because highly confident wrong predictions become more common.
- **Direct Qwen-versus-DeepSeek reasoning interaction:** reasoning effects differ strongly across model families for log loss, hard accuracy, probability-prevalence MAE, and hard-prevalence MAE.
- **DeepSeek factorial:** reasoning improves Brier more under thin personas, while rich persona information complements reasoning for hard population reconstruction.
- **Supervised references:** model ranking changes with the validation target. No single method dominates Brier, prevalence, hard-population, and joint-distribution fidelity.

Exact estimates and confidence intervals are in [`docs/REPO_WIDE_RESULTS_SYNTHESIS.md`](docs/REPO_WIDE_RESULTS_SYNTHESIS.md) and [`analysis_final/results/contrasts.csv`](analysis_final/results/contrasts.csv).

## Canonical research artifact

The durable analysis package is under [`analysis_final/`](analysis_final/).

- [`analysis_final/results/`](analysis_final/results/) contains aggregate-only result tables and a SHA-256 manifest.
- [`analysis_final/figures/`](analysis_final/figures/) contains eight figures in PDF, SVG, and 600-dpi PNG, with a separate checksum manifest.
- [`analysis_final/unified_analysis.py`](analysis_final/unified_analysis.py) is the canonical four-family common metric engine.
- [`analysis_final/baselines.py`](analysis_final/baselines.py) implements the cross-fitted supervised reference models.
- [`analysis_final/figures.R`](analysis_final/figures.R) generates the figure suite.
- [`analysis_final/final_qa.py`](analysis_final/final_qa.py) validates the result, figure, documentation, licensing, and privacy boundaries.

The provenance record is [`docs/FINAL_PROVENANCE.md`](docs/FINAL_PROVENANCE.md). The frozen scientific boundary is recorded in [`docs/SCIENTIFIC_FREEZE.md`](docs/SCIENTIFIC_FREEZE.md).

## Figure suite

The R/ggplot2 package contains:

1. micro-versus-macro fidelity map;
2. Qwen-versus-DeepSeek reasoning reversal;
3. DeepSeek persona × reasoning factorial;
4. age-gradient reasoning effects;
5. joint-population response-pattern fingerprint;
6. individual-versus-joint fidelity landscape with supervised references;
7. DeepSeek confidence-tail trade-off;
8. outcome-level reasoning-effect heatmap.

All PNGs are rendered at 600 dpi. Plot titles are kept outside the artwork.

## Reproducibility and integrity

The durable publication package is aggregate-only. Historical respondent-level generation outputs remain encrypted and are not committed as final plaintext artifacts. Human CAMS outcome truth is excluded from generation and is joined only during post-generation analysis.

The common-engine package records:

- 1,000 CAMS truth respondents;
- 250 respondents in the Claude robustness subset;
- 11 completed LLM cells;
- 10,000 bootstrap replicates;
- bootstrap seed `3108202691`;
- no paid LLM inference in final harmonization;
- no respondent-level plaintext in the durable result package.

Both result and figure directories contain file-level SHA-256 manifests. The final QA workflow checks package integrity and the zero-inference boundary.

### Verify version 1.0.0

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pandas
python analysis_final/final_qa.py
```

A successful run ends with:

```text
FINAL_RESEARCH_ARTIFACT_QA_PASS
```

### Regenerate figures from committed aggregate results

The figure script uses R with `ggplot2`, `dplyr`, `tidyr`, `readr`, `scales`, `ggrepel`, `patchwork`, and `svglite`.

```bash
Rscript analysis_final/figures.R analysis_final/results analysis_final/figures_rebuilt
```

This route reads only the committed aggregate result package.

## Data

The human benchmark is the **Comprehensive Annual Modular Survey (CAMS), NSS 79th Round 2022–23**, produced by the National Sample Survey Office, Ministry of Statistics and Programme Implementation, Government of India.

Reference: `DDI-IND-MOSPI-NSSO-CAMS22-23`.

The official anonymized microdata are available to registered users through the MoSPI Microdata Portal, subject to its access terms: <https://microdata.gov.in/>.

This repository does not redistribute respondent-level matched human and LLM records in plaintext.

## Frozen study boundary

The machine-readable study boundary is [`studies/registry.json`](studies/registry.json).

- **S01:** complete and analyzed.
- **S03:** complete and analyzed.
- **S02:** archived unrun prospective study.
- **S04:** scientifically blocked because matched PLFS truth is unavailable and excluded from truth-linked claims.
- **S05:** archived unrun prospective study.

Historical CMS and PLFS branches remain in the repository for provenance and engineering history. They are not part of the truth-linked accuracy evidence without matched truth assets.

## Repository map

```text
LLM_Persona/
├── README.md
├── CITATION.cff                    # machine-readable citation metadata
├── LICENSE                         # MIT license for software code
├── LICENSE-CONTENT.md              # CC BY 4.0 for original research content
├── requirements.txt
├── analysis_final/
│   ├── results/                    # canonical aggregate results
│   ├── figures/                    # PDF/SVG/600-dpi PNG figures
│   ├── unified_analysis.py         # canonical cross-study engine
│   ├── baselines.py                # cross-fitted supervised references
│   ├── figures.R                   # R figure generation
│   └── final_qa.py                 # integrity/privacy/release gate
├── docs/
│   ├── REPO_WIDE_RESULTS_SYNTHESIS.md
│   ├── FINAL_PROVENANCE.md
│   ├── SCIENTIFIC_FREEZE.md
│   ├── REPO_MAP.md
│   ├── RELEASE_NOTES_v1.0.0.md
│   └── RELEASE_v1.0.0.md
├── studies/                        # frozen study registry and follow-up provenance
├── reasoning_population_fidelity/ # completed Qwen reasoning study
├── src/                            # historical runtime and analysis infrastructure
├── data/encrypted/                 # encrypted reproducibility assets
└── .github/workflows/              # historical and final zero-inference workflows
```

## Documentation

- [`analysis_final/results/summary.json`](analysis_final/results/summary.json) provides machine-readable final status and provenance.
- [`docs/REPO_WIDE_RESULTS_SYNTHESIS.md`](docs/REPO_WIDE_RESULTS_SYNTHESIS.md) contains the empirical synthesis.
- [`analysis_final/results/contrasts.csv`](analysis_final/results/contrasts.csv) contains paired effects and confidence intervals.
- [`analysis_final/figures/`](analysis_final/figures/) contains the figure package.
- [`docs/FINAL_PROVENANCE.md`](docs/FINAL_PROVENANCE.md) records authoritative runs, artifacts, seeds, and privacy guarantees.
- [`docs/SCIENTIFIC_FREEZE.md`](docs/SCIENTIFIC_FREEZE.md) records the scientific boundary of version 1.0.0.
- [`docs/RELEASE_v1.0.0.md`](docs/RELEASE_v1.0.0.md) records the stable release identity and contents.

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

```bibtex
@software{abdullah_x_llm_persona_2026,
  author  = {Abdullah X},
  title   = {Better synthetic individuals do not make better synthetic populations: research artifact},
  year    = {2026},
  version = {1.0.0},
  url     = {https://github.com/abdullah-x-bd/LLM_Persona}
}
```

## Versioning

Version `v1.0.0` freezes the evidentiary meaning of this research artifact. Scientific extensions are versioned separately with their own provenance records rather than changing the meaning of the tagged release.

## License

This repository uses a mixed license:

- **Software code:** MIT License. See [`LICENSE`](LICENSE).
- **Original documentation, publication figures, aggregate publication result tables, and derived aggregate summaries:** Creative Commons Attribution 4.0 International (CC BY 4.0). See [`LICENSE-CONTENT.md`](LICENSE-CONTENT.md).

These licenses do not relicense Government of India CAMS microdata, encrypted respondent-level artifacts, model-provider outputs, or other third-party/restricted material. Those remain subject to their original terms and restrictions.
