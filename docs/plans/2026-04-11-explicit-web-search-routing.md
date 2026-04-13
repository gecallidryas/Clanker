# Explicit Web Search Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make explicit web-search requests run deterministic search execution with Gemini-first provider priority and clickable markdown-linked results.

**Architecture:** Add a conservative explicit-search detector in `discord_bot/cogs/ai_brain.py`, centralize provider priority and result formatting in `discord_bot/utils/web_search.py`, and cover the behavior with test-first regression cases. The normal model path remains unchanged for non-explicit search requests.

**Tech Stack:** Python, Discord.py, aiohttp, existing guild config/database helpers, unittest/pytest-style async tests

---

### Task 1: Lock Down Search Result Formatting

**Files:**
- Modify: `E:\femboibot\tests\test_web_search.py`
- Modify: `E:\femboibot\discord_bot\utils\web_search.py`

**Step 1: Write the failing test**

Add a test asserting that formatted results are emitted as:

```python
formatted = web_search._format_results(
    [{"title": "Example", "url": "https://example.com", "snippet": "Snippet"}]
)
assert formatted == "[Example](https://example.com)\nSnippet"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_search.py -k format -v`
Expected: FAIL because the current formatter returns `1. Example - https://example.com (Snippet)`

**Step 3: Write minimal implementation**

Update `_format_results` in `discord_bot/utils/web_search.py` to:

- emit one markdown link per result
- place snippet text on the following line when present
- separate results with blank lines

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_search.py -k format -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_web_search.py discord_bot/utils/web_search.py
git commit -m "test: lock down linked web search formatting"
```

### Task 2: Lock Down Provider Priority

**Files:**
- Modify: `E:\femboibot\tests\test_web_search.py`
- Modify: `E:\femboibot\discord_bot\utils\web_search.py`
- Check: `E:\femboibot\discord_bot\utils\guild_ai.py`

**Step 1: Write the failing test**

Add tests asserting:

- Gemini-backed search is used when configured
- Brave is used when Gemini search is unavailable but a Brave key exists
- legacy fallback is used only when both higher-priority providers are unavailable

Use mocks around provider helper functions so each test checks `result.data["provider"]`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_search.py -k "provider or brave or duckduckgo" -v`
Expected: FAIL because current code only chooses Brave or DuckDuckGo

**Step 3: Write minimal implementation**

Add provider selection helpers in `discord_bot/utils/web_search.py`:

- Gemini capability probe
- Gemini-backed search executor
- deterministic provider ordering

Normalize returned rows into the existing `title` / `url` / `snippet` shape.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_search.py -k "provider or brave or duckduckgo" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_web_search.py discord_bot/utils/web_search.py
git commit -m "feat: prioritize gemini for explicit web search"
```

### Task 3: Route Explicit Search Requests Before Model Generation

**Files:**
- Modify: `E:\femboibot\tests\test_ai_brain_reply_sequence.py` or add a focused AI brain test file if a narrower surface exists
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Check: `E:\femboibot\discord_bot\utils\tool_context.py`
- Check: `E:\femboibot\discord_bot\utils\tool_registry.py`

**Step 1: Write the failing test**

Add a test for a message such as `search web femboibot` asserting that:

- the explicit search router runs
- `web_search` is executed directly
- the bot replies with the formatted linked result text
- normal model generation is not required for that turn

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_brain_reply_sequence.py -k search -v`
Expected: FAIL because current flow only reaches search through model tool calls

**Step 3: Write minimal implementation**

In `discord_bot/cogs/ai_brain.py`:

- add a conservative explicit search-intent detector
- add a helper that executes `web_search` directly using a `ToolContext`
- short-circuit the normal response path when explicit search is detected

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_brain_reply_sequence.py -k search -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ai_brain_reply_sequence.py discord_bot/cogs/ai_brain.py
git commit -m "feat: route explicit search commands without model tools"
```

### Task 4: Run Focused Regression Verification

**Files:**
- Check: `E:\femboibot\tests\test_web_search.py`
- Check: `E:\femboibot\tests\test_ai_brain_reply_sequence.py`

**Step 1: Run focused tests**

Run: `pytest tests/test_web_search.py tests/test_ai_brain_reply_sequence.py -v`
Expected: PASS

**Step 2: Run any directly related broader test slices if needed**

Run: `pytest tests/test_tool_registry.py tests/test_tool_executor.py -v`
Expected: PASS

**Step 3: Document residual risk**

If Gemini capability detection must rely on mocked provider helpers rather than a live Gemini web-search call, note that the coverage proves routing and formatting but not upstream provider behavior.

**Step 4: Commit**

```bash
git add docs/plans/2026-04-11-explicit-web-search-routing-design.md docs/plans/2026-04-11-explicit-web-search-routing.md
git commit -m "docs: add explicit web search routing design and plan"
```
