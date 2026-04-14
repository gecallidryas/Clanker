# Gemini Grounding Verification Implementation Plan

> Archived implementation plan retained after merge. The operational workflow lives in `2026-04-14-gemini-grounding-verification.md`.

**Goal:** Reduce the residual risk in explicit web search by verifying the Gemini grounding payload against a live response shape and hardening parsing behavior around missing or shifted metadata.

**Architecture:** Keep the existing Gemini-first search flow in `discord_bot/utils/web_search.py`, but add a fixture-backed parser contract and a small live verification script so the repo no longer depends only on mocked unit tests for grounding metadata. The production parser stays lightweight; the confidence comes from captured real payloads and failure-mode tests.

**Tech Stack:** Python, google-genai, unittest/pytest, existing Discord bot utility layout

---

### Task 1: Capture The Current Grounding Shape Safely

**Files:**
- Create: `E:\femboibot\scripts\capture_gemini_grounding.py`
- Create: `E:\femboibot\tests\fixtures\gemini_grounding_response.json`
- Check: `E:\femboibot\discord_bot\utils\web_search.py`

**Step 1: Write the failing test**

Add a parser-contract test that loads a fixture file and asserts the parser extracts at least one normalized result with `title`, `url`, and optional `snippet`.

```python
def test_extract_gemini_results_from_realistic_fixture():
    payload = json.loads(Path("tests/fixtures/gemini_grounding_response.json").read_text())
    response = FakeGeminiResponse.from_payload(payload)
    results = web_search._extract_gemini_results(response, max_results=5)
    assert results
    assert results[0]["url"].startswith("http")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_search.py -k gemini_fixture -v`
Expected: FAIL because the fixture and contract adapter do not exist yet.

**Step 3: Write minimal implementation**

Create:
- a one-off script that performs a Gemini `google_search` request and saves the raw response shape to a local JSON fixture
- a minimal test adapter or helper that reconstructs the parser input shape from the saved JSON

Do not commit secrets or raw API keys. The fixture should contain only response payload data.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_search.py -k gemini_fixture -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/capture_gemini_grounding.py tests/fixtures/gemini_grounding_response.json tests/test_web_search.py
git commit -m "test: capture gemini grounding fixture"
```

### Task 2: Harden Parser Behavior For Missing And Partial Metadata

**Files:**
- Modify: `E:\femboibot\tests\test_web_search.py`
- Modify: `E:\femboibot\discord_bot\utils\web_search.py`

**Step 1: Write the failing test**

Add focused tests for:
- missing `grounding_metadata`
- missing `grounding_supports`
- web chunks without titles
- duplicate URLs across chunks
- snippets attached to multiple chunk indices

```python
def test_extract_gemini_results_handles_missing_grounding_metadata():
    response = FakeGeminiResponse(candidates=[FakeCandidate(grounding_metadata=None)])
    assert web_search._extract_gemini_results(response, max_results=5) == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_search.py -k extract_gemini_results -v`
Expected: FAIL on at least one missing-shape edge case.

**Step 3: Write minimal implementation**

Tighten `_extract_gemini_results` so it:
- never throws on partial Gemini metadata
- consistently deduplicates URLs
- falls back to domain text when title is missing
- keeps snippet normalization deterministic

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_search.py -k extract_gemini_results -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_web_search.py discord_bot/utils/web_search.py
git commit -m "test: harden gemini grounding parser edge cases"
```

### Task 3: Add A Controlled Live Verification Path

**Files:**
- Create: `E:\femboibot\tests\test_gemini_grounding_live.py`
- Modify: `E:\femboibot\discord_bot\utils\web_search.py`
- Check: `E:\femboibot\discord_bot\utils\guild_ai.py`

**Step 1: Write the failing test**

Add a live test that is skipped unless an explicit env var such as `RUN_LIVE_GEMINI_GROUNDING=1` and a Gemini key are present. The test should run one real search and assert the parser returns normalized results.

```python
@pytest.mark.live
def test_live_gemini_grounding_contract():
    ...
```

**Step 2: Run test to verify it fails or skips correctly**

Run: `pytest tests/test_gemini_grounding_live.py -v`
Expected:
- SKIPPED when env vars are absent
- FAIL if the live contract is broken

**Step 3: Write minimal implementation**

Ensure the live test uses the same parser path as production rather than bespoke parsing logic.

**Step 4: Run test to verify expected behavior**

Run: `pytest tests/test_gemini_grounding_live.py -v`
Expected: SKIPPED in normal CI, PASS in an opted-in environment with valid Gemini credentials.

**Step 5: Commit**

```bash
git add tests/test_gemini_grounding_live.py discord_bot/utils/web_search.py
git commit -m "test: add opt-in live gemini grounding contract check"
```

### Task 4: Document Operational Verification And Failure Triage

**Files:**
- Modify: `E:\femboibot\docs\FEATURES.md`
- Modify: `E:\femboibot\docs\plans\2026-04-14-gemini-grounding-verification.md`

**Step 1: Write the failing doc check**

Define the exact operator workflow:
- how to capture a new fixture
- when to run the live verification test
- what to inspect if Gemini starts returning empty or malformed search results

**Step 2: Run doc review**

Run: `Get-Content docs\\FEATURES.md`
Expected: contains a short maintenance note for Gemini-backed web search verification.

**Step 3: Write minimal documentation**

Add a concise maintenance section covering:
- fixture refresh cadence
- live-test opt-in env vars
- parser fallback expectations

**Step 4: Re-run focused verification**

Run: `pytest tests/test_web_search.py tests/test_gemini_grounding_live.py -v`
Expected: PASS or intentional SKIP for the live test.

**Step 5: Commit**

```bash
git add docs/FEATURES.md docs/plans/2026-04-14-gemini-grounding-verification.md tests/test_web_search.py tests/test_gemini_grounding_live.py
git commit -m "docs: add gemini grounding verification workflow"
```
