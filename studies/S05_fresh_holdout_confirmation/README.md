# S05 Fresh preregistered holdout confirmation

**Question:** Do the principal patterns discovered in the existing repository survive a genuinely untouched respondent sample?

Planned sample: 500 CAMS respondents not used in the original 1,000-person study or in hypothesis formation.

Frozen four-arm design:

1. Qwen thin persona, reasoning off
2. Qwen rich persona, reasoning off
3. Qwen rich persona, reasoning medium
4. GPT-OSS rich persona, reasoning off

These cells jointly retest persona enrichment, reasoning, model-identity population shifts, and joint-distribution compression without requiring a prohibitively large factorial.

**Hard launch block:** both `data/encrypted/cams_holdout_codes_v1.x25519.aesgcm.gz.b64` and `data/encrypted/cams_holdout_truth_v1.x25519.aesgcm.gz.b64` must be created from source microdata under a documented exclusion rule proving that none of the 500 respondents is in the original analysis sample. Hypotheses, primary contrasts, outcome coding, and analysis code must be frozen before the new truth is inspected.
