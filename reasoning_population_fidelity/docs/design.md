# Study design checkpoint

## Working title

**Does Thinking Make Synthetic People Less Human? Reasoning, Demographic Overdetermination, and Uncertainty in LLM Population Simulation**

## Primary empirical setting

Government of India CAMS 2022-23 respondent microdata, using real respondent attributes to construct personas while withholding target outcomes for ground-truth evaluation.

## Study 1

Within-person paired comparison across reasoning conditions using the same model, prompt, respondent, question set, and sampling configuration.

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

## Study 2

Run the same frozen respondent sample across several economical model families. Measure whether cross-model disagreement predicts synthetic-human mismatch and whether disagreement-based deferral improves fidelity at reduced coverage.

## Baselines

- population marginal
- demographic cell estimator
- regularized logistic regression
- gradient-boosted trees

## Budget policy

Total OpenRouter budget available for this study: USD 10.30.

The pipeline should target approximately USD 7-8 for the main experiments and retain the remainder for pilot failures, retries, and robustness checks. Exact model choices and run sizes will be frozen only after current pricing and token-cost preflight calculations.

## Execution order

1. reconstruct CAMS variables and codebook
2. choose permissible persona variables and hidden target outcomes
3. construct survey-weighted frozen sample
4. implement non-LLM baselines
5. freeze prompt and output schema
6. implement request cache, retries, checkpoints, token/cost ledger
7. run complete zero-cost dry test
8. execute tiny paid pilot
9. inspect pilot and freeze primary analysis plan
10. launch full run
11. run prespecified analysis and robustness checks

## Isolation rule

All future work for this experiment should be created under `reasoning_population_fidelity/` unless an explicit decision is made to migrate it elsewhere.
