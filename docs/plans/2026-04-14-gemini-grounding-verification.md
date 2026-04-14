# Gemini Grounding Verification

## Purpose

Keep Gemini-backed web search verifiable after provider or parser changes. The workflow below covers fixture refresh, opt-in live verification, and failure triage when Gemini starts returning empty or malformed search results.

## Operator Workflow

1. Capture a new fixture when the live Gemini grounding shape changes.
   - Run `python scripts/capture_gemini_grounding.py --output tests/fixtures/gemini_grounding_response.json`.
   - If credentials are unavailable, the canonical fixture command exits without writing. Use a temporary output path only if you need a synthetic sample for local inspection, and do not treat that sample as a real refresh.
   - Update the fixture only after checking that the captured payload still contains usable `grounding_chunks` and `grounding_supports`.
2. Run the live verification test only when you need to validate the real provider path.
   - Set `RUN_LIVE_GEMINI_GROUNDING=1`.
   - Provide `GEMINI_API_KEY` or one of `GEMINI_API_KEY_1` through `GEMINI_API_KEY_10`.
   - Optionally set `GEMINI_LIVE_MODEL` and `GEMINI_LIVE_QUERY` if you want to override the defaults used by `tests/test_gemini_grounding_live.py`.
3. Inspect failures in this order if Gemini results look empty or malformed.
   - Check whether the live test is skipping because the opt-in env var or API key is missing.
   - Confirm Gemini returned at least one candidate with usable grounding metadata.
   - Verify `_extract_gemini_results` still sees valid chunk URIs, stable titles, and non-empty snippet text.
   - If Gemini metadata is missing or malformed, expect the search path to fall back to Brave, then DuckDuckGo.

## Verification Expectations

- The fixture-backed parser test should lock the normalized `title`/`url`/`snippet` shape for known payloads.
- The live test should be opt-in and is allowed to skip by default in CI or local runs.
- Parser fallback behavior should prefer usable Gemini grounding data, ignore empty or malformed metadata, and preserve the fallback search order when Gemini cannot produce results.

## Maintenance Cadence

- Refresh the fixture whenever Gemini changes its grounding payload shape or the parser contract is adjusted.
- Run the live test after parser changes, provider selection changes, or any manual fixture refresh that may have altered the captured response.
- If a live run fails, compare the current response with the fixture before changing parser logic.
