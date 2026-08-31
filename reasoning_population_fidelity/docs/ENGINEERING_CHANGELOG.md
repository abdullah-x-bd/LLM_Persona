# Study 1 engineering change log

This log records engineering-only decisions made around Study 1, including pre-production changes and post-launch operational recovery. Human CAMS truth was not loaded for scoring when the pre-production treatment, provider, token-cap, and retry decisions were made. After an interim aggregate analysis was later viewed, no prompt, persona, model, provider, reasoning treatment, response schema, outcome, analysis rule, or frozen request ID was changed; subsequent changes were limited to operational completion and are disclosed below.

## 2026-08-30: xhigh final-content incompatibility

The original version-2 treatment used `off / low / xhigh`. Paid canaries repeatedly showed schema-valid `off` and `low` responses while `xhigh` failed to expose a usable final structured answer under completion ceilings compatible with the Study 1 budget. Compacting the machine response and increasing xhigh completion headroom did not make xhigh operationally reliable.

The highest treatment was therefore changed to the model's next-highest native reasoning effort, `medium`. The final version-3 treatment is `off / low / medium`. The same 1,000 CAMS respondents, personas, six survey questions, response schema, model, deterministic generation settings, paired design, outcomes, and analysis direction were retained.

## 2026-08-30: transient null-content response on low

The first version-3 paid canary produced a valid `off` response and then received a paid HTTP-success response for `low` whose message content was null. The runner stopped immediately, so `medium` was never reached. Because `low` had already produced valid paid responses in earlier canaries, this failure was treated as provider or serving-path intermittency rather than evidence of a treatment incompatibility.

The successful `off` request in that canary was billed at exactly the current AkashML price implied by its token usage, identifying the price-sorted serving path as AkashML. This motivated fixing provider identity for the final experiment so provider variation cannot masquerade as a reasoning-treatment effect.

## 2026-08-30: bounded application-level retries and complete attempt accounting

OpenRouter provider failover handles provider errors, but an HTTP-success response with null final content can reach the application without triggering provider failover. The engineering runner therefore permits up to three application-level attempts per respondent-condition request in a normal collection cycle.

Every HTTP response is accounted for before content parsing. Prompt tokens, completion tokens, reasoning tokens, provider identity, generation ID, and any known billed cost are recorded for every received attempt, including attempts whose final content is empty or invalid. A null or malformed final response is retried only while attempts remain. A request is accepted only after the existing strict response validator passes.

## 2026-08-30: final completion-cap reallocation before substantive scoring

Engineering pilots showed that the earlier draft completion ceilings did not allocate enough room to the feasible reasoning arms while spending unnecessary headroom on reasoning-off. Before the full production run and before human truth was loaded for scoring, the final request configuration was reallocated to `off = 120`, `low = 1100`, and `medium = 1430` maximum completion tokens. These are the values in `reasoning_population_fidelity/config/preflight.json` and in the frozen 3,000-request set whose SHA256 is `120cc6bef15e7b2eb8fb2c49c7efa2fab5496b0a429cf34c8d9100b588cf9293`.

The `Generation configuration` prose in `ANALYSIS_PLAN_FROZEN.md` still lists an earlier draft ceiling triplet (`250 / 600 / 1200`). That line is stale documentation and was not the configuration used to generate Study 1. The frozen request set and final pre-production configuration are authoritative for the actual treatment implementation. This discrepancy is documented rather than silently rewriting the pre-run analysis-plan file after outcomes were observed.

No human-vs-model accuracy, prevalence error, Brier score, subgroup result, or other substantive fidelity metric was used to choose the `120 / 1100 / 1430` allocation.

## 2026-08-30: privacy-filter incompatibility of Alibaba pin

A subsequent canary pinned to Alibaba returned `404: No endpoints found for qwen/qwen3.8-27b` on all three attempts before any provider response was received. The live model endpoint metadata alone had shown Alibaba as price- and parameter-compatible, but the request also retained the frozen `data_collection = deny` policy.

OpenRouter's published provider policy lists Alibaba Cloud Int. as retaining prompts, while AkashML is listed as zero retention. OpenRouter documents that `data_collection = deny` restricts routing to providers that do not collect user data. The Alibaba endpoint was therefore incompatible with the experiment's existing privacy filter and was correctly eliminated by the router.

The provider pin was fixed to the exact `akashml/fp8` endpoint. `data_collection = deny` remained unchanged and provider fallbacks remained disabled.

## 2026-08-31: production credit exhaustion and checkpointed resume

The first 3,000-request production attempt began normally but later encountered OpenRouter `402` insufficient-credit rejections after the account balance was exhausted. The run preserved 963 schema-valid requests in an encrypted checkpoint. Definite 402 rejections were subsequently treated as zero-cost rejections in resume accounting rather than as hypothetical full-price completions.

Resume workflows always reconstructed the exact frozen request set, verified the request SHA256, decrypted the prior checkpoint only inside GitHub Actions, skipped already-successful request IDs, and submitted only missing frozen requests. No human truth was loaded during collection.

## 2026-08-31: post-interim operational completion recovery

An interim aggregate analysis was viewed after partial collection. From that point onward, all recovery changes were restricted to operational completion. No treatment, prompt, schema, model, provider, reasoning effort, frozen completion cap, outcome, or analysis rule was changed.

The remaining reasoning requests were disproportionately `finish_reason = length` cases. Recovery therefore extended the number of identical operational retry cycles and changed concurrency/batch sizes while retaining the same frozen request payloads. Recovery cost ceilings were transparently extended beyond the original USD 7.80 Study 1 operational budget while remaining below the pre-existing USD 9.50 project hard cap. These extensions were made only to obtain the already-defined missing respondent-condition cells rather than to alter their substantive content.

The final completed artifact was produced by GitHub Actions run `33371250037`. Its integrity gate verified exactly 3,000 schema-valid unique requests, with 1,000 `off`, 1,000 `low`, and 1,000 `medium`; zero remaining failures; the frozen request SHA256 above; provider order exactly `akashml/fp8`; fallbacks disabled; and `data_collection = deny`. The final combined realized-or-guard accounting was USD 8.70589685.

The final attempt history contains 5,953 attempt records. The accepted dataset has 1,000 responses per condition. Failed `finish_reason = length` attempts are concentrated in reasoning-enabled arms: 510 in `low` and 343 in `medium`, versus zero in `off`. This operational asymmetry is analyzed explicitly in post hoc robustness checks rather than hidden.

No pre-production engineering change in this log was motivated by observed predictive performance. Post-interim changes are identified separately above and were limited to collecting the remaining cells under unchanged scientific treatments.
