# Study 1 engineering change log

This log records engineering-only changes made after paid canaries and before the full Study 1 production run. Human CAMS truth was not loaded for scoring during these decisions, no human-versus-model fidelity metric was calculated, and substantive response content was not inspected to choose any change below.

## 2026-08-30: xhigh final-content incompatibility

The original version-2 treatment used `off / low / xhigh`. Paid canaries repeatedly showed schema-valid `off` and `low` responses while `xhigh` failed to expose a usable final structured answer under completion ceilings compatible with the Study 1 budget. Compacting the machine response and increasing xhigh completion headroom did not make xhigh operationally reliable.

The highest treatment was therefore changed to the model's next-highest native reasoning effort, `medium`. The final version-3 treatment is `off / low / medium`. The same 1,000 CAMS respondents, personas, six survey questions, response schema, model, deterministic generation settings, paired design, outcomes, and analysis direction were retained.

## 2026-08-30: transient null-content response on low

The first version-3 paid canary produced a valid `off` response and then received a paid HTTP-success response for `low` whose message content was null. The runner stopped immediately, so `medium` was never reached. Because `low` had already produced valid paid responses in earlier canaries, this failure was treated as provider or serving-path intermittency rather than evidence of a treatment incompatibility.

The successful `off` request in that canary was billed at exactly the current AkashML price implied by its token usage, identifying the price-sorted serving path as AkashML. This motivated fixing provider identity for the final experiment so provider variation cannot masquerade as a reasoning-treatment effect.

## 2026-08-30: bounded application-level retries and complete attempt accounting

OpenRouter provider failover handles provider errors, but an HTTP-success response with null final content can reach the application without triggering provider failover. The engineering runner therefore now permits up to three application-level attempts per respondent-condition request.

Every HTTP response is accounted for before content parsing. Prompt tokens, completion tokens, reasoning tokens, provider identity, generation ID, and any known billed cost are recorded for every received attempt, including attempts whose final content is empty or invalid. A null or malformed final response is retried only while attempts remain. A request is accepted only after the existing strict response validator passes.

Pilot authorization ceilings were raised only to cover the full worst case of all three attempts being billed at the frozen provider price ceiling. The 1-respondent canary is capped at USD 0.02 and the 20-respondent, 60-request engineering pilot is capped at USD 0.38. These are hard authorization ceilings, not expected spend. The full Study 1 production budget remains unchanged.

## 2026-08-30: privacy-filter incompatibility of Alibaba pin

A subsequent canary pinned to Alibaba returned `404: No endpoints found for qwen/qwen3.8-27b` on all three attempts before any provider response was received. The live model endpoint metadata alone had shown Alibaba as price- and parameter-compatible, but the request also retained the frozen `data_collection = deny` policy.

OpenRouter's published provider policy lists Alibaba Cloud Int. as retaining prompts, while AkashML is listed as zero retention. OpenRouter documents that `data_collection = deny` restricts routing to providers that do not collect user data. The Alibaba endpoint was therefore incompatible with the experiment's existing privacy filter and was correctly eliminated by the router.

The provider pin is now the exact `akashml/fp8` endpoint. AkashML is zero retention under OpenRouter's published provider table, its Qwen3.8 27B endpoint supports the frozen model parameters and remains within the price ceiling, and it has already returned valid paid `off` and `low` responses in prior canaries. `data_collection = deny` remains unchanged, provider fallbacks remain disabled, and the three-attempt bounded retry/accounting layer remains in place to handle transient empty completions.

No change in this log was motivated by observed predictive performance.
