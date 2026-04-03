# Reply Streaming Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reusable streaming reply engine for mention/reply chat that preserves one-shot fallback behavior and can later be reused by slash-command AI paths.

**Architecture:** Build a provider-agnostic streaming layer under `discord_bot/utils/streaming/` with explicit request/event/result types, semantic buffering, Discord send policy, typing keepalive, thought logging, and channel session ownership. Wire provider capability resolution through `guild_ai.py` and `api_manager.py`, then refit `ai_brain.py` to run stream-first with one-shot fallback and existing tool loops preserved.

**Tech Stack:** Python, `discord.py`, `aiosqlite`, OpenAI async SDK, Google Gemini SDK, pytest, asyncio.

---

### Task 1: Streaming Core

**Files:**
- Create: `discord_bot/utils/streaming/types.py`
- Create: `discord_bot/utils/streaming/buffer.py`
- Create: `discord_bot/utils/streaming/chunker.py`
- Create: `discord_bot/utils/streaming/discord_sender.py`
- Create: `discord_bot/utils/streaming/typing_manager.py`
- Create: `discord_bot/utils/streaming/session_registry.py`
- Create: `discord_bot/utils/streaming/thought_logger.py`
- Create: `discord_bot/utils/streaming/orchestrator.py`
- Test: `tests/test_stream_buffer.py`
- Test: `tests/test_stream_chunker.py`
- Test: `tests/test_stream_discord_sender.py`
- Test: `tests/test_stream_orchestrator.py`
- Test: `tests/test_stream_thought_logging.py`

**Step 1: Write failing tests**

Cover:
- semantic flush boundaries,
- code-fence-safe chunking,
- first-reply/follow-up send policy,
- interruption hint rules,
- channel ownership collision behavior,
- thought-log routing and sanitization.

**Step 2: Run targeted tests to verify red**

Run: `pytest tests/test_stream_buffer.py tests/test_stream_chunker.py tests/test_stream_discord_sender.py tests/test_stream_orchestrator.py tests/test_stream_thought_logging.py -q`

Expected: failures for missing modules/classes and missing behavior.

**Step 3: Implement minimal streaming core**

Add normalized dataclasses, semantic buffering, chunking, sender budget enforcement, typing keepalive, thought logger, session registry, and orchestrator flow with partial/interruption handling.

**Step 4: Run targeted tests to verify green**

Run: `pytest tests/test_stream_buffer.py tests/test_stream_chunker.py tests/test_stream_discord_sender.py tests/test_stream_orchestrator.py tests/test_stream_thought_logging.py -q`

Expected: targeted tests pass.

### Task 2: Provider and Config Wiring

**Files:**
- Modify: `discord_bot/utils/api_manager.py`
- Modify: `discord_bot/utils/guild_ai.py`
- Modify: `discord_bot/utils/rate_limiter.py`
- Modify: `discord_bot/utils/logger.py`
- Modify: `discord_bot/utils/db_handler.py`
- Modify: `discord_bot/cogs/config.py`
- Test: `tests/test_stream_provider_adapters.py`

**Step 1: Write failing tests**

Cover:
- provider capability resolution,
- explicit OpenAI-compatible custom endpoint gating,
- pseudo/fallback streaming event conversion,
- stream send-budget helper behavior,
- thought/debug channel config persistence.

**Step 2: Run targeted tests to verify red**

Run: `pytest tests/test_stream_provider_adapters.py -q`

Expected: failures for missing adapters/config behavior.

**Step 3: Implement minimal provider/config changes**

Add provider adapter helpers, capability resolution, DB/config fields, mod-log reuse guardrails, and structured stream logging helpers.

**Step 4: Run targeted tests to verify green**

Run: `pytest tests/test_stream_provider_adapters.py -q`

Expected: provider/config tests pass.

### Task 3: Mention/Reply Integration

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Modify: `discord_bot/utils/text_splitter.py`
- Test: `tests/test_ai_brain_multi_response.py`

**Step 1: Write failing tests**

Cover:
- stream-first reply flow,
- fallback when no meaningful text was sent,
- partial interruption hint when text was already sent,
- tool loop continuity,
- one active stream per channel.

**Step 2: Run targeted tests to verify red**

Run: `pytest tests/test_ai_brain_multi_response.py -q`

Expected: failures for old non-streaming-only path.

**Step 3: Implement minimal integration**

Extract shared turn execution, invoke the orchestrator for mention/reply chat, preserve fallback path, and keep output cleaning/chunk safety consistent with existing one-shot behavior.

**Step 4: Run targeted tests to verify green**

Run: `pytest tests/test_ai_brain_multi_response.py -q`

Expected: AI brain streaming tests pass.

### Task 4: Verification and Docs

**Files:**
- Modify: `docs/2026-03-30-reply-streaming-overhaul-design.md` or adjacent docs only if implementation-specific config defaults changed

**Step 1: Run focused verification**

Run: `pytest tests/test_stream_buffer.py tests/test_stream_chunker.py tests/test_stream_discord_sender.py tests/test_stream_orchestrator.py tests/test_stream_provider_adapters.py tests/test_stream_thought_logging.py tests/test_ai_brain_multi_response.py tests/test_text_splitter.py -q`

Expected: all targeted streaming tests pass.

**Step 2: Run adjacent regression checks**

Run: `pytest tests/test_api_manager.py tests/test_tool_parser.py tests/test_message_cooldown.py -q`

Expected: pass.

**Step 3: Document remaining gaps**

Capture unimplemented provider-native details, slash-command adoption follow-up, or rollout toggles if not fully completed in-session.
