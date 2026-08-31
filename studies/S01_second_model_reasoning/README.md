# S01 Second-model reasoning replication

**Question:** Does the reasoning-induced micro/macro divergence replicate outside Qwen?

Design: 1,000 existing frozen CAMS respondents, rich persona, paired `off` and `medium` reasoning, `openai/gpt-oss-120b`, AkashML only, no fallback. Primary comparison is medium minus off on survey-weighted individual Brier and population probability-prevalence MAE; hard prevalence MAE and hard accuracy are key secondary metrics.

This study uses the existing CAMS truth bundle only after generation. The generation runner never loads truth. Its rich arms are reused by S03.
