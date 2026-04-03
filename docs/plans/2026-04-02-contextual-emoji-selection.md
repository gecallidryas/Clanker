# Contextual Emoji Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace rule-based emoji insertion with a single bot-controlled contextual emoji selector that appends one validated Discord emoji only when the reply tone supports it.

**Architecture:** The bot will stop instructing the model to emit custom emojis and will stop converting model shortcodes into Discord tags in the normal response path. Instead, `EmojiManager` will score validated emoji candidates against conversation tone signals derived from the user message and final reply, then optionally append one high-confidence emoji.

**Tech Stack:** Python, discord.py, pytest

---

### Task 1: Replace legacy emoji-manager tests with contextual scoring tests

**Files:**
- Modify: `tests/test_emoji_manager.py`

**Step 1: Write the failing tests**

Add tests for:

- neutral text returns no emoji
- celebratory context prefers celebratory emoji
- hostile/annoyed context prefers annoyed emoji over positive name-mention emoji
- known custom shortcodes are stripped from model output instead of converted

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_emoji_manager.py -q`
Expected: FAIL because the new contextual methods do not exist yet and legacy trigger behavior is still asserted.

**Step 3: Write minimal implementation**

Implement contextual candidate scoring and shortcode stripping in `discord_bot/utils/emoji_manager.py`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_emoji_manager.py -q`
Expected: PASS

### Task 2: Remove model-owned custom emoji generation from the AI reply pipeline

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`

**Step 1: Write the failing test**

Add or update a focused test covering the post-generation path so that:

- model output custom shortcodes are not turned into Discord emoji tags
- the bot may append one validated contextual emoji after cleanup

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_brain_multi_response.py -q`
Expected: FAIL because the current pipeline still injects prompt emoji instructions and converts shortcodes.

**Step 3: Write minimal implementation**

- remove custom emoji prompt sections/instructions from the reply prompt
- remove `apply_trigger_emojis`
- remove response-path `replace_shortcodes`
- call the new contextual selection method once after cleanup

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ai_brain_multi_response.py -q`
Expected: PASS

### Task 3: Align startup logging and compatibility helpers

**Files:**
- Modify: `discord_bot/main.py`
- Modify: `discord_bot/utils/emoji_manager.py`

**Step 1: Write the failing test**

If a targeted test is practical, add one for validated inventory counts or helper behavior. Otherwise rely on existing unit tests for manager compatibility.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_emoji_manager.py -q`
Expected: FAIL if helper compatibility behavior is incomplete.

**Step 3: Write minimal implementation**

- update startup log wording
- keep validation/cache methods intact for existing runtime behavior

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_emoji_manager.py -q`
Expected: PASS

### Task 4: Run focused regression verification

**Files:**
- Modify: `tests/test_emoji_manager.py`
- Modify: `tests/test_ai_brain_multi_response.py`

**Step 1: Run focused regression suite**

Run: `$env:PYTHONPATH='E:\\femboibot\\discord_bot'; python -m pytest tests/test_emoji_manager.py tests/test_ai_brain_multi_response.py tests/test_output_cleaner.py tests/test_app_emojis_replacement.py tests/test_emoji_shortcode_repair.py -q`

Expected: PASS

**Step 2: Run any necessary follow-up fix**

If failures expose compatibility issues, fix them with the minimal code change and rerun the same command.

**Step 3: Record final verification**

Keep the passing command output for final reporting.
