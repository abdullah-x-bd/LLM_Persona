# Preflight gate

No paid inference is authorized by this folder yet.

A full paid run may be enabled only after all of the following pass:

1. Unit tests, including leakage rejection, structured-response validation, exact prompt identity across reasoning conditions, real CAMS column parser test, sampling test, and paid-run lock test.
2. Dry fixture expansion produces exactly one `none`, `low`, and `high` request for every respondent.
3. Deterministic mock run produces zero parse errors and the smoke analysis completes.
4. Real `CSV_CAMS_79.zip` preparation succeeds with the final sample size and no merge, missing-value, uniqueness, or leakage failures.
5. Real request cost projection is below the Study 1 cap.
6. No-cost OpenRouter metadata check confirms that `qwen/qwen3.8-27b` is still listed, supports reasoning and structured outputs, and its live price has not exceeded the configured price guard.
7. A very small paid pilot is run only after the previous gates pass. The pilot is used only to measure parsing reliability, latency, token usage, and realized cost. It must not be used to inspect or tune the substantive result.
8. The full-run sample size is frozen from pilot token-cost data before any full-run outcome analysis.
9. The full run remains protected by both the config flag and the `RPF_ENABLE_PAID=YES_I_ACCEPT_COST` environment variable.
10. Total project spend must remain within USD 10.30.

Current primary model price snapshot, checked 2026-08-30: qwen/qwen3.8-27b at USD 0.35 per million input tokens and USD 2.75 per million output tokens. Price must be rechecked immediately before the paid pilot.
