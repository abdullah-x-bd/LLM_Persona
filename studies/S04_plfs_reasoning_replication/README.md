# S04 PLFS cross-domain reasoning replication

**Question:** Does reasoning alter synthetic-population fidelity outside digital inclusion?

Planned design: 1,000 deterministically selected respondents from the already frozen PLFS 2023–24 persona-code bundle, rich persona, paired `off` and `medium` reasoning using `openai/gpt-oss-120b` on AkashML.

The six outcomes are labour-force participation, employment, unemployment, self-employment, regular wage/salaried employment, and casual labour under the current-weekly-status framing used in the existing PLFS branch.

**Hard launch block:** the repository currently lacks a separate matched PLFS truth bundle. No paid inference is allowed until `data/encrypted/plfs_2023_24_truth.enc.b64` exists, its respondent IDs are verified against the selected persona codes, and its six outcome recodes plus analysis weights are documented. This prevents spending on a run that cannot be evaluated against human truth.
