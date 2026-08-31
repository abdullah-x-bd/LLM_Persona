# S02 Length-safe Qwen reasoning replication

**Question:** Does the original Qwen result survive when completion truncation is engineered to be negligible?

Design: all 1,000 frozen CAMS respondents, rich persona, paired reasoning `off` versus `medium`, `qwen/qwen3.8-27b`, AkashML only, no fallback. The medium arm receives 3,200 maximum completion tokens, more than double the original 1,430-token production cap. The same 256-token cap is used for the off arm.

The primary confirmatory test is medium minus off for survey-weighted individual Brier and population probability-prevalence MAE. Hard prevalence MAE, hard accuracy, log loss, calibration, entropy, TV/JS distance, and the frequency of `finish_reason=length` are prespecified secondary checks. The study should not be described as length-safe unless the realized length-failure rate is below the preregistered tolerance.
