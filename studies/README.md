# Confirmatory follow-up study suite

This directory contains the five experiments designed after the first repo-wide synthesis. They are implemented as one guarded suite so identical arms are not paid for twice and all studies use the same privacy, provider, schema, cost-accounting, and artifact rules.

## Scientific objective

The umbrella hypothesis is that synthetic-population fidelity is multi-level: an intervention can improve respondent-level probabilistic prediction without improving, and sometimes while degrading, aggregate prevalence, categorical responses, subgroup structure, or the joint distribution of synthetic respondents.

## Studies

| ID | Study | New paid arms | Current readiness |
|---|---|---|---|
| S01 | Second-model reasoning replication | GPT-OSS-120B rich persona, off vs medium reasoning, 1,000 paired CAMS respondents | Preflight-ready |
| S02 | Length-safe reasoning replication | Qwen3.8-27B rich persona, off vs medium reasoning, 1,000 paired CAMS respondents, large completion headroom | Preflight-ready |
| S03 | Persona × reasoning factorial | GPT-OSS-120B thin off and thin medium on 1,000 CAMS respondents; rich arms are reused from S01 | Preflight-ready |
| S04 | PLFS cross-domain reasoning replication | GPT-OSS-120B rich off vs medium on 1,000 PLFS respondents | Blocked until the matched PLFS truth bundle is restored |
| S05 | Fresh preregistered holdout | 500 never-before-analysed CAMS respondents across four predeclared arms | Blocked until fresh codes and truth are frozen |

The exact machine-readable specification is `studies/registry.json`.

## Safety and spending rules

No file in this directory performs paid inference merely because it is pushed. Paid execution requires all of the following:

1. the study has all required encrypted data assets;
2. static request construction succeeds;
3. the live zero-cost OpenRouter preflight succeeds;
4. the requested model still supports structured outputs, `max_tokens`, and reasoning where required;
5. an AkashML endpoint is available and falls inside the live study ceiling;
6. provider fallbacks remain disabled;
7. provider data collection is set to `deny`;
8. available OpenRouter credit covers the single-pass ceiling;
9. the caller explicitly enters `I_ACCEPT_PAID_INFERENCE` in the manual paid workflow.

Human truth is never loaded by the generation runner. Respondent-level model output is encrypted before it is uploaded as a workflow artifact.

## Shared code

- `common/suite_core.py` reconstructs frozen respondents and requests and performs static/data readiness checks.
- `common/openrouter_preflight.py` queries only metadata/key endpoints and computes live cost ceilings. It never calls chat completions.
- `common/paid_runner.py` is the guarded production inference runner.

## Reuse rule

S03 deliberately does not regenerate the rich-persona GPT-OSS arms. Those are byte-compatible experimental cells from S01 and are reused in the 2 × 2 analysis. This saves roughly half of the factorial inference cost and prevents an unnecessary second draw from becoming a hidden nuisance variable.

## Before publication

Every paid study must receive a frozen request-set hash, run ID, provider endpoint tag, realized cost, retry count, completion/length-failure audit, and a truth-separated aggregate analysis record. Exploratory diagnostics must be labeled separately from preregistered confirmatory metrics.
