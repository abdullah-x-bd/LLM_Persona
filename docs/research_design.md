# Frozen Research Design Draft

## Research question
How accurately can persona-conditioned LLMs reconstruct held-out survey outcomes from actual NSO respondents, and is the resulting accuracy sufficient to justify prospective testing as a rapid preliminary policy-evidence tool for Indian policymaking?

## Primary dataset
NSO Comprehensive Annual Modular Survey (CAMS) 2022-23.

## Planned analytic sample
Initial target: 400 respondents aged 15+, sampled reproducibly after variable and eligibility checks. The final sample size may be increased only before outcome evaluation.

## Persona conditions

### Thin persona
Age, gender, state, and rural/urban residence.

### Rich persona
Thin persona variables plus eligible pre-outcome socioeconomic characteristics available in CAMS, such as marital status, education/enrolment, economic activity, household size, social group, household language, and household consumption/expenditure band.

No target outcome or direct proxy that trivially reveals the held-out answer may be included in persona construction.

## Candidate held-out outcomes
1. Ability to use a computer/laptop/tablet.
2. Ability to use the internet.
3. Internet use during the previous three months.
4. Ability to send/receive email.
5. Ability to perform digital banking/payment activity.
6. Ability to use copy-and-paste tools.

Exact variable names and eligibility universes will be verified against the downloaded codebook before generation.

## Hypotheses

### H1 Population fidelity
LLM-persona estimates will reproduce a majority of selected NSO population estimates within a pre-specified policy-relevant error margin.

### H2 Subgroup fidelity
LLM-persona estimates will reproduce the direction and approximate magnitude of major gender, rural/urban, and age disparities observed in NSO data.

### H3 Persona enrichment
Rich socioeconomic personas will produce lower estimation error than thin demographic personas.

### H4 Individual fidelity
Matched LLM predictions will outperform a naive majority-class baseline, while individual correspondence may remain weaker than population-level correspondence.

## Primary metrics
- Weighted NSO prevalence by outcome.
- Weighted LLM-estimated prevalence by outcome.
- Absolute error in percentage points.
- Mean absolute error across outcomes.
- Proportion of outcomes within 3, 5, and 10 percentage points.
- Gender, rural/urban, and age-gap direction and magnitude error.
- Individual accuracy and balanced accuracy.
- Thin-versus-rich paired comparison.

## Primary tolerance
The primary interpretive benchmark is ±5 percentage points for aggregate estimates. This is an operational policy-relevance threshold for the proof-of-concept, not a universal statistical standard.

## Baselines
At minimum, compare individual predictions against the majority-class baseline. If feasible, add a logistic-regression benchmark trained only on the same persona covariates.

## Prompt discipline
The model prompt, question wording, persona construction rules, outcome definitions, sample seed, and evaluation metrics must be frozen before comparing generated responses with held-out NSO outcomes.

## Data leakage rule
All target outcomes and variables that directly disclose or trivially imply the target response must be withheld from the persona prompt.

## Policy interpretation
Strong retrospective performance would support prospective shadow-survey validation, not replacement of official human surveys. Mixed performance should lead to domain- or subgroup-specific recommendations. Weak performance should constrain use to lower-stakes exploratory tasks such as questionnaire pretesting or hypothesis generation.

## Secondary human survey
A small convenience sample may be used only as an exploratory acceptability study concerning possible uses of LLM-generated preliminary estimates. It is not a nationally representative validation sample.
