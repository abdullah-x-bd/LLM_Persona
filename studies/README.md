# Follow-up study suite

The follow-up suite is frozen for the current manuscript.

| ID | Design | Final status |
|---|---|---|
| S01 | DeepSeek rich persona, reasoning off vs high, n=1,000 paired CAMS | **COMPLETE AND ANALYZED** |
| S02 | Length-safe Qwen off vs medium | **ARCHIVED, UNRUN** |
| S03 | DeepSeek 2 × 2 persona × reasoning factorial, n=1,000 | **COMPLETE AND ANALYZED** |
| S04 | PLFS DeepSeek reasoning replication | **SCIENTIFICALLY BLOCKED**, no matched truth bundle |
| S05 | Fresh CAMS holdout confirmation | **ARCHIVED, UNRUN** |

S01 and S03 are the only new paid follow-up studies included in the current paper. Their final production provider was OpenInference FP8, with fallbacks disabled, provider data collection `deny`, and human truth excluded from generation. S03 reuses the exact S01 rich/off and rich/high cells.

S02 and S05 remain preserved as prospective designs for provenance or future work. They should not be described as completed studies. S04 must not be launched or interpreted scientifically until a matched PLFS truth asset exists.

## Completed DeepSeek evidence

S01 shows that high reasoning can improve Brier, hard accuracy, probability prevalence, hard prevalence, and joint population structure, while worsening log loss through a larger tail of extreme wrong probabilities.

S03 shows that persona information and reasoning interact. Reasoning substitutes for some missing persona information for individual Brier, but complements rich information for hard population reconstruction. The factorial analysis also recovers a strong age gradient and substantial changes in response-pattern diversity.

This result is intentionally contrasted with the completed Qwen reasoning study, where medium reasoning improves Brier/log loss but worsens hard accuracy and population prevalence. The final zero-inference analysis estimates the Qwen-versus-DeepSeek reasoning heterogeneity directly with a paired respondent bootstrap.

## Canonical records

- Machine status and artifact IDs: `registry.json`
- S01: `S01_second_model_reasoning/README.md`
- S03: `S03_persona_reasoning_factorial/README.md`
- DeepSeek results: `../docs/DEEPSEEK_S01_S03_FACTORIAL_RESULTS.md`
- Final cross-study analysis: `../analysis_final/`
- Pre-manuscript audit: `../docs/PRE_MANUSCRIPT_AUDIT.md`

Historical preflight, provider-scan, engineering, production, and recovery code is retained as provenance. No additional inference is part of the current manuscript plan.
