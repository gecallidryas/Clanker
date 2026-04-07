# Database Summarization Docs And Verification Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Document the stored-memory database summarization feature and verify whether it actually works in the current runtime.

**Architecture:** Keep the implementation unchanged unless verification exposes a clear defect that must be fixed, but add focused tests around `DatabaseSummarizer` and update docs to reflect the true dependency chain. The docs should distinguish conversation TLDR summarization from memory reconciliation and call out that the database reconciler currently depends on the process-level Gemini summarize key path.

**Tech Stack:** Python, unittest, markdown docs, Gemini manager wiring in `utils/api_manager.py`

---

### Task 1: Lock in current summarizer behavior with tests

**Files:**
- Create: `discord_bot/tests/test_database_summarizer.py`
- Test: `discord_bot/tests/test_database_summarizer.py`

**Step 1: Write the failing test**

Add tests that prove:
- `DatabaseSummarizer` returns parsed reconciled facts when given an injected summarizer
- `DatabaseSummarizer` disables itself cleanly when the summarize manager cannot be created

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest discord_bot.tests.test_database_summarizer -v`
Expected: FAIL because the new test file does not exist yet.

**Step 3: Write minimal implementation**

Create the test file with focused unit coverage only. Do not refactor production code unless a real failure requires it.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest discord_bot.tests.test_database_summarizer -v`
Expected: PASS

### Task 2: Document the feature and its prerequisites

**Files:**
- Modify: `discord_bot/docs/features.md`
- Modify: `discord_bot/docs/guide/settings-reference.md`

**Step 1: Add docs**

Document:
- what “database summarization” means in this repo
- which commands/cogs trigger it
- which provider/key path it uses
- that it currently depends on `GEMINI_SUMMARIZE_KEY` and `google-genai` at process level
- that this is distinct from guild-configured TLDR summarization

**Step 2: Verify doc accuracy against code**

Cross-check:
- `discord_bot/utils/database_summarizer.py`
- `discord_bot/utils/api_manager.py`
- `discord_bot/cogs/memories.py`
- `discord_bot/cogs/teach.py`

### Task 3: Verify whether it works in this runtime

**Files:**
- No code changes required

**Step 1: Run runtime checks**

Run:
- `printf 'GEMINI_SUMMARIZE_KEY=%s\n' "${GEMINI_SUMMARIZE_KEY:+set}${GEMINI_SUMMARIZE_KEY:-unset}"`
- a Python import check for `google.genai`
- a Python probe that instantiates `DatabaseSummarizer`

**Step 2: Report actual status**

State clearly whether the feature works in this environment right now, and why.

### Task 4: Final verification

**Files:**
- Modify: `discord_bot/tests/test_database_summarizer.py`
- Modify: `discord_bot/docs/features.md`
- Modify: `discord_bot/docs/guide/settings-reference.md`

**Step 1: Run focused verification**

Run: `python3 -m unittest discord_bot.tests.test_database_summarizer -v`
Expected: PASS

**Step 2: Run syntax-safe import verification**

Run: `python3 -m py_compile discord_bot/utils/database_summarizer.py`
Expected: PASS
