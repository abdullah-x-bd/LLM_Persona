# S03 Persona × reasoning factorial

**Question:** Does reasoning interact with how much factual respondent information the model receives?

The complete design is a 2 × 2 factorial on the same 1,000 frozen CAMS respondents using `openai/gpt-oss-120b`:

- thin persona, reasoning off
- thin persona, reasoning medium
- rich persona, reasoning off
- rich persona, reasoning medium

Only the two thin arms are new paid inference. The two rich arms are the S01 outputs and must be reused exactly. The primary estimand is the persona × reasoning interaction, evaluated separately for individual Brier, probability-prevalence MAE, hard prevalence MAE, and hard accuracy.

The mechanism hypothesis to freeze before results are inspected is that reasoning may rely more heavily on learned demographic priors when the persona is sparse, so the reasoning effect may differ between thin and rich profiles.
