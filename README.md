# Better synthetic individuals do not make better synthetic populations

[![Final repository QA](https://github.com/abdullah-x-bd/LLM_Persona/actions/workflows/final_qa.yml/badge.svg)](https://github.com/abdullah-x-bd/LLM_Persona/actions/workflows/final_qa.yml)

A frozen research artifact for evaluating whether improvements in **individual-level LLM simulation** translate into improvements in **population-level fidelity**.

The central result is a non-guarantee: **improving synthetic individuals does not guarantee improving synthetic populations**. Across persona interventions, inference-time reasoning, multiple model families, and multiple population estimands, individual predictive fidelity and population fidelity can move together or in opposite directions.

This repository contains the completed analysis code, aggregate result tables, final R figures, study registry, provenance records, and machine-readable integrity checks for the frozen evidence package.

## What is novel here

Prior work has established that LLM-generated populations can fail to reproduce real population distributions. This project tests a narrower question directly: **when a controlled intervention makes the same synthetic respondents better at matching their corresponding human respondents, does the reconstructed population also improve?**

The answer depends on the model and the estimand. The same intervention can improve respondent-level Brier score while worsening population prevalence, improve one representation of prevalence while worsening another, or improve average probability error while creating a heavier tail of confidently wrong predictions.

The practical implication is simple: **synthetic respondents should be validated against the population-level quantity for which they will actually be used.** Person-level accuracy alone is not sufficient evidence of population validity.

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

The final common engine harmonizes **11 completed LLM cells**, uses survey weights throughout, and estimates paired contrasts with **10,000 respondent bootstrap replicates** where paired outputs are available.

## Headline findings

- **Luna rich vs thin:** respondent-level Brier improves by 0.0187, while hard-prevalence MAE worsens by about 3.20 percentage points.
- **Claude rich vs thin:** Brier, log loss, hard accuracy, and hard-prevalence MAE improve, while probability-prevalence MAE worsens by about 1.06 percentage points.
- **Qwen medium reasoning vs off:** Brier and log loss improve, while hard accuracy and both prevalence-error measures worsen.
- **DeepSeek high reasoning vs off under rich personas:** Brier, hard accuracy, both prevalence endpoints, and joint population structure improve, while log loss worsens because highly confident wrong predictions become more common.
- **Direct Qwen-versus-DeepSeek reasoning interaction:** reasoning effects differ strongly across model families for log loss, hard accuracy, probability-prevalence MAE, and hard-prevalence MAE.
- **DeepSeek factorial:** reasoning improves Brier more under thin personas, while rich persona information complements reasoning for hard population reconstruction.
- **Supervised references:** model ranking changes with the validation target. No single method dominates Brier, prevalence, hard-population, and joint-distribution fidelity.

For exact estimates and confidence intervals, see [`docs/REPO_WIDE_RESULTS_SYNTHESIS.md`](docs/REPO_WIDE_RESULTS_SYNTHESIS.md) and [`analysis_final/results/contrasts.csv`](analysis_final/results/contrasts.csv).

## Canonical research artifact

The public, durable publication package lives under [`analysis_final/`](analysis_final/).

- [`analysis_final/results/`](analysis_final/results/) contains aggregate-only final result tables and a SHA-256 manifest.
- [`analysis_final/figures/`](analysis_final/figures/) contains the eight final figures in PDF, SVG, and 600-dpi PNG, with a separate checksum manifest.
- [`analysis_final/unified_analysis.py`](analysis_final/unified_analysis.py) is the canonical four-family common metric engine.
- [`analysis_final/baselines.py`](analysis_final/baselines.py) implements the cross-fitted supervised reference models.
- [`analysis_final/figures.R`](analysis_final/figures.R) generates the final figure suite.
- [`analysis_final/final_qa.py`](analysis_final/final_qa.py) validates the frozen result, figure, documentation, and privacy boundary.

The authoritative final provenance record is [`docs/FINAL_PROVENANCE.md`](docs/FINAL_PROVENANCE.md).

## Final figure suite

The R/ggplot2 publication package contains:

1. micro-versus-macro fidelity map;
2. Qwen-versus-DeepSeek reasoning reversal;
3. DeepSeek persona × reasoning factorial;
4. age-gradient reasoning effects;
5. joint-population response-pattern fingerprint;
6. individual-versus-joint fidelity landscape with supervised references;
7. DeepSeek confidence-tail trade-off;
8. outcome-level reasoning-effect heatmap.

All PNGs are rendered at 600 dpi. No plot title is embedded in the artwork.

## Reproducibility and integrity

The durable publication package is deliberately aggregate-only. Historical respondent-level generation outputs remain encrypted and are not committed as final plaintext artifacts. Human CAMS outcome truth is kept out of generation and is joined only during post-generation analysis.

The final common-engine package records:

- 1,000 CAMS truth respondents;
- 250 respondents in the frozen Claude robustness subset;
- 11 completed LLM cells;
- 10,000 bootstrap replicates;
- bootstrap seed `3108202691`;
- no paid LLM inference in final harmonization;
- no respondent-level plaintext in the durable result package.

Both result and figure directories contain file-level SHA-256 manifests. The final QA workflow rechecks package integrity and the zero-inference boundary.

### Verify the committed publication package

Python 3.12 is used by the final QA workflow.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pandas
python analysis_final/final_qa.py
```

A successful run ends with:

```text
FINAL_REPO_QA_PASS
```

### Regenerate the figures from committed aggregate results

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
- **S02:** archived unrun prospective study, not required for the frozen evidence package.
- **S04:** scientifically blocked because matched PLFS truth is unavailable and excluded from truth-linked claims.
- **S05:** archived unrun prospective study, not required for the frozen evidence package.

Historical CMS and PLFS branches remain in the repository for provenance and engineering history. They are not part of the final truth-linked accuracy evidence without matched truth assets.

## Repository map

```text
LLM_Persona/
├── README.md
├── CITATION.cff                    # machine-readable citation metadata
├── LICENSE                         # MIT license for software code
├── LICENSE-CONTENT.md              # CC BY 4.0 for original research content
├── requirements.txt
├── analysis_final/
│   ├── results/                    # canonical aggregate publication results
│   ├── figures/                    # final PDF/SVG/600-dpi PNG figures
│   ├── unified_analysis.py         # canonical cross-study engine
│   ├── baselines.py                # cross-fitted supervised references
│   ├── figures.R                   # publication figure generation
│   └── final_qa.py                 # integrity/privacy/release gate
├── docs/
│   ├── REPO_WIDE_RESULTS_SYNTHESIS.md
│   ├── FINAL_PROVENANCE.md
│   ├── PRE_MANUSCRIPT_AUDIT.md
│   ├── REPO_MAP.md
│   ├── RELEASE_NOTES_v1.0.0.md
│   └── RELEASE_CHECKLIST.md
├── studies/                        # frozen study registry and follow-up provenance
├── reasoning_population_fidelity/ # completed Qwen reasoning study
├── src/                            # historical runtime and analysis infrastructure
├── data/encrypted/                 # encrypted reproducibility assets
└── .github/workflows/              # historical and final zero-inference workflows
```

## Documentation guide

For the shortest path through the repository:

1. [`analysis_final/results/summary.json`](analysis_final/results/summary.json) for machine-readable final status and provenance;
2. [`docs/REPO_WIDE_RESULTS_SYNTHESIS.md`](docs/REPO_WIDE_RESULTS_SYNTHESIS.md) for the full empirical synthesis;
3. [`analysis_final/results/contrasts.csv`](analysis_final/results/contrasts.csv) for paired effects and confidence intervals;
4. [`analysis_final/figures/`](analysis_final/figures/) for the final publication figures;
5. [`docs/FINAL_PROVENANCE.md`](docs/FINAL_PROVENANCE.md) for authoritative runs, artifacts, seeds, and privacy guarantees;
6. [`docs/PRE_MANUSCRIPT_AUDIT.md`](docs/PRE_MANUSCRIPT_AUDIT.md) for the historical scientific freeze audit.

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff). The repository is being prepared as the stable `v1.0.0` research artifact. Until the companion article receives its final bibliographic record, cite the tagged repository release when using the code, figures, or aggregate results.

A release-ready BibTeX form is:

```bibtex
@software{abdullah_x_llm_persona_2026,
  author  = {Abdullah X},
  title   = {Better synthetic individuals do not make better synthetic populations: research artifact},
  year    = {2026},
  version = {1.0.0},
  url     = {https://github.com/abdullah-x-bd/LLM_Persona}
}
```

After a formal article DOI is available, this section and `CITATION.cff` should be updated to make the published paper the preferred citation.

## Release policy

The frozen scientific evidence should not be silently rewritten after `v1.0.0`. Reviewer-driven or later scientific extensions should receive new provenance records and a new version rather than changing the evidentiary meaning of the original release.

The ready-to-paste release notes and release checklist are in [`docs/RELEASE_NOTES_v1.0.0.md`](docs/RELEASE_NOTES_v1.0.0.md) and [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

## License

This repository uses a mixed license:

- **Software code:** MIT License. See [`LICENSE`](LICENSE).
- **Original documentation, publication figures, aggregate publication result tables, and derived aggregate summaries:** Creative Commons Attribution 4.0 International (CC BY 4.0). See [`LICENSE-CONTENT.md`](LICENSE-CONTENT.md).

These licenses do not relicense Government of India CAMS microdata, encrypted respondent-level artifacts, model-provider outputs, or other third-party/restricted material. Those remain subject to their original terms and restrictions.
