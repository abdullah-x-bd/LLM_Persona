# Preflight gate

No paid inference is authorized by this folder yet.

A full paid run may be enabled only after all of the following pass:

1. Unit tests, including leakage rejection, structured-response validation, exact prompt identity across reasoning conditions, real CAMS column parser test, sampling test, and paid-run lock test.
2. Dry fixture expansion produces exactly one `none`, `low`, and `high` request for every respondent.
3. Deterministic mock run produces zero parse errors and the smoke analysis completes.
4. Real `CSV_CAMS_79.zip` preparation succeeds with the final sample size and no merge, missing-value, uniqueness, or leakage failures.
5. Real request cost projection is below the Study 1 cap.
6. No-cost OpenRouter metadata check confirms that `qwen/qwen3.8-27b` is still listed, supports reasoning and structured outputs, and at least one compatible endpoint fits the hard provider price ceiling.
7. A very small paid pilot is run only after the previous gates pass. The pilot is used only to measure parsing reliability, latency, token usage, and realized cost. It must not be used to inspect or tune the substantive result.
8. The full-run sample size is frozen from pilot token-cost data before any full-run outcome analysis.
9. The full run remains protected by both the config flag and the `RPF_ENABLE_PAID=YES_I_ACCEPT_COST` environment variable.
10. Total project spend must remain within USD 10.30.

## Current dry status

Passed locally and in the deterministic harness:

- Python compilation.
- Five unit tests.
- Exact-CAMS-column synthetic ZIP parsing and household/member merge.
- Stratified sampling path.
- Persona leakage guard.
- Identical prompts across reasoning conditions.
- Strict structured response parser.
- Eighteen-request end-to-end deterministic mock run with zero parse errors.
- Smoke analysis.
- Paid-run double lock.

The first online metadata check correctly stopped because routed pricing differed from the initial catalog snapshot. The configuration was then tightened using the live routed metadata and a provider-level hard price ceiling rather than disabling the price gate.

## Price controls

On 2026-08-30 the authenticated OpenRouter model metadata returned USD 0.425 per million input tokens and USD 2.55 per million output tokens for the routed model entry. Provider-specific prices can differ. The future live request policy therefore also requires price sorting and rejects any provider above USD 0.50 per million prompt tokens or USD 3.00 per million completion tokens.

Study 1 completion ceilings are currently 200 tokens for `none`, 300 for `low`, and 400 for `high`, with a USD 7.80 Study 1 budget cap. These ceilings may only be changed before the paid pilot or in response to pilot engineering failures, never after inspecting substantive study results.

## Gate still requiring the actual source archive

The full real-data preflight requires the original `CSV_CAMS_79.zip`. Until that archive is available in the runtime, exact-column synthetic fixtures test the parser but do not substitute for the final real-data merge and cost projection.
