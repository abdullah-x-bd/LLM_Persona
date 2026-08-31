# S04 PLFS cross-domain reasoning replication

**Question:** Does the reasoning effect on synthetic-population fidelity generalize beyond digital inclusion?

## Planned design

Population: 1,000 deterministically selected respondents from the frozen PLFS 2023–24 persona-code bundle.

Model: `deepseek/deepseek-v4-flash-0731` on AkashML, no provider fallback, data collection `deny`.

Paired arms:

- rich persona, reasoning off, 256-token completion cap
- rich persona, reasoning high, 1,800-token completion cap

Outcomes: labour-force participation, employment, unemployment, self-employment, regular wage/salaried employment, and casual labour using the current-weekly-status framing already implemented in the PLFS branch.

DeepSeek high reasoning is used because the live metadata gate verified it can be disabled and supports high effort. The earlier GPT-OSS candidate was rejected before paid inference because its reasoning is mandatory.

## Hard scientific launch block

The repository currently lacks a separate matched PLFS truth bundle. Production inference is prohibited until `data/encrypted/plfs_2023_24_truth.enc.b64` exists and all of the following have been verified before generation:

1. respondent IDs match the selected PLFS persona codes;
2. the six target outcomes are documented and reproducibly recoded;
3. analysis weights are present and validated;
4. the request set is frozen and hashed;
5. the truth bundle remains inaccessible to the generation runner.

Engineering-only proxy pilots may use existing PLFS persona codes to validate prompting, provider routing, schema handling, latency, and cost accounting. Such proxy responses are never part of S04 scientific data and do not remove this launch block.

## Cost planning

S04 uses the same DeepSeek off/high arm structure as S01. A current proxy-based ceiling can be calculated from actual PLFS prompt lengths, but the authoritative production cost will be recomputed only after the final 1,000-person request set is frozen and the truth asset is restored.
