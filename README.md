# LLM Persona Survey Validation for Indian Policy Research

This repository contains the analysis for an Applied Policy Fellowship brief testing whether persona-conditioned large language models can reconstruct held-out outcomes from Government of India National Sample Survey microdata closely enough to justify prospective testing as a rapid preliminary policy-evidence tool.

## Working research question

**How accurately can persona-conditioned LLMs reconstruct held-out survey outcomes from actual NSO respondents, and is the resulting accuracy sufficient to justify prospective testing as a rapid preliminary policy-evidence tool for Indian policymaking?**

## Core design

1. Use NSO Comprehensive Annual Modular Survey (CAMS) 2022-23 unit-level microdata.
2. Construct matched personas from respondent characteristics that precede the target digital-use outcomes.
3. Withhold selected survey outcomes from the LLM.
4. Ask the LLM the corresponding NSO questions for each matched persona.
5. Compare synthetic predictions with the respondent's actual held-out answers and with weighted NSO population estimates.
6. Compare thin and rich persona specifications.
7. Benchmark individual-level prediction against simple statistical baselines.
8. Evaluate aggregate accuracy, subgroup fidelity, individual correspondence, and robustness.
9. Optionally pair the computational study with a small exploratory human survey on acceptability of synthetic estimation for preliminary policy research.

## Planned primary outcomes

- Computer/laptop/tablet use capability
- Internet use capability
- Internet use in the previous three months
- Email capability
- Digital banking/payment capability
- Copy-and-paste capability

The exact variable mapping will be frozen after inspection of the downloaded CAMS files and codebook.

## Planned hypotheses

- **H1 Population fidelity:** LLM-persona estimates will reproduce a majority of selected NSO population estimates within a pre-specified policy-relevant error margin.
- **H2 Subgroup fidelity:** LLM-persona estimates will reproduce the direction and approximate magnitude of major demographic disparities in the NSO data.
- **H3 Persona enrichment:** Rich socioeconomic personas will yield lower estimation error than thin demographic personas.
- **H4 Individual fidelity:** Matched LLM predictions will outperform a naive majority-class baseline, while individual correspondence may remain weaker than population-level correspondence.

## Repository layout

```text
LLM_Persona/
├── README.md
├── .gitignore
├── requirements.txt
├── docs/
│   └── research_design.md
├── data/
│   └── README.md
├── src/
│   └── .gitkeep
├── outputs/
│   └── .gitkeep
├── brief/
│   └── .gitkeep
└── presentation/
    └── .gitkeep
```

## Data handling

Raw NSO microdata, credentials, API keys, and respondent-level model outputs are excluded from version control. Only code, documentation, aggregate results, reproducible derived artifacts, and materials permitted for redistribution should be committed.

## Status

Project initialized on 29 August 2026. Experimental specification will be frozen before evaluation against held-out outcomes.
