# S05 Fresh preregistered holdout confirmation

**Question:** Do the principal patterns discovered in the existing repository survive a genuinely untouched respondent sample?

## Planned sample

500 CAMS respondents that are demonstrably disjoint from the original 1,000-person CAMS analysis sample and were not used to formulate the follow-up hypotheses.

## Frozen four-arm design

1. Qwen thin persona, reasoning off
2. Qwen rich persona, reasoning off
3. Qwen rich persona, reasoning medium with 3,200-token headroom
4. DeepSeek V4 Flash rich persona, reasoning off

This compact design prospectively retests persona enrichment, reasoning, model-identity population shifts, and joint-distribution compression without a prohibitively large full factorial.

DeepSeek replaces the earlier GPT-OSS candidate because the zero-cost OpenRouter gate found GPT-OSS reasoning mandatory. DeepSeek can be run with reasoning disabled and passed the pinned AkashML parameter checks.

## Hard launch block

Both of these assets must exist before scientific inference:

- `data/encrypted/cams_holdout_codes_v1.x25519.aesgcm.gz.b64`
- `data/encrypted/cams_holdout_truth_v1.x25519.aesgcm.gz.b64`

Before launch, the build must prove respondent-ID disjointness from the original 1,000, freeze and hash the 500-person sample, freeze primary contrasts and analysis code, and keep the truth bundle separated from generation.

Engineering-only proxy pilots may substitute existing CAMS personas solely to test model/provider/schema/latency/cost plumbing. Those responses are discarded and can never enter S05 analysis.

## Primary contrasts

- Qwen rich/off minus Qwen thin/off
- Qwen rich/medium minus Qwen rich/off
- DeepSeek rich/off minus Qwen rich/off

The shared confirmatory metric panel is defined in `docs/FOLLOWUP_EXPERIMENT_PLAN.md`.

## Cost planning

Because the fresh holdout does not yet exist, all present S05 dollar figures are planning estimates based on the existing CAMS prompt-length distribution. The production ceiling must be recomputed from the actual frozen holdout immediately before paid inference.
