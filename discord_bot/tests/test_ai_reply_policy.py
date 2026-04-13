import asyncio
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from utils import ai_reply_policy
from cogs import ai_brain
from cogs import config as config_cog


class ReplyPolicyHelperTests(unittest.TestCase):
    def test_explicit_trigger_detection_combines_direct_signals(self) -> None:
        signals = ai_reply_policy.build_reply_trigger_signals(
            mentioned=False,
            replied_to_bot=True,
            has_selected_trigger=False,
            auto_channel_signal=ai_reply_policy.AutoChannelSignal(),
            is_foreign_webhook=False,
        )
        self.assertTrue(signals.explicit_trigger)
        self.assertTrue(signals.replied_to_bot)

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

    def test_positive_counter_hit_uses_threshold_when_next_target_is_zero(self) -> None:
        decision = ai_reply_policy.evaluate_auto_channel_signal(
            channel_id=123,
            auto_channel_ids={123},
            auto_threshold=3,
            counter_value=3,
            next_target=0,
        )
        self.assertTrue(decision.counter_hit)

    def test_foreign_webhook_is_not_treated_as_bot_owned(self) -> None:
        self.assertFalse(
            ai_reply_policy.is_bot_owned_webhook(
                message_id=999,
                passport_store={},
            )
        )

    def test_self_reply_limit_blocks_after_threshold(self) -> None:
        state = ai_reply_policy.SelfReplyChainState(depth=3, last_was_self=True)
        self.assertTrue(ai_reply_policy.self_reply_limit_reached(state, limit=3))

    def test_recent_window_prefers_open_question(self) -> None:
        window = [
            {"username": "A", "content": "any idea why this broke?", "is_bot_owned": False},
            {"username": "B", "content": "not sure", "is_bot_owned": False},
        ]
        score = ai_reply_policy.score_no_mention_candidate(window)
        self.assertGreaterEqual(score.total, ai_reply_policy.AMBIGUOUS_MIN_SCORE)
        self.assertTrue(score.needs_llm_tiebreak)

    def test_explicit_invitation_raises_score(self) -> None:
        window = [
            {"username": "A", "content": "what do you think about this fix?", "is_bot_owned": False},
            {"username": "B", "content": "i want a second opinion", "is_bot_owned": False},
        ]
        score = ai_reply_policy.score_no_mention_candidate(window)
        self.assertGreaterEqual(score.total, ai_reply_policy.AMBIGUOUS_MIN_SCORE)

    def test_closed_acknowledgment_stays_quiet(self) -> None:
        window = [
            {"username": "A", "content": "thanks", "is_bot_owned": False},
            {"username": "B", "content": "np", "is_bot_owned": False},
        ]
        score = ai_reply_policy.score_no_mention_candidate(window)
        self.assertTrue(score.reject_immediately)

    def test_recent_bot_saturation_penalizes_candidate(self) -> None:
        window = [
            {"username": "Bot", "content": "hello", "is_bot_owned": True},
            {"username": "Bot", "content": "anything else?", "is_bot_owned": True},
            {"username": "User", "content": "ok", "is_bot_owned": False},
        ]
        score = ai_reply_policy.score_no_mention_candidate(window)
        self.assertLess(score.total, ai_reply_policy.AMBIGUOUS_MIN_SCORE)

    def test_llm_judge_uses_recent_window_not_only_latest_message(self) -> None:
        window = [
            {"username": "A", "content": "we need a second opinion", "is_bot_owned": False},
            {"username": "B", "content": "maybe ask femmy", "is_bot_owned": False},
        ]

        prompt = ai_reply_policy.build_no_mention_judge_prompt(window, channel_name="general")

        self.assertIn("we need a second opinion", prompt)
        self.assertIn("maybe ask femmy", prompt)
        self.assertIn("general", prompt)

    def test_parse_failure_defaults_to_quiet(self) -> None:
        verdict = ai_reply_policy.parse_no_mention_judge_response("not json")

        self.assertFalse(verdict.reply)
        self.assertEqual(verdict.reason, "parse_failure")

    def test_low_confidence_judge_response_defaults_to_quiet(self) -> None:
        verdict = ai_reply_policy.parse_no_mention_judge_response(
            '{"reply": true, "confidence": 0.25, "reason": "maybe"}'
        )

        self.assertFalse(verdict.reply)
        self.assertEqual(verdict.reason, "low_confidence")


class ConversationContextTests(unittest.TestCase):
    def test_get_recent_messages_returns_newest_window(self) -> None:
        context = ai_brain.ConversationContext(max_size=10, expiry_minutes=30)
        for idx in range(6):
            context.add_message(idx + 1, idx + 10, f"user{idx}", f"msg {idx}")

        window = context.get_recent_messages(limit=4)

        self.assertEqual([item["content"] for item in window], ["msg 2", "msg 3", "msg 4", "msg 5"])


class OutboundPassportTests(unittest.TestCase):
    def _make_brain(self) -> ai_brain.AIBrain:
        fake_bot = SimpleNamespace(user=SimpleNamespace(id=999))
        with ExitStack() as stack:
            stack.enter_context(patch.object(ai_brain, "register_builtin_tools", return_value=None))
            stack.enter_context(patch.object(ai_brain, "get_expression_service", return_value=object()))
            return ai_brain.AIBrain(fake_bot)

    def test_reply_to_bot_owned_webhook_counts_as_reply_to_bot(self) -> None:
        brain = self._make_brain()
        brain._track_outbound_bot_message(
            message_id=555,
            owner_kind="persona_webhook",
            persona_mode="mode_femboy",
        )
        fake_message = SimpleNamespace(
            reference=SimpleNamespace(message_id=555, resolved=None),
            webhook_id=None,
        )

        self.assertTrue(brain._is_reply_to_bot(fake_message))

    def test_outbound_passports_are_pruned_with_chain_memory_evictions(self) -> None:
        brain = self._make_brain()
        brain.chain_limit = 1
        brain._track_outbound_bot_message(
            message_id=111,
            owner_kind="bot",
            persona_mode=None,
        )

        brain._track_message_id(111, brain.bot.user.id)
        brain._track_message_id(222, 123)

        self.assertNotIn(111, brain.bot_owned_messages)


class DeterministicTriggerTests(unittest.TestCase):
    def test_auto_counter_hit_creates_candidate_signal(self) -> None:
        signal = ai_reply_policy.evaluate_auto_channel_signal(
            channel_id=77,
            auto_channel_ids={77},
            auto_threshold=4,
            counter_value=4,
            next_target=4,
        )
        self.assertTrue(signal.counter_hit)


class OnMessagePolicyTests(unittest.IsolatedAsyncioTestCase):
    def _start_patch(self, target: str, **kwargs):
        patcher = patch(target, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def _make_brain(self) -> ai_brain.AIBrain:
        fake_bot = SimpleNamespace(
            user=SimpleNamespace(id=999, display_name="Femmy"),
            get_user=lambda _user_id: None,
        )
        with ExitStack() as stack:
            stack.enter_context(patch.object(ai_brain, "register_builtin_tools", return_value=None))
            stack.enter_context(patch.object(ai_brain, "get_expression_service", return_value=object()))
            brain = ai_brain.AIBrain(fake_bot)

        self._start_patch(
            "cogs.ai_brain.get_personal_memory_privacy",
            new=AsyncMock(
                return_value={
                    "personal_memory_opt_out": False,
                    "allow_mention_fact_lookup": False,
                    "personal_memory_export_enabled": True,
                    "passive_reply_visibility_opt_out": False,
                    "privacy_updated_at": None,
                }
            ),
        )
        brain._handle_pending_agentic_confirmation = AsyncMock(return_value=None)
        brain._handle_pending_admin_confirmation = AsyncMock(return_value=None)
        brain._get_triggered_modes_in_order = AsyncMock(return_value=[])
        brain._resolve_active_persona_modes = AsyncMock(return_value=["mode_femboy"])
        brain._maybe_handle_admin_nl_request = AsyncMock(return_value=False)
        brain._maybe_handle_starboard_setup_request = AsyncMock(return_value=False)
        brain._maybe_handle_channel_request = AsyncMock(return_value=False)
        brain._maybe_handle_role_request = AsyncMock(return_value=False)
        brain._get_reply_context = AsyncMock(return_value="")
        brain._execute_persona_invocation = AsyncMock(return_value=SimpleNamespace(id=4242))
        brain._judge_no_mention_candidate = AsyncMock(
            return_value=ai_reply_policy.NoMentionJudgeVerdict(reply=True, confidence=0.95, reason="invited")
        )
        brain._bot_reply_chain_depth = AsyncMock(return_value=0)
        return brain

    def _make_message(
        self,
        *,
        content: str,
        channel_id: int = 123,
        author_id: int = 111,
        message_id: int = 5000,
        webhook_id=None,
        reply_to_message_id=None,
    ) -> SimpleNamespace:
        channel = SimpleNamespace(
            id=channel_id,
            name="general",
            send=AsyncMock(),
            fetch_message=AsyncMock(),
        )
        guild = SimpleNamespace(
            id=321,
            owner_id=111,
            get_member=lambda _user_id: None,
        )
        author = SimpleNamespace(
            id=author_id,
            bot=False,
            display_name="User",
            guild_permissions=SimpleNamespace(administrator=False, manage_guild=False),
        )
        reference = None
        if reply_to_message_id is not None:
            reference = SimpleNamespace(message_id=reply_to_message_id, resolved=None)
        return SimpleNamespace(
            id=message_id,
            content=content,
            author=author,
            guild=guild,
            channel=channel,
            mentions=[],
            attachments=[],
            reference=reference,
            webhook_id=webhook_id,
            reply=AsyncMock(),
        )

    def _default_config(self, *, channel_id: int = 123) -> dict[str, object]:
        return {
            "ai_multi_persona_enabled": 0,
            "ai_triggered_persona_limit": 1,
            "ai_channel_whitelist": f"[{channel_id}]",
            "ai_reply_cooldown_seconds": 0,
            "ai_reply_cooldown_type": "per_user",
            "ai_self_reply_limit": 3,
            "ai_auto_channels": f"[{channel_id}]",
            "ai_auto_threshold": 0,
            "ai_streaming_enabled": 0,
        }

    async def _wait_for_background_turns(self, delay: float = 0.05) -> None:
        await asyncio.sleep(delay)

    async def test_reply_to_persona_webhook_is_treated_as_direct_trigger(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        brain._track_outbound_bot_message(
            message_id=900,
            owner_kind="persona_webhook",
            persona_mode="mode_femboy",
        )
        message = self._make_message(
            content="what do you mean?",
            reply_to_message_id=900,
        )

        await brain.on_message(message)
        await self._wait_for_background_turns()

        self.assertEqual(brain._execute_persona_invocation.await_count, 1)

    async def test_foreign_webhook_message_stays_quiet(self) -> None:
        brain = self._make_brain()
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )

        message = self._make_message(content="what do you think?", webhook_id=555)

        await brain.on_message(message)

        self.assertEqual(brain._execute_persona_invocation.await_count, 0)

    async def test_same_user_explicit_fragments_are_coalesced_into_one_turn(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        message_one = self._make_message(content="I WANT TO", message_id=5001)
        message_one.mentions = [brain.bot.user]
        message_two = self._make_message(content="COOK BEEF TODAY", message_id=5002)
        message_two.mentions = [brain.bot.user]

        await brain.on_message(message_one)
        await brain.on_message(message_two)
        await self._wait_for_background_turns()

        self.assertEqual(brain._execute_persona_invocation.await_count, 1)
        call = brain._execute_persona_invocation.await_args
        self.assertIs(call.kwargs["message"], message_two)
        self.assertEqual(call.kwargs["content_for_prompt"], "I WANT TO\nCOOK BEEF TODAY")
        recent_messages = brain.get_context(123).get_recent_messages(limit=5)
        self.assertEqual([item["content"] for item in recent_messages], ["I WANT TO\nCOOK BEEF TODAY"])

    async def test_same_user_non_trigger_fragment_still_merges_while_turn_is_pending(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        message_one = self._make_message(content="I WANT YOU TO", message_id=5051)
        message_one.mentions = [brain.bot.user]
        message_two = self._make_message(content="SEND ME CAT PICS", message_id=5052)

        await brain.on_message(message_one)
        await brain.on_message(message_two)
        await self._wait_for_background_turns()

        self.assertEqual(brain._execute_persona_invocation.await_count, 1)
        call = brain._execute_persona_invocation.await_args
        self.assertIs(call.kwargs["message"], message_two)
        self.assertEqual(call.kwargs["content_for_prompt"], "I WANT YOU TO\nSEND ME CAT PICS")
        recent_messages = brain.get_context(123).get_recent_messages(limit=5)
        self.assertEqual(
            [item["content"] for item in recent_messages],
            ["I WANT YOU TO\nSEND ME CAT PICS"],
        )

    async def test_different_users_keep_independent_pending_turns(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        message_one = self._make_message(content="hello there", author_id=111, message_id=6001)
        message_one.mentions = [brain.bot.user]
        message_two = self._make_message(content="can you help?", author_id=222, message_id=6002)
        message_two.mentions = [brain.bot.user]

        await brain.on_message(message_one)
        await brain.on_message(message_two)
        await self._wait_for_background_turns()

        self.assertEqual(brain._execute_persona_invocation.await_count, 2)

    async def test_same_user_fragment_before_visible_output_restarts_with_merged_turn(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        first_started = asyncio.Event()
        first_released = asyncio.Event()
        first_cancelled = asyncio.Event()
        observed_prompts: list[str] = []

        async def fake_execute(**kwargs):
            observed_prompts.append(kwargs["content_for_prompt"])
            if len(observed_prompts) == 1:
                first_started.set()
                try:
                    await first_released.wait()
                except asyncio.CancelledError:
                    first_cancelled.set()
                    raise
            return SimpleNamespace(id=4242)

        brain._execute_persona_invocation = AsyncMock(side_effect=fake_execute)

        message_one = self._make_message(content="I WANT TO", message_id=7001)
        message_one.mentions = [brain.bot.user]
        message_two = self._make_message(content="COOK", message_id=7002)
        message_two.mentions = [brain.bot.user]

        await brain.on_message(message_one)
        await asyncio.sleep(0.03)
        await first_started.wait()

        await brain.on_message(message_two)
        await asyncio.sleep(0.05)
        first_released.set()
        await self._wait_for_background_turns()

        self.assertTrue(first_cancelled.is_set())
        self.assertEqual(observed_prompts[-1], "I WANT TO\nCOOK")

    async def test_pre_visible_restart_does_not_duplicate_context_snapshot(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        first_started = asyncio.Event()
        first_released = asyncio.Event()
        seen_snapshots: list[str] = []

        async def fake_execute(**kwargs):
            seen_snapshots.append(kwargs["context_snapshot"])
            if len(seen_snapshots) == 1:
                first_started.set()
                try:
                    await first_released.wait()
                except asyncio.CancelledError:
                    raise
            return SimpleNamespace(id=4242)

        brain._execute_persona_invocation = AsyncMock(side_effect=fake_execute)

        message_one = self._make_message(content="I WANT TO", message_id=7101)
        message_one.mentions = [brain.bot.user]
        message_two = self._make_message(content="COOK", message_id=7102)
        message_two.mentions = [brain.bot.user]

        await brain.on_message(message_one)
        await asyncio.sleep(0.03)
        await first_started.wait()

        await brain.on_message(message_two)
        await asyncio.sleep(0.05)
        first_released.set()
        await self._wait_for_background_turns()

        self.assertEqual(seen_snapshots[-1], "User: I WANT TO\nCOOK")
        recent_messages = brain.get_context(123).get_recent_messages(limit=5)
        self.assertEqual([item["content"] for item in recent_messages], ["I WANT TO\nCOOK"])

    async def test_same_user_visible_stream_buffers_one_follow_up_turn(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        first_started = asyncio.Event()
        first_released = asyncio.Event()
        observed_prompts: list[str] = []
        key = ai_brain.TurnKey(channel_id=123, user_id=111)

        async def fake_execute(**kwargs):
            observed_prompts.append(kwargs["content_for_prompt"])
            active = brain.turn_coordinator.get_active(key)
            if len(observed_prompts) == 1 and active is not None:
                brain.turn_coordinator.mark_visible(key, version=active.version)
                first_started.set()
                await first_released.wait()
            return SimpleNamespace(id=4242)

        brain._execute_persona_invocation = AsyncMock(side_effect=fake_execute)

        message_one = self._make_message(content="I WANT TO", message_id=8001)
        message_one.mentions = [brain.bot.user]
        message_two = self._make_message(content="BEEF TODAY", message_id=8002)
        message_two.mentions = [brain.bot.user]
        message_three = self._make_message(content="CAN YOU HELP ME", message_id=8003)
        message_three.mentions = [brain.bot.user]

        await brain.on_message(message_one)
        await asyncio.sleep(0.03)
        await first_started.wait()

        await brain.on_message(message_two)
        await brain.on_message(message_three)
        await asyncio.sleep(0.05)
        self.assertEqual(brain._execute_persona_invocation.await_count, 1)

        first_released.set()
        await asyncio.sleep(0.05)
        await self._wait_for_background_turns()

        self.assertEqual(brain._execute_persona_invocation.await_count, 2)
        self.assertEqual(observed_prompts[-1], "BEEF TODAY\nCAN YOU HELP ME")

    async def test_cog_unload_cancels_background_turn_tasks(self) -> None:
        brain = self._make_brain()
        key = ai_brain.TurnKey(channel_id=123, user_id=111)
        message = self._make_message(content="hello", message_id=8500)
        pending_task = asyncio.create_task(asyncio.sleep(10))
        active_task = asyncio.create_task(asyncio.sleep(10))
        follow_up_task = asyncio.create_task(asyncio.sleep(10))
        brain.pending_turn_tasks[key] = pending_task
        brain.active_turn_tasks[key] = active_task
        brain.follow_up_turn_tasks[key] = follow_up_task
        pending = brain.turn_coordinator.upsert_pending(
            key,
            fragment_text="hello",
            source_message=message,
            now=1.0,
        )
        brain.turn_coordinator.mark_active(pending, now=2.0)
        brain.turn_coordinator.mark_visible(key, version=pending.version)
        brain.turn_coordinator.buffer_follow_up(
            key,
            fragment_text="world",
            source_message=message,
            now=3.0,
        )

        await brain.cog_unload()
        await asyncio.sleep(0)

        self.assertTrue(pending_task.cancelled())
        self.assertTrue(active_task.cancelled())
        self.assertTrue(follow_up_task.cancelled())
        self.assertIsNone(brain.turn_coordinator.get_pending(key))
        self.assertIsNone(brain.turn_coordinator.get_active(key))
        self.assertIsNone(brain.turn_coordinator.get_buffered_follow_up(key))

    async def test_cog_unload_cancels_persona_queue_tasks(self) -> None:
        brain = self._make_brain()
        release = asyncio.Event()

        async def runner(_job):
            await release.wait()

        await brain.persona_queue.enqueue(123, ai_brain.PersonaInvocationJob(mode_key="mode_default"))
        task = brain.persona_queue.schedule_drain(123, runner)
        self.assertIsNotNone(task)
        await asyncio.sleep(0)

        await brain.cog_unload()
        await asyncio.sleep(0)

        self.assertTrue(task.cancelled())
        self.assertFalse(brain.persona_queue._queues)
        self.assertFalse(brain.persona_queue._tasks)

    async def test_background_persona_queue_failure_is_logged(self) -> None:
        brain = self._make_brain()
        message = self._make_message(content="hello", message_id=8510)
        job = ai_brain.PersonaInvocationJob(
            mode_key="mode_default",
            source_message=message,
            guild_config=self._default_config(),
            content_for_prompt="hello",
            context_snapshot="User: hello",
        )
        await brain.persona_queue.enqueue(message.channel.id, job)
        brain._execute_persona_invocation = AsyncMock(side_effect=RuntimeError("queue boom"))

        with patch.object(ai_brain.logger, "error") as log_error:
            task = brain._schedule_persona_queue_drain(message.channel.id)
            self.assertIsNotNone(task)
            with self.assertRaises(RuntimeError):
                await task

        self.assertGreaterEqual(log_error.call_count, 1)
        self.assertIn("persona queue", log_error.call_args.args[0].lower())

    async def test_same_user_message_after_visible_stream_finishes_still_merges_into_follow_up(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.05
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))

        first_started = asyncio.Event()
        first_released = asyncio.Event()
        observed_prompts: list[str] = []
        key = ai_brain.TurnKey(channel_id=123, user_id=111)

        async def fake_execute(**kwargs):
            observed_prompts.append(kwargs["content_for_prompt"])
            active = brain.turn_coordinator.get_active(key)
            if len(observed_prompts) == 1 and active is not None:
                brain.turn_coordinator.mark_visible(key, version=active.version)
                first_started.set()
                await first_released.wait()
            return SimpleNamespace(id=4242)

        brain._execute_persona_invocation = AsyncMock(side_effect=fake_execute)

        message_one = self._make_message(content="FIRST", message_id=9001)
        message_one.mentions = [brain.bot.user]
        message_two = self._make_message(content="SECOND", message_id=9002)
        message_two.mentions = [brain.bot.user]
        message_three = self._make_message(content="THIRD", message_id=9003)
        message_three.mentions = [brain.bot.user]

        await brain.on_message(message_one)
        await asyncio.sleep(0.06)
        await first_started.wait()

        await brain.on_message(message_two)
        await asyncio.sleep(0.01)
        first_released.set()
        await asyncio.sleep(0.01)
        await brain.on_message(message_three)
        await asyncio.sleep(0.08)

        self.assertEqual(brain._execute_persona_invocation.await_count, 2)
        self.assertEqual(observed_prompts[-1], "SECOND\nTHIRD")

    async def test_same_user_follow_up_waits_for_queued_secondary_persona_to_finish(self) -> None:
        brain = self._make_brain()
        brain.turn_coordinator.debounce_window = 0.01
        config = self._default_config()
        config["ai_multi_persona_enabled"] = 1
        config["ai_triggered_persona_limit"] = 2
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=config),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))
        brain._get_triggered_modes_in_order = AsyncMock(
            return_value=["mode_femboy", "mode_default"]
        )
        brain._resolve_active_persona_modes = AsyncMock(
            return_value=["mode_femboy", "mode_default"]
        )

        queued_started = asyncio.Event()
        queued_released = asyncio.Event()
        observed_modes: list[str] = []
        observed_prompts: list[str] = []
        key = ai_brain.TurnKey(channel_id=123, user_id=111)

        async def fake_execute(**kwargs):
            observed_modes.append(kwargs["mode"])
            observed_prompts.append(kwargs["content_for_prompt"])
            active = brain.turn_coordinator.get_active(key)
            if kwargs["mode"] == "mode_femboy" and active is not None:
                brain.turn_coordinator.mark_visible(key, version=active.version)
            if kwargs["mode"] == "mode_default":
                queued_started.set()
                await queued_released.wait()
            return SimpleNamespace(id=4242)

        brain._execute_persona_invocation = AsyncMock(side_effect=fake_execute)

        first_message = self._make_message(content="FIRST", message_id=9201)
        first_message.mentions = [brain.bot.user]
        follow_up_message = self._make_message(content="SECOND", message_id=9202)
        follow_up_message.mentions = [brain.bot.user]

        await brain.on_message(first_message)
        await asyncio.sleep(0.05)
        await queued_started.wait()

        await brain.on_message(follow_up_message)
        await asyncio.sleep(0.05)

        self.assertEqual(brain._execute_persona_invocation.await_count, 2)

        queued_released.set()
        await asyncio.sleep(0.05)
        await self._wait_for_background_turns()

        self.assertEqual(brain._execute_persona_invocation.await_count, 4)
        self.assertEqual(observed_modes, ["mode_femboy", "mode_default", "mode_femboy", "mode_default"])
        self.assertEqual(observed_prompts[-2:], ["SECOND", "SECOND"])

    async def test_non_whitelisted_passive_candidate_stays_quiet(self) -> None:
        brain = self._make_brain()
        config = self._default_config(channel_id=999)
        config["ai_auto_channels"] = "[123]"
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch("cogs.ai_brain.get_guild_config", new=AsyncMock(return_value=config))

        message = self._make_message(content="what do you think about this?", channel_id=123)

        await brain.on_message(message)

        self.assertEqual(brain._execute_persona_invocation.await_count, 0)

    async def test_passive_candidate_respects_reply_cooldown(self) -> None:
        brain = self._make_brain()
        config = self._default_config()
        config["ai_reply_cooldown_seconds"] = 30
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch("cogs.ai_brain.get_guild_config", new=AsyncMock(return_value=config))
        self._start_patch("cogs.ai_brain.check_reply_cooldown", return_value=(True, 22))

        message = self._make_message(content="what do you think about this?", channel_id=123)

        await brain.on_message(message)

        self.assertEqual(brain._execute_persona_invocation.await_count, 0)

    async def test_rate_limited_explicit_trigger_still_enters_context(self) -> None:
        brain = self._make_brain()
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=False))

        message = self._make_message(content="hello there", message_id=5050)
        message.mentions = [brain.bot.user]

        await brain.on_message(message)

        recent_messages = brain.get_context(123).get_recent_messages(limit=5)
        self.assertEqual([item["content"] for item in recent_messages], ["hello there"])
        self.assertEqual(message.reply.await_count, 1)

    async def test_auto_channel_threshold_zero_requires_positive_context(self) -> None:
        brain = self._make_brain()
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )

        message = self._make_message(content="ok", channel_id=123)

        await brain.on_message(message)

        self.assertEqual(brain._execute_persona_invocation.await_count, 0)

    async def test_auto_channel_threshold_zero_with_strong_invitation_replies(self) -> None:
        brain = self._make_brain()
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch("cogs.ai_brain.ai_limiter.acquire", new=AsyncMock(return_value=True))
        context = brain.get_context(123)
        context.add_message(4100, 222, "A", "we need a second opinion")

        message = self._make_message(content="what do you think about this fix?", channel_id=123)

        await brain.on_message(message)

        self.assertEqual(brain._execute_persona_invocation.await_count, 1)

    async def test_user_reply_visibility_opt_out_blocks_passive_trigger(self) -> None:
        brain = self._make_brain()
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch(
            "cogs.ai_brain.get_guild_config",
            new=AsyncMock(return_value=self._default_config()),
        )
        self._start_patch(
            "cogs.ai_brain.get_personal_memory_privacy",
            new=AsyncMock(
                return_value={
                    "personal_memory_opt_out": False,
                    "allow_mention_fact_lookup": False,
                    "personal_memory_export_enabled": True,
                    "passive_reply_visibility_opt_out": True,
                    "privacy_updated_at": None,
                }
            ),
        )
        context = brain.get_context(123)
        context.add_message(4100, 222, "A", "we need a second opinion")
        message = self._make_message(content="what do you think about this fix?", channel_id=123)

        await brain.on_message(message)

        self.assertEqual(brain._execute_persona_invocation.await_count, 0)

    async def test_passive_auto_channel_counter_does_not_bleed_between_users(self) -> None:
        brain = self._make_brain()
        config = self._default_config()
        config["ai_auto_threshold"] = 2
        self._start_patch("cogs.ai_brain.get_server_mode", new=AsyncMock(return_value="mode_femboy"))
        self._start_patch("cogs.ai_brain.get_guild_config", new=AsyncMock(return_value=config))

        first_user_message = self._make_message(content="hello there", author_id=111, message_id=9301)
        second_user_message = self._make_message(
            content="what do you think about this fix?",
            author_id=222,
            message_id=9302,
        )

        await brain.on_message(first_user_message)
        await brain.on_message(second_user_message)

        self.assertEqual(brain._execute_persona_invocation.await_count, 0)


class ConfigSummaryTests(unittest.TestCase):
    def test_ai_embed_explains_conservative_auto_channel_behavior(self) -> None:
        with ExitStack() as stack:
            stack.enter_context(patch.object(config_cog, "get_encryption", return_value=object()))
            cog = config_cog.Config(SimpleNamespace())

        embed = cog._build_ai_embed(
            {
                "ai_channel_whitelist": "[123]",
                "ai_auto_channels": "[123]",
                "ai_auto_threshold": 0,
                "ai_reply_cooldown_seconds": 0,
                "ai_reply_cooldown_type": "per_user",
                "ai_self_reply_limit": 3,
                "ai_multi_persona_enabled": 0,
                "ai_triggered_persona_limit": 1,
                "ai_persona_webhooks_enabled": 1,
                "ai_streaming_enabled": 1,
                "ai_stream_min_flush_chars": 120,
                "ai_stream_max_total_chars": 6000,
                "ai_thought_log_level": "off",
                "ai_thought_log_channel_id": 0,
            }
        )

        routing_field = next(field for field in embed.fields if field.name == "Routing")
        self.assertIn("always eligible", routing_field.value.lower())


if __name__ == "__main__":
    unittest.main()
