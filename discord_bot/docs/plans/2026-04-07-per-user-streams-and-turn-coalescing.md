# Per-User Streams And Turn Coalescing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let different users receive concurrent AI replies in the same channel while making one user's split or rapidly corrected messages behave like a single coherent turn.

**Architecture:** Replace the current channel-wide stream lock with a per-`(channel_id, user_id)` claim and introduce a versioned same-user turn coordinator in `AIBrain`. The coordinator owns four states for a user turn in a channel: pending debounce, active pre-visible stream, active visible stream, and buffered follow-up. Same-user fragments extend or merge the current turn; if they arrive before any visible output, the active generation is cancelled and restarted with the merged content, and if they arrive after visible output has begun, they collapse into exactly one follow-up turn that runs after the visible stream completes.

**Tech Stack:** Python, discord.py, asyncio, unittest, existing streaming helpers in `discord_bot/utils/streaming/`

---

## Runtime Invariants

- At most one visible stream per `(channel_id, user_id)` at a time.
- Different users may stream concurrently in the same channel.
- Same-user fragments are never dropped or duplicated.
- Stale debounce tasks and stale stream completions must not send replies.
- Passive no-mention auto-channel heuristics remain unchanged in this rollout.
- Persona fan-out queueing remains channel-scoped unless explicitly touched by a later task.

## UX Contract

- `@bot I WANT TO`
- `COOK`
- `BEEF TODAY`
- `CAN YOU HELP ME`

When those messages come from the same user within the debounce window, the bot should treat them as one turn and produce one reply.

- If the user keeps typing before the bot has shown any visible output, restart the active generation with the merged content.
- If the bot has already shown visible output, do not overlap same-user replies; buffer one merged follow-up turn instead.
- Do not send the old channel-wide busy message when another user triggers the bot in the same channel.

## Non-Goals

- No change to passive no-mention reply scoring.
- No new slash-command surface in this rollout.
- No provider-specific speculative streaming tricks.
- No attempt to make multi-persona fan-out concurrent inside one channel; that remains serialized.

---

### Task 1: Lock the per-user stream ownership contract with tests

**Files:**
- Create: `discord_bot/tests/test_stream_session_registry.py`
- Modify: `discord_bot/utils/streaming/session_registry.py`
- Test: `discord_bot/tests/test_stream_session_registry.py`

**Step 1: Write the failing test**

Create focused async tests that prove:
- two different users can acquire stream claims in the same channel at the same time
- the same user cannot acquire two claims in the same channel
- the same user can hold independent claims in different channels
- releasing one user's claim does not clear another user's claim
- the context manager releases the claim even if the wrapped block raises

Use small tests like:

```python
async def test_claim_releases_after_exception(self) -> None:
    registry = ChannelStreamRegistry()
    with self.assertRaises(RuntimeError):
        async with registry.claim(channel_id=10, user_id=100):
            raise RuntimeError("boom")
    self.assertFalse(registry.is_active(channel_id=10, user_id=100))
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest discord_bot.tests.test_stream_session_registry -v`
Expected: FAIL because the registry is still keyed only by `channel_id`.

**Step 3: Write minimal implementation**

Update `ChannelStreamRegistry` so it:
- keys active claims by `(channel_id, user_id)`
- exposes `acquire`, `release`, `is_active`, and `claim` with both `channel_id` and `user_id`
- preserves lock safety with a single internal asyncio lock
- raises `ChannelStreamBusyError` only for duplicate claims by the same user in the same channel

Do not touch `AIBrain` yet.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest discord_bot.tests.test_stream_session_registry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_bot/tests/test_stream_session_registry.py discord_bot/utils/streaming/session_registry.py
git commit -m "test: define per-user stream session ownership"
```

### Task 2: Build a versioned turn coordinator helper instead of ad-hoc timers

**Files:**
- Create: `discord_bot/utils/turn_coalescer.py`
- Create: `discord_bot/tests/test_turn_coalescer.py`
- Test: `discord_bot/tests/test_turn_coalescer.py`

**Step 1: Write the failing test**

Create fast, pure-state tests that prove:
- a first same-user fragment creates a pending turn with version `1`
- a second fragment increments the version and extends the debounce deadline
- fragments preserve order and merge with newline delimiters
- attachments and reply targets are merged onto the newest source message
- a stale flush for version `1` is ignored after version `2` exists
- a same-user pre-visible restart request marks the active generation stale rather than creating a second visible turn
- visible-stream follow-up buffering collapses repeated fragments into one buffered follow-up bundle
- different users in the same channel never share state

Use simple dataclasses such as:

```python
@dataclass(slots=True)
class TurnKey:
    channel_id: int
    user_id: int
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest discord_bot.tests.test_turn_coalescer -v`
Expected: FAIL because the helper module does not exist yet.

**Step 3: Write minimal implementation**

Create `discord_bot/utils/turn_coalescer.py` with:
- `TurnKey`
- `PendingTurn`
- `ActiveTurn`
- `BufferedFollowUp`
- a `TurnCoordinator` class that owns only state and version checks, not Discord I/O

Required helper behavior:
- `upsert_pending(...)`
- `mark_active(...)`
- `has_visible_output(...)`
- `mark_visible(...)`
- `request_restart_before_visible(...)`
- `buffer_follow_up(...)`
- `pop_ready_pending(...)`
- `pop_buffered_follow_up(...)`
- `clear_finished(...)`

Policy defaults in the helper:
- debounce window: `2.0` seconds
- merge delimiter: newline
- exactly one buffered follow-up slot per `(channel_id, user_id)`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest discord_bot.tests.test_turn_coalescer -v`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_bot/utils/turn_coalescer.py discord_bot/tests/test_turn_coalescer.py
git commit -m "feat: add versioned same-user turn coordinator"
```

### Task 3: Route explicit same-user messages through debounce merging before prompt construction

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Modify: `discord_bot/tests/test_ai_reply_policy.py`
- Test: `discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing test**

Extend `OnMessagePolicyTests` with async tests that prove:
- same-user explicit-trigger fragments within the debounce window call `_execute_persona_invocation` only once
- the merged invocation receives newline-joined `content_for_prompt`
- the newest fragment message is used as the reply anchor
- merged attachments from multiple fragments are preserved in order
- different users in the same channel maintain independent pending turns

Patch timer sleeps so the tests do not wait in real time.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: FAIL because `on_message` still invokes immediately for each message.

**Step 3: Write minimal implementation**

Refactor `AIBrain` so explicit triggers and active-conversation continuations go through a pending-turn path:
- add coordinator state in `__init__`
- add helper methods such as `_queue_same_user_turn`, `_schedule_pending_flush`, `_flush_pending_turn`, and `_build_merged_turn_payload`
- insert merged context once at flush time, not per fragment
- keep passive no-mention auto-channel flow on the current immediate path

Implementation constraints:
- do not break rate limiting; the limiter should still apply once per flushed turn
- do not break reply context; the newest source message should drive the final reply and reply-context lookup
- do not change persona selection semantics for the flushed turn

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: debounce and merge same-user explicit turns"
```

### Task 4: Support pre-visible restart for the same user instead of forcing a stale first turn

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Modify: `discord_bot/utils/streaming/discord_sender.py`
- Modify: `discord_bot/tests/test_ai_reply_policy.py`
- Test: `discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing test**

Add async tests that prove:
- if a same-user fragment arrives after stream claim but before visible output, the first generation is cancelled
- the restarted generation runs once with merged content
- the cancelled generation does not send a stale reply later
- cross-user concurrency still works while same-user restart happens

Patch the stream path so the test can simulate “claimed but not yet visible” deterministically.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: FAIL because same-user active streams have no restart semantics yet.

**Step 3: Write minimal implementation**

Update the active-turn path so it tracks:
- the active version for `(channel_id, user_id)`
- the asyncio task for the current generation
- whether any visible output has been emitted yet

Implementation detail:
- use `DiscordReplySession.has_visible_output` to decide between restart and follow-up buffering
- if no visible output exists, cancel the current generation, mark its version stale, and immediately schedule a restarted generation with merged content
- make the cancelled generation exit quietly without sending interruption text

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py discord_bot/utils/streaming/discord_sender.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: restart same-user streams before visible output"
```

### Task 5: Buffer one same-user follow-up once visible output has begun

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Modify: `discord_bot/tests/test_ai_reply_policy.py`
- Test: `discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing test**

Add async tests that prove:
- if visible output has started, a same-user fragment does not create a second overlapping stream
- repeated same-user fragments during the active visible stream collapse into one buffered follow-up
- once the visible stream completes, the buffered follow-up flushes exactly once
- the old channel-wide busy reply is not sent when another user triggers the bot in the same channel

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: FAIL because visible-stream follow-up buffering is not implemented.

**Step 3: Write minimal implementation**

Update the same-user active-stream behavior:
- if the active sender has visible output, buffer one follow-up turn instead of restarting
- if more fragments arrive before the follow-up flushes, merge them into that one buffered follow-up
- after the active generation completes successfully or fails, schedule the follow-up if buffered content exists
- keep follow-up scheduling versioned so a stale completion cannot run an old follow-up

Do not bring back the old generic busy message for cross-user traffic.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: buffer one same-user follow-up after visible output"
```

### Task 6: Harden lifecycle cleanup, exception safety, and observability

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Modify: `discord_bot/tests/test_ai_reply_policy.py`
- Modify: `discord_bot/docs/features.md`
- Modify: `discord_bot/docs/guide/settings-reference.md`
- Test: `discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing test**

Add tests that prove:
- pending debounce tasks are cleaned up when their turn finishes
- a cancelled or failing generation releases its stream claim
- stale generations cannot send a second reply after a restart
- `cog_unload` or equivalent cleanup cancels outstanding debounce tasks safely

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: FAIL because cleanup and stale-generation guards are not fully implemented.

**Step 3: Write minimal implementation**

Add hardening to `AIBrain`:
- centralize task cancellation and cleanup in helper methods
- guard reply send paths with active-version checks
- add debug logs for merge, restart, follow-up buffer, stale-flush skip, and cleanup events
- if there is no `cog_unload` cleanup path today, add one that cancels outstanding debounce tasks

Document the final behavior in:
- `discord_bot/docs/features.md`
- `discord_bot/docs/guide/settings-reference.md`

Docs must mention:
- concurrent streaming is per `(channel, user)`
- same-user pre-visible fragments trigger restart behavior
- same-user post-visible fragments become one buffered follow-up
- passive no-mention flow is intentionally unchanged

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest discord_bot.tests.test_ai_reply_policy.OnMessagePolicyTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py discord_bot/tests/test_ai_reply_policy.py discord_bot/docs/features.md discord_bot/docs/guide/settings-reference.md
git commit -m "chore: harden turn coordination lifecycle and docs"
```

### Task 7: Final verification

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Modify: `discord_bot/utils/turn_coalescer.py`
- Modify: `discord_bot/utils/streaming/session_registry.py`
- Modify: `discord_bot/utils/streaming/discord_sender.py`
- Modify: `discord_bot/tests/test_ai_reply_policy.py`
- Modify: `discord_bot/tests/test_stream_session_registry.py`
- Modify: `discord_bot/tests/test_turn_coalescer.py`
- Modify: `discord_bot/docs/features.md`
- Modify: `discord_bot/docs/guide/settings-reference.md`

**Step 1: Run focused tests**

Run:
- `python3 -m unittest discord_bot.tests.test_stream_session_registry -v`
- `python3 -m unittest discord_bot.tests.test_turn_coalescer -v`
- `python3 -m unittest discord_bot.tests.test_ai_reply_policy -v`

Expected: PASS

**Step 2: Run syntax verification**

Run:
- `python3 -m py_compile discord_bot/cogs/ai_brain.py`
- `python3 -m py_compile discord_bot/utils/turn_coalescer.py`
- `python3 -m py_compile discord_bot/utils/streaming/session_registry.py`
- `python3 -m py_compile discord_bot/utils/streaming/discord_sender.py`

Expected: PASS

**Step 3: Run targeted manual verification in Discord**

Verify:
- user A and user B can both trigger concurrent replies in the same channel
- one user sending `I WANT TO`, `COOK`, `BEEF TODAY`, `CAN YOU HELP ME` within the debounce window gets one merged reply
- one user sending more text before the bot shows visible output causes restart, not two replies
- one user sending more text after visible output starts gets one follow-up reply after the first finishes
- no old channel-wide busy message appears for cross-user traffic

**Step 4: Summarize residual risk**

Document:
- provider cancellation timing may still vary slightly by backend even though stale-generation guards prevent duplicate visible replies
- multi-persona fan-out remains separately serialized per channel and is intentionally outside this rollout
