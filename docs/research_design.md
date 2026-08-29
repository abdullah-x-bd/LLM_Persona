# Frozen Research Design

## Research question
How accurately can persona-conditioned LLMs reconstruct held-out survey outcomes from actual NSO respondents, and is the resulting accuracy sufficient to justify prospective testing as a rapid preliminary policy-evidence tool for Indian policymaking?

## Primary dataset
NSO Comprehensive Annual Modular Survey (CAMS), NSS 79th Round, 2022-23.

## Analytic sample
The pre-inference sample is frozen at 1,000 respondents aged 15+. The design uses systematic probability-proportional-to-size sampling within 20 strata formed by rural/urban sector, male/female gender, and five age groups. Stratum sample allocation is proportional to the official weighted population. The seed is 29082026.

This sample size was set before any LLM response was generated. A 1,000-person sample gives substantially better precision for a primary ±5 percentage-point policy-relevance benchmark than the earlier 400-person draft.

## One-to-one matched design
Each selected CAMS respondent is represented by one synthetic counterpart. The respondent's held-out outcomes remain hidden from the model. Every respondent-condition combination receives a fresh, isolated API request with no prior conversation context.

## Persona conditions
### Rich matched persona
A deterministic natural-language representation of legitimate pre-outcome characteristics from the same real respondent: age, gender, state, rural/urban residence, relationship to household head, marital status, formal education/enrolment status, recent economic activity, household size, household religion, social group, household language, and household MPCE quintile.

### Thin matched persona
Age, gender, state, and rural/urban residence only.

No device ownership, internet access, mobile usage, banking behavior, digital-skill variable, target outcome, or direct proxy that trivially reveals a held-out answer is included.

## Held-out outcomes
The primary six outcomes are all defined over the full age-15+ analytic population, with questionnaire routing handled so structural skips imply a negative outcome only where logically and officially appropriate:
1. Ability to use a mobile telephone.
2. Mobile telephone use during the previous three months.
3. Ability to use a computer/laptop/tablet or similar device.
4. Ability to use the internet.
5. Internet use during the previous three months.
6. Execution of copy-and-paste skill during the previous three months.

Email and digital-payment ability were removed from the primary battery during pre-inference auditing because their CAMS questionnaire denominators are conditional. Treating structural skips as negative would not reproduce the official denominator.

## Pre-inference benchmark validation
Using the official CAMS multiplier, the full microdata reproduce published national figures, including approximately 57.5% internet use in the previous three months and 46.1% execution of copy-and-paste skill among persons aged 15+.

The frozen 1,000-person PPS validation sample is also highly representative of the full weighted microdata on all six target outcomes. Before any LLM inference, the absolute sample-to-full-data difference is below 0.5 percentage points for every primary outcome.

## Hypotheses
### H1 Population fidelity
LLM-persona estimates will reproduce a majority of selected matched-human population estimates within a pre-specified ±5 percentage-point policy-relevance margin.

### H2 Subgroup fidelity
LLM-persona estimates will reproduce the direction and approximate magnitude of major gender, rural/urban, and age disparities observed among the matched human respondents and in the broader NSO data.

### H3 Persona enrichment
Rich socioeconomic personas will produce lower aggregate estimation error than thin demographic personas.

### H4 Individual fidelity
Matched LLM predictions will outperform a naive majority-class baseline at the individual level, while individual correspondence may remain weaker than population-level correspondence.

## Primary metrics
- Weighted matched-human prevalence by outcome.
- Weighted LLM prevalence from hard yes/no responses.
- Weighted LLM prevalence from probability-of-yes responses.
- Absolute error in percentage points and mean absolute error across outcomes.
- Number/proportion of outcomes within 3, 5, and 10 percentage points.
- Gender, rural/urban, and age subgroup fidelity.
- Weighted individual accuracy, sensitivity, specificity, and Brier score.
- Majority-class baseline.
- Rich-versus-thin comparison.

## Primary tolerance
The primary interpretive benchmark is ±5 percentage points for aggregate estimates. This is an operational proof-of-concept threshold, not a universal statistical standard.

## Prompt and API discipline
Question wording, persona construction, sample membership, sample seed, outcome definitions, response schema, model identifiers, and evaluation metrics are frozen before paid inference. Request order is reproducibly randomized. Each synthetic respondent is generated in an independent request. Provider fallback is disabled for the main runs so model/provider identity is stable.

## Policy interpretation
Strong retrospective performance supports a prospective shadow-survey pilot in which synthetic predictions are generated before corresponding human survey results become available. It does not support replacing official human surveys. Mixed performance should lead to domain- or subgroup-specific recommendations. Weak performance should constrain use to lower-stakes exploratory tasks such as questionnaire pretesting or hypothesis generation.

## Secondary human survey
A small convenience sample may be used only as an exploratory acceptability study about possible uses of LLM-generated preliminary estimates. It is not a nationally representative validation sample.
