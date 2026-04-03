# Reply Sequence Hard Removal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the legacy Discord reply-sequence system entirely so the persona-queue runtime is the only orchestration model left in production code, config, and tests.

**Architecture:** Delete the old reply-sequence runtime and prompt-shaping code from `discord_bot/cogs/ai_brain.py`, remove `reply_sequence_*` guild-config fields and native config-panel controls, and replace preservation tests with regressions that assert the persona-queue runtime is the only supported continuation model. Keep the shared streaming sender stack, webhook persona identity flow, and the current non-stream processing-ack recovery path.

**Tech Stack:** Python, discord.py, aiosqlite, pytest, unittest

---

## Context The Implementer Needs

- The active runtime is already persona-job based in `E:\femboibot\discord_bot\cogs\ai_brain.py`.
- The remaining reply-sequence surface is legacy scaffolding:
  - runtime types/helpers in `E:\femboibot\discord_bot\cogs\ai_brain.py`
  - config schema/default keys in `E:\femboibot\discord_bot\utils\db_handler.py`
  - native config-panel controls in `E:\femboibot\discord_bot\utils\native_config_panel.py`
  - preservation tests in `E:\femboibot\tests\test_ai_brain_reply_sequence.py`
- Historical design docs may continue to mention reply-sequence behavior. Do not spend time deleting historical plan documents unless the user explicitly asks for doc archival cleanup.

## Definition Of Done

- `discord_bot/cogs/ai_brain.py` contains no reply-sequence runtime, prompt argument, or parsing/sending helpers.
- `discord_bot/utils/db_handler.py` contains no `reply_sequence_*` config columns, defaults, or exported key lists.
- `discord_bot/utils/native_config_panel.py` contains no reply-sequence UI or handlers.
- `tests/test_ai_brain_reply_sequence.py` is removed or converted so it no longer preserves the deleted model.
- Focused and final verification suites pass.

### Task 1: Replace Preservation Tests With Removal Tests

**Files:**
- Delete or modify: `E:\femboibot\tests\test_ai_brain_reply_sequence.py`
- Modify: `E:\femboibot\tests\test_ai_brain_multi_response.py`
- Modify: `E:\femboibot\tests\test_ai_config_surface.py`

**Step 1: Write the failing tests**

Add removal-focused regressions:
- `AIBrain` no longer exposes `reply_sequence_sessions`
- `build_prompt()` no longer accepts a `reply_sequence_session` argument
- prompts never mention fenced ````reply_sequence```` control blocks
- AI config surfaces and command groups expose no reply-sequence settings

Example test sketch:

```python
def test_ai_brain_no_longer_tracks_reply_sequence_sessions():
    brain = ai_brain_mod.AIBrain(_FakeBot())
    assert not hasattr(brain, "reply_sequence_sessions")
```

```python
def test_build_prompt_signature_has_no_reply_sequence_argument():
    params = inspect.signature(AIBrain.build_prompt).parameters
    assert "reply_sequence_session" not in params
```

**Step 2: Run the tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- failures showing the legacy reply-sequence API still exists

**Step 3: Remove or rewrite the obsolete preservation tests**

- Delete `test_ai_brain_reply_sequence.py` entirely if nothing in it still matters after hard removal.
- Move any still-relevant non-reply-sequence assertions into `test_ai_brain_multi_response.py`.
- Keep tests tightly scoped to the new architecture rather than old internals.

**Step 4: Run the tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_config_surface.py
git rm E:\femboibot\tests\test_ai_brain_reply_sequence.py
git commit -m "test: replace reply sequence preservation tests"
```

### Task 2: Remove Reply-Sequence Runtime From `ai_brain.py`

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Modify: `E:\femboibot\tests\test_ai_brain_multi_response.py`

**Step 1: Write the failing tests**

Add tests that prove the runtime no longer contains the old model:
- no reply-sequence dataclasses or state map
- no prompt branch adding reply-sequence instructions
- no message-interruption cleanup for reply-sequence sessions

Example test sketch:

```python
def test_build_prompt_does_not_emit_reply_sequence_instructions():
    prompt = asyncio.run(
        brain.build_prompt(
            guild_id=123,
            user_id=456,
            message="hello",
            context="ctx",
            member=fake_member,
        )
    )
    assert "reply_sequence" not in prompt
```

**Step 2: Run the tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py -q
```

Expected:
- failures because `ai_brain.py` still defines reply-sequence runtime and prompt text

**Step 3: Write the minimal implementation**

In `ai_brain.py`:
- delete `ReplySequenceControl` and `ReplySequenceSession`
- delete `REPLY_SEQUENCE_PATTERN` and `REPLY_SEQUENCE_ALLOWED_PAYLOADS`
- delete all `_reply_sequence_*` helpers and `_cancel_interrupted_reply_sequences`
- remove `reply_sequence_sessions` initialization and channel cleanup
- remove `reply_sequence_session` from `build_prompt()`
- remove reply-sequence prompt sections and instructions
- remove any dead sticker/GIF helpers that are only reachable from the deleted runtime

Do not change:
- persona job building
- queue scheduling
- shared streaming sender integration
- processing-ack recovery unless a test proves it depends on deleted code

**Step 4: Run the tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_brain_persona_queue.py E:\femboibot\tests\test_stream_discord_sender.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_brain_persona_queue.py E:\femboibot\tests\test_stream_discord_sender.py
git commit -m "refactor: remove legacy reply sequence runtime"
```

### Task 3: Hard-Remove Reply-Sequence Config Storage

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\db_handler.py`
- Modify: `E:\femboibot\tests\test_persona_db.py`
- Modify: `E:\femboibot\tests\test_mode_registry.py`
- Modify: `E:\femboibot\tests\test_ai_config_surface.py`

**Step 1: Write the failing tests**

Add tests for:
- `get_guild_config()` no longer returns `reply_sequence_*` keys
- fresh guild initialization does not create reply-sequence fields
- exported/default key lists do not mention reply sequence

Example test sketch:

```python
async def test_guild_config_omits_removed_reply_sequence_fields():
    await init_guild_db(123)
    config = await get_guild_config(123)
    assert "reply_sequence_enabled" not in config
```

**Step 2: Run the tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- failures because the schema/default config still includes reply-sequence keys

**Step 3: Write the minimal implementation**

In `db_handler.py`:
- remove `reply_sequence_enabled`
- remove `reply_sequence_timeout_seconds`
- remove `reply_sequence_hard_max_stages`
- remove `reply_sequence_allow_gif`
- remove `reply_sequence_allow_sticker`
- remove `reply_sequence_allow_emoji_only`
- remove the same keys from schema migration/default-field lists/exported config key lists

If SQLite column-drop support is awkward in the current migration scheme, rebuild the `guild_config` table in migration code rather than silently leaving unused columns behind. Hard removal means the runtime config API must stop surfacing those fields.

**Step 4: Run the tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_mode_registry.py E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\db_handler.py E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_mode_registry.py E:\femboibot\tests\test_ai_config_surface.py
git commit -m "refactor: remove reply sequence config storage"
```

### Task 4: Remove Native Config-Panel Reply-Sequence UI

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\native_config_panel.py`
- Modify: `E:\femboibot\tests\test_config_panel.py`
- Modify: `E:\femboibot\tests\test_ai_config_surface.py`

**Step 1: Write the failing tests**

Add tests for:
- no reply-sequence labels/buttons in the native AI config panel
- AI settings summary shows persona runtime and streaming only
- no update handler accepts reply-sequence settings

Example test sketch:

```python
def test_native_config_panel_has_no_reply_sequence_controls():
    text = Path(NATIVE_PANEL_PATH).read_text(encoding="utf-8")
    assert "reply_sequence" not in text
```

Use behavior-level tests where feasible, but a narrow source-level assertion is acceptable here because the requirement is total removal.

**Step 2: Run the tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_config_panel.py E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- failures because reply-sequence UI and handlers still exist

**Step 3: Write the minimal implementation**

In `native_config_panel.py`:
- remove reply-sequence summary fields
- remove reply-sequence buttons and callbacks
- remove timeout/max-stage update handlers
- remove reply-sequence toggle mappings
- keep streaming and persona runtime controls intact

**Step 4: Run the tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_config_panel.py E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\native_config_panel.py E:\femboibot\tests\test_config_panel.py E:\femboibot\tests\test_ai_config_surface.py
git commit -m "refactor: remove reply sequence config panel controls"
```

### Task 5: Final Cleanup And Verification

**Files:**
- Modify: `E:\femboibot\docs\FEATURES.md`
- Modify: any touched tests needed for final consistency

**Step 1: Write any missing failing regressions**

Add regressions for:
- persona queue remains the only continuation/orchestration model exposed in docs and config summaries
- webhook persona identity still works
- stream channel locking still works
- multi-persona disabled still falls back to the primary persona

**Step 2: Run the focused suite to verify failures**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_brain_persona_queue.py E:\femboibot\tests\test_config_panel.py E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- any newly added regressions fail before final fixes

**Step 3: Write minimal fixes**

Patch only the failures discovered by the focused suite. Keep historical documents untouched unless a test explicitly covers user-facing docs like `FEATURES.md`.

**Step 4: Run the final verification suite**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_brain_persona_queue.py E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_persona_manage_config.py E:\femboibot\tests\test_mode_registry.py E:\femboibot\tests\test_config_panel.py E:\femboibot\tests\test_ai_config_surface.py E:\femboibot\tests\test_runtime_guard.py E:\femboibot\tests\test_stream_orchestrator.py E:\femboibot\tests\test_stream_discord_sender.py E:\femboibot\tests\test_stream_provider_adapters.py E:\femboibot\tests\test_webhook_identity.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\discord_bot\utils\db_handler.py E:\femboibot\discord_bot\utils\native_config_panel.py E:\femboibot\docs\FEATURES.md E:\femboibot\tests
git commit -m "refactor: hard remove legacy reply sequence system"
```

## Notes For Execution

- Preserve the current persona queue runtime in `E:\femboibot\discord_bot\utils\persona_queue.py`.
- Preserve the current streaming sender stack in `E:\femboibot\discord_bot\utils\streaming\discord_sender.py`.
- Preserve webhook persona identity support in `E:\femboibot\discord_bot\utils\webhook_identity.py`.
- The non-stream processing-ack recovery path in `ai_brain.py` is allowed to remain if it has no dependency on reply-sequence internals.
- Historical planning docs are evidence of past work, not active product surface. Do not delete them unless the user asks for historical doc cleanup.

## Execution Handoff

Plan complete and saved to `docs/plans/2026-04-03-reply-sequence-hard-removal.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
