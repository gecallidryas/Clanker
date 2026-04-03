# Tomori-Style Multi-Persona Webhook Port Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current reply-sequence runtime with Tomori-style behavior: one streamed persona/webhook response per invocation, optional queued extra personas, and no duplicate streaming/provider infrastructure.

**Architecture:** Keep the existing Python provider adapters and `utils.streaming` pipeline, then layer Tomori-style persona routing, webhook identity sending, and queued persona jobs on top. Remove or retire the current model-controlled reply-sequence runtime so there is only one conversation orchestration model in production.

**Tech Stack:** Python, discord.py, aiosqlite, existing `utils.streaming` modules, existing `guild_ai` provider adapters, pytest/unittest.

---

## Execution Correction

- The writable repo at `E:\femboibot` does not yet contain the previously verified Task 1 baseline from the execution worktree.
- Continue execution in `E:\femboibot` by applying the plan-scoped Task 1 persona-config/runtime helpers first where Task 4 depends on them, then resume the Task 4 persona-queue cutover and later tasks in order.

## Verified Reuse Targets

- Reuse `discord_bot/utils/streaming/orchestrator.py` for buffered flushes and interruption handling.
- Reuse `discord_bot/utils/streaming/discord_sender.py` for chunk budgeting and pacing, but extend it for webhook persona identity.
- Reuse `discord_bot/utils/streaming/session_registry.py` for per-channel stream exclusion.
- Reuse `discord_bot/utils/guild_ai.py` streaming and one-shot provider entry points.
- Reuse `discord_bot/cogs/persona.py` and `discord_bot/utils/db_handler.py` persona persistence for custom personas.

## Verified Replacement Targets

- Replace the current reply-sequence runtime in `discord_bot/cogs/ai_brain.py`.
- Do not add a second streaming stack.
- Do not port Tomori provider adapters or text chunkers into this repo.
- Do not keep two competing continuation systems active at once.

### Task 1: Add Guild Persona Runtime Config

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\db_handler.py`
- Modify: `E:\femboibot\tests\test_persona_db.py`
- Modify: `E:\femboibot\tests\test_mode_registry.py`

**Step 1: Write the failing tests**

Add tests for:
- a persisted active persona list
- a persisted triggered persona limit
- a persisted multi-persona toggle
- fallback behavior when the stored active list is empty or contains deleted custom personas

Example test sketch:

```python
async def test_active_persona_list_falls_back_to_primary_mode():
    await init_guild_db(123)
    await set_server_mode(123, "mode_femboy")
    modes = await get_active_persona_modes(123)
    assert modes == ["mode_femboy"]
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_mode_registry.py -q
```

Expected:
- failures for missing helpers and missing config fields

**Step 3: Write minimal implementation**

In `db_handler.py`:
- add `guild_config` fields:
  - `ai_multi_persona_enabled INTEGER DEFAULT 0`
  - `ai_triggered_persona_limit INTEGER DEFAULT 1`
  - `ai_active_personas TEXT`
  - `ai_persona_webhooks_enabled INTEGER DEFAULT 1`
- add helpers:
  - `get_active_persona_modes(guild_id: int) -> list[str]`
  - `set_active_persona_modes(guild_id: int, mode_keys: list[str]) -> None`
  - `sanitize_active_persona_modes(guild_id: int, mode_keys: list[str]) -> list[str]`
- keep `server_config.persona_mode` as the primary/default persona for compatibility

**Step 4: Run tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_mode_registry.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\db_handler.py E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_mode_registry.py
git commit -m "feat: add multi-persona runtime config"
```

### Task 2: Add Single-Instance Runtime Guard

**Files:**
- Create: `E:\femboibot\discord_bot\utils\runtime_guard.py`
- Modify: `E:\femboibot\discord_bot\main.py`
- Create: `E:\femboibot\tests\test_runtime_guard.py`

**Step 1: Write the failing tests**

Add tests for:
- successful lock acquisition on first boot
- failure on second acquisition for the same lock target
- cleanup on context exit

Example test sketch:

```python
def test_runtime_guard_prevents_second_instance(tmp_path):
    guard1 = RuntimeInstanceGuard(tmp_path / "bot.lock")
    guard2 = RuntimeInstanceGuard(tmp_path / "bot.lock")
    with guard1.claim():
        with pytest.raises(RuntimeError):
            with guard2.claim():
                pass
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_runtime_guard.py -q
```

Expected:
- missing module/class failures

**Step 3: Write minimal implementation**

Implement a small process guard:
- file lock or exclusive create-based lock
- clear error message that the bot is already running
- opt-out env var only if truly needed for development, defaulting to safe behavior

Wire it into `main.py` so startup exits before connecting to Discord when another local process is already active.

**Step 4: Run tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_runtime_guard.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\runtime_guard.py E:\femboibot\discord_bot\main.py E:\femboibot\tests\test_runtime_guard.py
git commit -m "fix: prevent duplicate local bot instances"
```

### Task 3: Add Webhook Persona Identity Sender

**Files:**
- Create: `E:\femboibot\discord_bot\utils\webhook_identity.py`
- Modify: `E:\femboibot\discord_bot\utils\streaming\discord_sender.py`
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Create: `E:\femboibot\tests\test_webhook_identity.py`
- Modify: `E:\femboibot\tests\test_stream_discord_sender.py`

**Step 1: Write the failing tests**

Add tests for:
- persona sends use webhook username/avatar identity
- first webhook chunk is sent as a new message rather than `reply`
- fallback to normal bot sends when webhook creation/use fails
- webhook identity cache reuse

Example test sketch:

```python
async def test_webhook_session_sends_all_chunks_via_webhook():
    session = DiscordReplySession(
        source_message=fake_source,
        send_policy=DiscordSendPolicy(),
        budget=StreamSendBudget(),
        webhook_context=fake_webhook_context,
    )
    await session.send_text("hello")
    assert fake_webhook.sent[0]["username"] == "Lilya"
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_stream_discord_sender.py E:\femboibot\tests\test_webhook_identity.py -q
```

Expected:
- failures for missing webhook support

**Step 3: Write minimal implementation**

Implement a webhook utility module that:
- gets or creates one reusable webhook per channel
- sends webhook messages with persona username/avatar
- supports threads where applicable
- degrades safely to direct bot messages

Extend `DiscordReplySession` so it can operate in:
- normal bot-reply mode
- persona-webhook mode

Do not create a second sender stack. Extend the existing one.

**Step 4: Run tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_stream_discord_sender.py E:\femboibot\tests\test_webhook_identity.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\webhook_identity.py E:\femboibot\discord_bot\utils\streaming\discord_sender.py E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\tests\test_stream_discord_sender.py E:\femboibot\tests\test_webhook_identity.py
git commit -m "feat: add webhook persona sender support"
```

### Task 4: Replace Reply-Sequence Runtime With Persona Queue Model

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Create: `E:\femboibot\discord_bot\utils\persona_queue.py`
- Modify: `E:\femboibot\tests\test_ai_brain_reply_sequence.py`
- Create: `E:\femboibot\tests\test_ai_brain_persona_queue.py`

**Step 1: Write the failing tests**

Add tests for:
- one active persona streams one invocation into multiple Discord messages
- multiple triggered active personas are queued as separate jobs
- queued personas run sequentially in the same channel
- later personas do not see earlier persona replies in their input context
- queued persona count is capped by config
- replies from non-active personas do not run unless multi-persona is enabled

Example test sketch:

```python
async def test_multi_persona_trigger_enqueues_followup_persona_jobs():
    jobs = brain._build_persona_jobs(
        active_mode_keys=["mode_femboy", "mode_oneesan"],
        triggered_mode_keys={"mode_femboy", "mode_oneesan"},
        triggered_persona_limit=2,
    )
    assert [job.mode_key for job in jobs] == ["mode_femboy", "mode_oneesan"]
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_reply_sequence.py E:\femboibot\tests\test_ai_brain_persona_queue.py -q
```

Expected:
- failures because the runtime is still using reply-sequence sessions

**Step 3: Write minimal implementation**

In `ai_brain.py`:
- remove the reply-sequence turn/session path from `on_message`
- keep `generate_response_stream` and `utils.streaming` orchestration
- add explicit persona-job building:
  - resolve active personas
  - intersect with triggered personas
  - order deterministically by trigger position
  - cap by `ai_triggered_persona_limit`
- run the first persona immediately
- enqueue additional personas into a per-channel queue
- keep isolated per-persona tool/function state

In `persona_queue.py`:
- add a small queue manager for pending persona jobs per channel
- process one persona job at a time after the current one finishes

Do not generate one shared response for all personas.
Do not keep the current `ReplySequenceSession` model active.

**Step 4: Run tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_reply_sequence.py E:\femboibot\tests\test_ai_brain_persona_queue.py E:\femboibot\tests\test_ai_brain_multi_response.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\discord_bot\utils\persona_queue.py E:\femboibot\tests\test_ai_brain_reply_sequence.py E:\femboibot\tests\test_ai_brain_persona_queue.py E:\femboibot\tests\test_ai_brain_multi_response.py
git commit -m "feat: port tomori-style persona queue runtime"
```

### Task 5: Add Persona Activation and Multi-Persona Admin Controls

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\config.py`
- Modify: `E:\femboibot\discord_bot\cogs\persona.py`
- Create: `E:\femboibot\tests\test_persona_manage_config.py`

**Step 1: Write the failing tests**

Add tests for:
- enabling/disabling multi-persona mode
- selecting active personas
- setting triggered persona limit
- disabling webhook persona sends
- preserving the existing single primary mode UX as a compatibility path

Example test sketch:

```python
async def test_set_active_personas_persists_json_list():
    await set_active_persona_modes(123, ["mode_femboy", "custom_123_lilya"])
    assert await get_active_persona_modes(123) == ["mode_femboy", "custom_123_lilya"]
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_persona_manage_config.py -q
```

Expected:
- missing command/helper failures

**Step 3: Write minimal implementation**

Add config controls for:
- `ai_multi_persona_enabled`
- `ai_triggered_persona_limit`
- `ai_persona_webhooks_enabled`
- active persona selection list

Keep existing `/mode` and single-persona switching semantics as the primary persona selector, but let admins opt into multiple active personas.

**Step 4: Run tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_persona_manage_config.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\config.py E:\femboibot\discord_bot\cogs\persona.py E:\femboibot\tests\test_persona_manage_config.py
git commit -m "feat: add multi-persona admin controls"
```

### Task 6: Remove Conflicting Reply-Sequence UX and Keep Streaming Config

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\config.py`
- Modify: `E:\femboibot\docs\FEATURES.md`
- Create: `E:\femboibot\tests\test_ai_config_surface.py`

**Step 1: Write the failing tests**

Add tests for:
- streaming config remains available
- old reply-sequence-specific toggles are no longer presented as the active continuation model
- AI settings summary shows multi-persona and webhook identity options instead

**Step 2: Run tests to verify they fail**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- failures on config surface expectations

**Step 3: Write minimal implementation**

Update config and docs so:
- streaming remains a transport/output feature
- multi-persona queueing is the continuation/orchestration feature
- reply-sequence payload controls are removed or marked deprecated in the admin UX

**Step 4: Run tests to verify they pass**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_config_surface.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\config.py E:\femboibot\docs\FEATURES.md E:\femboibot\tests\test_ai_config_surface.py
git commit -m "refactor: align ai config with persona queue model"
```

### Task 7: Full Verification Pass

**Files:**
- Modify: `E:\femboibot\tests\test_ai_brain_multi_response.py`
- Modify: `E:\femboibot\tests\test_ai_brain_reply_limits.py`
- Modify: `E:\femboibot\tests\test_stream_provider_adapters.py`

**Step 1: Write any missing failing regressions**

Add regressions for:
- custom endpoint capability handling still works
- channel stream lock still blocks overlapping streams
- duplicate local process guard does not affect tests
- bot still falls back to one persona when multi-persona is disabled

**Step 2: Run focused suite to verify failures**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_brain_reply_limits.py E:\femboibot\tests\test_stream_provider_adapters.py -q
```

Expected:
- any new regressions fail before implementation fixes

**Step 3: Write minimal fixes**

Patch only the regression points found by the focused suite.

**Step 4: Run the final verification suite**

Run:

```powershell
pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_ai_brain_reply_limits.py E:\femboibot\tests\test_ai_brain_reply_sequence.py E:\femboibot\tests\test_ai_brain_persona_queue.py E:\femboibot\tests\test_persona_db.py E:\femboibot\tests\test_persona_manage_config.py E:\femboibot\tests\test_runtime_guard.py E:\femboibot\tests\test_stream_orchestrator.py E:\femboibot\tests\test_stream_discord_sender.py E:\femboibot\tests\test_stream_provider_adapters.py E:\femboibot\tests\test_webhook_identity.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\tests
git commit -m "test: cover tomori-style multi-persona webhook port"
```

## Implementation Notes

- Preserve existing provider adapters and custom-endpoint capability parsing.
- Preserve the existing stream buffer/chunker/sender path unless a failing test proves it must change.
- When porting Tomori behavior, match semantics, not file layout.
- The persona queue must be channel-serialized to avoid overlapping sends.
- The process-duplication bug is a runtime guard problem, not an AI-brain logic problem.
- Prefer deprecating the old reply-sequence config path over silently leaving dead controls behind.

## Execution Handoff

Plan complete and saved to `docs/plans/2026-04-02-tomori-multipersona-webhook-port.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
