# Follow-up study suite

Version 1.0.0 freezes the follow-up study boundary shown below.

| ID | Design | Status |
|---|---|---|
| S01 | DeepSeek rich persona, reasoning off vs high, n=1,000 paired CAMS | **COMPLETE AND ANALYZED** |
| S02 | Length-safe Qwen off vs medium | **ARCHIVED, UNRUN** |
| S03 | DeepSeek 2 × 2 persona × reasoning factorial, n=1,000 | **COMPLETE AND ANALYZED** |
| S04 | PLFS DeepSeek reasoning replication | **SCIENTIFICALLY BLOCKED**, no matched truth bundle |
| S05 | Fresh CAMS holdout confirmation | **ARCHIVED, UNRUN** |

S01 and S03 are the completed paid follow-up studies in the frozen evidence package. Their final production provider was OpenInference FP8, with fallbacks disabled, provider data collection set to `deny`, and human truth excluded from generation. S03 reuses the exact S01 rich/off and rich/high cells.

S02 and S05 are preserved as unrun prospective designs. S04 is excluded from truth-linked scientific claims because the repository does not contain a matched PLFS truth asset.

## Completed DeepSeek evidence

S01 shows that high reasoning can improve Brier, hard accuracy, probability prevalence, hard prevalence, and joint population structure while worsening log loss through a larger tail of extreme wrong probabilities.

S03 shows that persona information and reasoning interact. Reasoning substitutes for some missing persona information for individual Brier, but complements rich information for hard population reconstruction. The factorial analysis also recovers a strong age gradient and substantial changes in response-pattern diversity.

This result contrasts with the completed Qwen reasoning study, where medium reasoning improves Brier and log loss while worsening hard accuracy and population prevalence. The final zero-inference analysis estimates Qwen-versus-DeepSeek reasoning heterogeneity directly with a paired respondent bootstrap.

## Canonical records

- Machine status and artifact IDs: `registry.json`
- S01: `S01_second_model_reasoning/README.md`
- S03: `S03_persona_reasoning_factorial/README.md`
- DeepSeek results: `../docs/DEEPSEEK_S01_S03_FACTORIAL_RESULTS.md`
- Cross-study analysis: `../analysis_final/`
- Scientific freeze record: `../docs/SCIENTIFIC_FREEZE.md`

Historical preflight, provider-scan, engineering, production, and recovery code is retained for provenance. Version 1.0.0 contains no additional inference beyond the completed evidence described above.
