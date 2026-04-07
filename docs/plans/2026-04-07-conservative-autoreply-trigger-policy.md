# Conservative Auto-Reply Trigger Policy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Port Tomori-style trigger policy into `discord_bot` while upgrading no-mention auto-replies to a conservative, recent-context-aware decision pipeline that feels more human and less interruptive.

**Architecture:** Keep `discord_bot`'s existing config surface and move reply-policy logic into a dedicated helper module. Guaranteed triggers such as reply-to-bot, reply-to-bot-owned persona webhook, and persona trigger words remain deterministic. No-mention replies flow through a multi-stage conservative gate: hard blockers, shared auto-channel candidacy, heuristic scoring over the recent 5-6 message window, and a strict JSON LLM tiebreaker only for ambiguous cases.

**Tech Stack:** Python, discord.py, unittest, asyncio, existing provider/runtime helpers in `discord_bot`

---

## Context The Implementer Needs

- The current runtime entry point is `discord_bot/cogs/ai_brain.py`, especially:
  - `ConversationContext`
  - `_track_message_id`
  - `_resolve_reply_to`
  - `_is_reply_to_bot`
  - `_bot_reply_chain_depth`
  - `on_message`
  - `_execute_persona_invocation`
- The current config surface already exposes:
  - `ai_channel_whitelist`
  - `ai_reply_cooldown_seconds`
  - `ai_reply_cooldown_type`
  - `ai_self_reply_limit`
  - `ai_auto_channels`
  - `ai_auto_threshold`
- `ai_auto_channels` and `ai_auto_threshold` currently exist in config but are not fully wired into runtime reply behavior.
- `ConversationContext` currently stores messages but only exposes a flattened context string. The new no-mention judge needs a structured recent-message window.
- Outbound message tracking currently uses `_track_message_id(sent.id, sent.author.id)`. That is not enough for persona webhook parity because webhook-authored bot messages must still count as bot-owned reply targets.
- Existing cooldown helpers live in `discord_bot/utils/message_cooldown.py`.
- Existing personal privacy only covers memory opt-out. Tomori-style trigger privacy will need a separate per-user reply-visibility flag if full parity is desired.

## Definition Of Done

- Direct replies to bot-owned persona webhook messages are recognized as replies to the bot.
- Explicit trigger behavior in `discord_bot` matches Tomori's effective policy: direct reply, mention, persona trigger, and shared auto-channel candidate handling.
- Auto channels with threshold `> 0` produce shared counter-based candidacy.
- Auto channels with threshold `0` become always-eligible channels, but no-mention replies still require a conservative green light.
- Whitelist, cooldown, privacy, and self-reply limits block unsolicited replies consistently.
- The no-mention judge uses a recent 5-6 message window, not only the newest message.
- Focused tests cover helper logic and `AIBrain` integration.

### Task 1: Add Reply Policy Test Harness

**Files:**
- Create: `/mnt/e/femboibot/discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing tests**

Add focused unit tests for the future policy helpers:

```python
import unittest

from discord_bot.utils import ai_reply_policy


class ReplyPolicyHelperTests(unittest.TestCase):
    def test_threshold_zero_marks_auto_channel_as_always_eligible(self) -> None:
        decision = ai_reply_policy.evaluate_auto_channel_signal(
            channel_id=123,
            auto_channel_ids={123},
            auto_threshold=0,
            counter_value=0,
            next_target=0,
        )
        self.assertTrue(decision.always_eligible)
        self.assertFalse(decision.counter_hit)

    def test_counter_hit_requires_configured_auto_channel(self) -> None:
        decision = ai_reply_policy.evaluate_auto_channel_signal(
            channel_id=123,
            auto_channel_ids={456},
            auto_threshold=3,
            counter_value=3,
            next_target=3,
        )
        self.assertFalse(decision.counter_hit)
```

```python
    def test_recent_window_prefers_open_question(self) -> None:
        window = [
            {"username": "A", "content": "any idea why this broke?", "is_bot_owned": False},
            {"username": "B", "content": "not sure", "is_bot_owned": False},
        ]
        score = ai_reply_policy.score_no_mention_candidate(window)
        self.assertGreaterEqual(score.total, ai_reply_policy.AMBIGUOUS_MIN_SCORE)
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL because `discord_bot.utils.ai_reply_policy` does not exist yet

**Step 3: Write minimal helper scaffolding**

Create `discord_bot/utils/ai_reply_policy.py` with placeholder dataclasses/constants/functions that satisfy imports but not full behavior:

```python
from dataclasses import dataclass

AMBIGUOUS_MIN_SCORE = 3


@dataclass
class AutoChannelSignal:
    counter_hit: bool = False
    always_eligible: bool = False


def evaluate_auto_channel_signal(...):
    return AutoChannelSignal()


def score_no_mention_candidate(window):
    raise NotImplementedError
```

**Step 4: Run the tests to verify the expected failures changed**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL on behavior assertions instead of import errors

**Step 5: Commit**

```bash
git add discord_bot/tests/test_ai_reply_policy.py discord_bot/utils/ai_reply_policy.py
git commit -m "test: add ai reply policy harness"
```

### Task 2: Add Structured Context Window And Bot-Owned Outbound Passports

**Files:**
- Modify: `/mnt/e/femboibot/discord_bot/cogs/ai_brain.py`
- Modify: `/mnt/e/femboibot/discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing tests**

Add tests proving:
- `ConversationContext` can return the last `N` structured messages
- outbound bot-owned webhook messages are recognized as bot reply targets

```python
class ConversationContextTests(unittest.TestCase):
    def test_get_recent_messages_returns_newest_window(self) -> None:
        context = ai_brain.ConversationContext(max_size=10, expiry_minutes=30)
        for idx in range(6):
            context.add_message(idx + 1, idx + 10, f"user{idx}", f"msg {idx}")

        window = context.get_recent_messages(limit=4)

        self.assertEqual([item["content"] for item in window], ["msg 2", "msg 3", "msg 4", "msg 5"])
```

```python
class OutboundPassportTests(unittest.IsolatedAsyncioTestCase):
    async def test_reply_to_bot_owned_webhook_counts_as_reply_to_bot(self) -> None:
        brain = ai_brain.AIBrain(_FakeBot())
        brain._track_outbound_bot_message(message_id=555, owner_kind="persona_webhook", persona_mode="mode_femboy")
        fake = _build_fake_reply_message(reply_to_message_id=555)
        self.assertTrue(brain._is_reply_to_bot(fake))
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL because `ConversationContext.get_recent_messages()` and outbound-passport tracking do not exist yet

**Step 3: Write minimal implementation**

In `discord_bot/cogs/ai_brain.py`:
- add `ConversationContext.get_recent_messages(limit: int, min_message_id: Optional[int] = None) -> list[dict[str, Any]]`
- add an outbound passport map on `AIBrain`, for example `self.bot_owned_messages`
- add `_track_outbound_bot_message(...)`
- update `_is_reply_to_bot()` to consult the passport map before falling back to raw author id
- update `_execute_persona_invocation()` to mark both direct bot messages and persona-webhook messages as bot-owned

**Step 4: Run the tests to verify they pass**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- PASS for the new context-window and outbound-passport tests

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: add structured context windows and outbound bot passports"
```

### Task 3: Implement Deterministic Tomori-Style Trigger Signals

**Files:**
- Modify: `/mnt/e/femboibot/discord_bot/utils/ai_reply_policy.py`
- Modify: `/mnt/e/femboibot/discord_bot/cogs/ai_brain.py`
- Modify: `/mnt/e/femboibot/discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing tests**

Add tests for:
- mention/reply/trigger extraction
- foreign webhook rejection
- self-reply chain limit
- shared auto-channel counter candidacy

```python
    def test_foreign_webhook_is_not_treated_as_bot_owned(self) -> None:
        self.assertFalse(ai_reply_policy.is_bot_owned_webhook(message_id=999, passport_store={}))

    def test_self_reply_limit_blocks_after_threshold(self) -> None:
        state = ai_reply_policy.SelfReplyChainState(depth=3, last_was_self=True)
        self.assertTrue(ai_reply_policy.self_reply_limit_reached(state, limit=3))
```

```python
class DeterministicTriggerTests(unittest.IsolatedAsyncioTestCase):
    async def test_auto_counter_hit_creates_candidate_signal(self) -> None:
        signal = ai_reply_policy.evaluate_auto_channel_signal(
            channel_id=77,
            auto_channel_ids={77},
            auto_threshold=4,
            counter_value=4,
            next_target=4,
        )
        self.assertTrue(signal.counter_hit)
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL because deterministic trigger helpers are incomplete

**Step 3: Write minimal implementation**

In `discord_bot/utils/ai_reply_policy.py`:
- add `SelfReplyChainState`
- add helper functions for auto-channel candidacy and self-reply guard checks
- add a small container such as `ReplyTriggerSignals` that carries:
  - `mentioned`
  - `replied_to_bot`
  - `has_selected_trigger`
  - `auto_counter_hit`
  - `auto_always_eligible`
  - `is_foreign_webhook`

In `discord_bot/cogs/ai_brain.py`:
- replace the ad hoc `should_respond` boolean construction with a call that gathers `ReplyTriggerSignals`
- use existing `ai_channel_whitelist`, cooldown values, and `ai_self_reply_limit` as deterministic blockers

**Step 4: Run the tests to verify they pass**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- PASS for deterministic trigger tests

**Step 5: Commit**

```bash
git add discord_bot/utils/ai_reply_policy.py discord_bot/cogs/ai_brain.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: add deterministic trigger policy helpers"
```

### Task 4: Add Conservative No-Mention Heuristic Scoring

**Files:**
- Modify: `/mnt/e/femboibot/discord_bot/utils/ai_reply_policy.py`
- Modify: `/mnt/e/femboibot/discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing tests**

Add tests that prove:
- open questions and explicit invitations raise the score
- recent bot saturation lowers the score
- closed acknowledgments reject the candidate

```python
    def test_closed_acknowledgment_stays_quiet(self) -> None:
        window = [
            {"username": "A", "content": "thanks", "is_bot_owned": False},
            {"username": "B", "content": "np", "is_bot_owned": False},
        ]
        score = ai_reply_policy.score_no_mention_candidate(window)
        self.assertTrue(score.reject_immediately)
```

```python
    def test_recent_bot_saturation_penalizes_candidate(self) -> None:
        window = [
            {"username": "Bot", "content": "hello", "is_bot_owned": True},
            {"username": "Bot", "content": "anything else?", "is_bot_owned": True},
            {"username": "User", "content": "ok", "is_bot_owned": False},
        ]
        score = ai_reply_policy.score_no_mention_candidate(window)
        self.assertLess(score.total, ai_reply_policy.AMBIGUOUS_MIN_SCORE)
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL because scoring is not implemented yet

**Step 3: Write minimal implementation**

Implement scoring in `discord_bot/utils/ai_reply_policy.py` with explicit weights for:
- unanswered open question
- invitation phrases such as "what do you think"
- persona references
- short lull / several human messages in a row
- penalties for recent bot-owned messages
- penalties for obvious closure markers like `ok`, `thanks`, `nvm`, `solved`

Design the scorer to return:
- `total`
- `reasons`
- `reject_immediately`
- `needs_llm_tiebreak`

**Step 4: Run the tests to verify they pass**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- PASS for heuristic scoring tests

**Step 5: Commit**

```bash
git add discord_bot/utils/ai_reply_policy.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: add conservative no-mention heuristic scoring"
```

### Task 5: Add Ambiguous-Case LLM Judge Using The Recent Window

**Files:**
- Modify: `/mnt/e/femboibot/discord_bot/utils/ai_reply_policy.py`
- Modify: `/mnt/e/femboibot/discord_bot/cogs/ai_brain.py`
- Modify: `/mnt/e/femboibot/discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing tests**

Add tests that prove:
- the judge prompt includes the last 5-6 structured messages
- parse failure defaults to no reply
- low-confidence responses default to no reply

```python
    async def test_llm_judge_uses_recent_window_not_only_latest_message(self) -> None:
        window = [
            {"username": "A", "content": "we need a second opinion", "is_bot_owned": False},
            {"username": "B", "content": "maybe ask femmy", "is_bot_owned": False},
        ]
        prompt = ai_reply_policy.build_no_mention_judge_prompt(window, channel_name="general")
        self.assertIn("we need a second opinion", prompt)
        self.assertIn("maybe ask femmy", prompt)
```

```python
    def test_parse_failure_defaults_to_quiet(self) -> None:
        verdict = ai_reply_policy.parse_no_mention_judge_response("not json")
        self.assertFalse(verdict.reply)
        self.assertEqual(verdict.reason, "parse_failure")
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL because judge prompt/parse helpers do not exist yet

**Step 3: Write minimal implementation**

In `discord_bot/utils/ai_reply_policy.py`:
- add strict JSON prompt builder and parser
- add confidence threshold constants
- make parse failure or malformed payload return `reply=False`

In `discord_bot/cogs/ai_brain.py`:
- add a dedicated helper such as `_judge_no_mention_candidate(...)`
- call it only when deterministic policy says the message is an auto-channel candidate and heuristic scoring returns `needs_llm_tiebreak=True`
- keep temperature low and require a strict JSON reply

**Step 4: Run the tests to verify they pass**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- PASS for prompt and parser tests

**Step 5: Commit**

```bash
git add discord_bot/utils/ai_reply_policy.py discord_bot/cogs/ai_brain.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: add conservative llm tiebreaker for auto replies"
```

### Task 6: Wire The Full Decision Pipeline Through `AIBrain.on_message`

**Files:**
- Modify: `/mnt/e/femboibot/discord_bot/cogs/ai_brain.py`
- Modify: `/mnt/e/femboibot/discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing integration-style tests**

Add async tests for the top-level behavior:
- direct reply to persona webhook => reply
- foreign webhook => no reply
- non-whitelisted channel => no reply
- cooldown active => no reply
- auto channel with threshold `0` and weak context => no reply
- auto channel with threshold `0` and strong invitation context => reply

```python
    async def test_auto_channel_threshold_zero_requires_positive_context(self) -> None:
        brain = _build_brain_with_policy()
        message = _build_fake_message(content="ok", channel_id=123)
        await brain.on_message(message)
        message.reply.assert_not_called()
```

```python
    async def test_reply_to_persona_webhook_is_treated_as_direct_trigger(self) -> None:
        brain = _build_brain_with_policy()
        brain._track_outbound_bot_message(message_id=900, owner_kind="persona_webhook", persona_mode="mode_femboy")
        message = _build_fake_reply_message(reply_to_message_id=900, content="what do you mean?")
        await brain.on_message(message)
        self.assertTrue(message.reply.called or brain._execute_persona_invocation.await_count == 1)
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL because `on_message()` is still using the old boolean gate

**Step 3: Write minimal implementation**

Refactor `discord_bot/cogs/ai_brain.py`:
- gather trigger signals early
- update auto-channel counters before candidate evaluation
- evaluate hard blockers consistently
- route explicit triggers directly
- route no-mention candidates through heuristic scoring and optional LLM judge
- clear/reset self-reply chain state when a real user message arrives
- increment self-reply chain depth when the bot sends a visible message

Keep the rest of generation behavior unchanged.

**Step 4: Run the tests to verify they pass**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- PASS for full top-level policy tests

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: wire conservative trigger policy into ai brain"
```

### Task 7: Add User Privacy Parity And Admin/Docs Updates

**Files:**
- Modify: `/mnt/e/femboibot/discord_bot/utils/db_handler.py`
- Modify: `/mnt/e/femboibot/discord_bot/cogs/teach.py`
- Modify: `/mnt/e/femboibot/discord_bot/cogs/config.py`
- Modify: `/mnt/e/femboibot/discord_bot/utils/native_config_panel.py`
- Modify: `/mnt/e/femboibot/discord_bot/docs/slash-commands.md`
- Modify: `/mnt/e/femboibot/discord_bot/docs/guide/settings-reference.md`
- Modify: `/mnt/e/femboibot/discord_bot/tests/test_ai_reply_policy.py`

**Step 1: Write the failing tests**

Add tests for:
- per-user reply visibility opt-out blocks non-manual triggers
- config summary explains the smarter auto-channel behavior

```python
    async def test_user_reply_visibility_opt_out_blocks_passive_trigger(self) -> None:
        ...
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- FAIL because reply-visibility privacy does not exist yet

**Step 3: Write minimal implementation**

- Add a separate user-profile field for trigger visibility, not a silent behavior change to memory opt-out.
- Expose it through the existing personal/privacy area in the least disruptive way.
- Update config-panel summaries so admins understand:
  - auto channels are candidate zones
  - threshold `0` means always-eligible, not unconditional response
  - direct triggers remain deterministic

**Step 4: Run the tests to verify they pass**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- PASS for privacy and summary tests

**Step 5: Commit**

```bash
git add discord_bot/utils/db_handler.py discord_bot/cogs/teach.py discord_bot/cogs/config.py discord_bot/utils/native_config_panel.py discord_bot/docs/slash-commands.md discord_bot/docs/guide/settings-reference.md discord_bot/tests/test_ai_reply_policy.py
git commit -m "feat: add reply visibility privacy and policy docs"
```

### Task 8: Run Full Verification And Record Residual Risks

**Files:**
- Modify: `/mnt/e/femboibot/docs/implementations/2026-04-07-conservative-autoreply-trigger-policy.md`

**Step 1: Run focused tests**

Run:

```bash
python3 -m unittest discord_bot.tests.test_ai_reply_policy -v
```

Expected:
- PASS

**Step 2: Run adjacent regression tests**

Run:

```bash
python3 -m unittest \
  discord_bot.tests.test_ai_reply_policy \
  discord_bot.tests.test_persona_manage_create \
  discord_bot.tests.test_admin_surface_consolidation \
  discord_bot.tests.test_tools_admin_surface_consolidation -v
```

Expected:
- PASS without breaking existing config/admin surfaces

**Step 3: Write implementation notes**

Create `/mnt/e/femboibot/docs/implementations/2026-04-07-conservative-autoreply-trigger-policy.md` summarizing:
- what changed
- what remained intentionally conservative
- residual risks:
  - heuristic weights may need tuning
  - LLM tiebreaker latency
  - webhook identity edge cases across reloads

**Step 4: Commit**

```bash
git add docs/implementations/2026-04-07-conservative-autoreply-trigger-policy.md
git commit -m "docs: record conservative auto-reply trigger policy rollout"
```

Plan complete and saved to `docs/plans/2026-04-07-conservative-autoreply-trigger-policy.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
