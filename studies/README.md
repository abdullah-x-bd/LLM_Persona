# Confirmatory follow-up study suite

This directory contains the five experiments designed after the repo-wide synthesis. They are implemented as one guarded suite so identical arms are not paid for twice and all studies use the same privacy, provider, schema, cost-accounting, and artifact rules.

## Scientific objective

The umbrella hypothesis is that synthetic-population fidelity is multi-level: an intervention can improve respondent-level probabilistic prediction without improving, and sometimes while degrading, aggregate prevalence, categorical responses, subgroup structure, or the joint distribution of synthetic respondents.

## Studies

| ID | Study | New paid arms | Current readiness |
|---|---|---|---|
| S01 | Second-model reasoning replication | DeepSeek V4 Flash 0731 rich persona, reasoning off vs high, 1,000 paired CAMS respondents | **Zero-cost preflight passed** |
| S02 | Length-safe reasoning replication | Qwen3.8-27B rich persona, off vs medium, 1,000 paired CAMS respondents, 3,200-token medium cap | **Zero-cost preflight passed** |
| S03 | Persona × reasoning factorial | DeepSeek thin/off and thin/high on 1,000 CAMS respondents; rich cells reused from S01 | **Zero-cost preflight passed** |
| S04 | PLFS cross-domain reasoning replication | DeepSeek rich/off vs rich/high on 1,000 PLFS respondents | **Blocked** until matched PLFS truth is restored; cost projection is available |
| S05 | Fresh preregistered holdout | 500 untouched CAMS respondents across four predeclared arms | **Blocked** until fresh codes and truth are frozen; cost projection uses existing CAMS prompt lengths only |

The exact machine-readable specification is `studies/registry.json`.

## Why DeepSeek replaced GPT-OSS

The first zero-cost gate evaluated `openai/gpt-oss-120b` for the second-model studies and found that current OpenRouter metadata marks reasoning as mandatory. That makes a genuine reasoning-off arm impossible. No paid inference had been performed. The design was therefore corrected prospectively to `deepseek/deepseek-v4-flash-0731`, for which the same gate verified optional reasoning and a supported `high` effort on the pinned AkashML endpoint.

This engineering correction is part of the provenance record and should be reported if the follow-up experiments enter a paper appendix.

## Current hard single-pass ceilings

These are **worst-case ceilings**, calculated as if every request consumes its full maximum completion allowance. They are not forecasts of realized spend.

- S01 live AkashML ceiling: **$0.452429**
- S02 live AkashML ceiling: **$9.256217**
- S03 live AkashML ceiling for the two new thin cells: **$0.430298**

S04 and S05 are cost-projected during preflight but remain impossible to launch while their required scientific assets are missing. The latest machine-readable reports are stored as the `followup-study-suite-preflight` GitHub Actions artifact.

## Safety and spending rules

No file in this directory performs paid inference merely because it is pushed. Paid execution requires all of the following:

1. all encrypted codes and human-truth assets required for the study exist;
2. static request construction succeeds;
3. the live zero-cost OpenRouter preflight succeeds immediately before spending;
4. the model still supports structured outputs, `max_tokens`, and the frozen reasoning conditions;
5. the selected AkashML endpoint supports every required parameter;
6. provider fallbacks remain disabled;
7. provider data collection is set to `deny`;
8. the live hard single-pass ceiling is below the study's registered cap;
9. any configured per-key OpenRouter limit has enough remaining capacity;
10. the caller explicitly enters `I_ACCEPT_PAID_INFERENCE` in the manual paid workflow.

The ordinary inference key currently reports no per-key limit, so `/api/v1/key` cannot reveal the account-wide prepaid balance. For the expensive S02/S05 runs, account credit must therefore also be checked in OpenRouter or through a management-key credits endpoint before launch. This does not weaken the workflow's own explicit study spend cap.

Human truth is never loaded by the generation runner. Respondent-level model output is encrypted before it is uploaded as a workflow artifact.

## Shared code

- `common/suite_core.py` reconstructs frozen respondents and requests, performs launch readiness checks, and computes static/proxy cost projections.
- `common/openrouter_preflight.py` queries metadata/key endpoints and live provider pricing. It contains no chat-completions call.
- `common/paid_runner.py` is the explicitly authorized production inference runner.
- `registry.json` freezes models, arm definitions, completion limits, source assets, study caps, and reuse relationships.

## Reuse rule

S03 deliberately does not regenerate the rich-persona DeepSeek cells. The rich/off and rich/high cells are exactly S01 and must be reused in the 2 × 2 factorial analysis. This saves approximately half of the factorial inference cost and avoids introducing a second stochastic draw as an uncontrolled nuisance variable.

## Before publication

Every paid study must receive a frozen request-set hash, run ID, model and provider endpoint tag, realized cost, retry count, finish-reason/length-failure audit, and a truth-separated aggregate analysis record. Exploratory diagnostics must be labeled separately from preregistered confirmatory metrics.
