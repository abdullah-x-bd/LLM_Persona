# Study design checkpoint

## Working title

**Does Thinking Make Synthetic People Less Human? Reasoning, Demographic Overdetermination, and Uncertainty in LLM Population Simulation**

## Primary empirical setting

Government of India CAMS 2022-23 respondent microdata, using real respondent attributes to construct personas while withholding target outcomes for ground-truth evaluation.

## Study 1

Within-person paired comparison across reasoning conditions using the same model, prompt, respondent, question set, generation configuration, and sampling configuration.

Primary planned conditions:

1. reasoning none
2. reasoning low
3. reasoning high

Primary outcome families:

- individual response fidelity
- survey-weighted prevalence error
- subgroup prevalence error
- distributional distance
- response-vector diversity
- conditional entropy
- demographic dependence / overdetermination

The co-primary frozen metrics and analysis order are specified in `docs/ANALYSIS_PLAN_FROZEN.md` before any paid inference.

## Study 2

Run the same frozen respondent sample across several economical model families. Measure whether cross-model disagreement predicts synthetic-human mismatch and whether disagreement-based deferral improves fidelity at reduced coverage.

## Baselines

- population marginal
- demographic cell estimator
- regularized logistic regression
- gradient-boosted trees

## Budget policy

Total OpenRouter budget available for this study: USD 10.30.

The pipeline targets approximately USD 7-8 for the main experiments and retains the remainder for pilot failures, retries, and robustness checks. The full Study 1 sample remains 1,000 respondents unless the engineering pilot demonstrates that the frozen run cannot fit within the hard budget ceiling.

## Execution order

1. reconstruct CAMS variables and codebook
2. choose permissible persona variables and hidden target outcomes
3. construct survey-weighted frozen sample
4. implement non-LLM baselines
5. freeze prompt and output schema
6. implement request cache, retries, checkpoints, token/cost ledger
7. run complete zero-cost dry test
8. generate and hash the complete 3,000-request real CAMS set
9. freeze primary analysis plan before model outputs are observed
10. execute tiny paid engineering pilot without human-truth comparison
11. verify parsing, routing, token usage, latency, and realized cost only
12. if engineering checks pass, launch the full frozen run
13. run the prespecified analysis and robustness checks

## Isolation rule

All future work for this experiment should be created under `reasoning_population_fidelity/` unless an explicit decision is made to migrate it elsewhere.
