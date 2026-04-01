import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


if "utils.rag_store" not in sys.modules:
    rag_store_stub = types.ModuleType("utils.rag_store")

    async def _dummy_get_rag_context(*args, **kwargs):
        return ""

    rag_store_stub.get_rag_context = _dummy_get_rag_context
    sys.modules["utils.rag_store"] = rag_store_stub


from cogs import ai_brain as ai_brain_mod  # noqa: E402


class _FakeBot:
    def __init__(self, bot_user_id: int = 999):
        self.user = types.SimpleNamespace(id=bot_user_id)


class _FakeReference:
    def __init__(self, message_id=None, resolved=None):
        self.message_id = message_id
        self.resolved = resolved


class _FakeChannel:
    def __init__(self, messages=None):
        self._messages = messages or {}

    async def fetch_message(self, message_id: int):
        return self._messages[message_id]


class _FakeMessage:
    def __init__(self, author_id: int, channel, reference=None, message_id: int | None = None):
        self.author = types.SimpleNamespace(id=author_id)
        self.channel = channel
        self.reference = reference
        self.id = message_id


class AIBrainReplyLimitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        ai_brain_mod.register_builtin_tools = lambda: None
        self.brain = ai_brain_mod.AIBrain(_FakeBot())

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools

    async def test_refresh_conversation_respects_configured_remaining(self):
        self.brain._refresh_conversation(10, 20, remaining_messages=9)
        self.assertEqual(self.brain.active_convos[(10, 20)]["remaining"], 9)

    async def test_bot_reply_chain_depth_fetches_uncached_reference(self):
        channel = _FakeChannel()
        bot_id = self.brain.bot.user.id

        bot_message_1 = _FakeMessage(bot_id, channel, message_id=1)
        bot_message_2 = _FakeMessage(
            bot_id,
            channel,
            reference=_FakeReference(resolved=bot_message_1),
            message_id=2,
        )
        user_message = _FakeMessage(
            12345,
            channel,
            reference=_FakeReference(message_id=2, resolved=None),
        )
        channel._messages[2] = bot_message_2

        depth = await self.brain._bot_reply_chain_depth(user_message)
        self.assertEqual(depth, 2)

    async def test_bot_reply_chain_depth_counts_non_contiguous_bot_ancestors(self):
        channel = _FakeChannel()
        bot_id = self.brain.bot.user.id

        root_bot = _FakeMessage(bot_id, channel, message_id=100)
        user_middle = _FakeMessage(
            2222,
            channel,
            reference=_FakeReference(resolved=root_bot),
            message_id=101,
        )
        recent_bot = _FakeMessage(
            bot_id,
            channel,
            reference=_FakeReference(resolved=user_middle),
            message_id=102,
        )
        incoming_user = _FakeMessage(
            3333,
            channel,
            reference=_FakeReference(resolved=recent_bot),
            message_id=103,
        )

        depth = await self.brain._bot_reply_chain_depth(incoming_user)
        self.assertEqual(depth, 2)

    async def test_channel_refresh_clears_channel_scoped_memory(self):
        calls = []

        async def _fake_delete(guild_id: int, channel_id: int, user_id=None):
            calls.append((guild_id, channel_id, user_id))
            return 4

        original_delete = ai_brain_mod.delete_short_term_facts_for_channel
        ai_brain_mod.delete_short_term_facts_for_channel = _fake_delete
        try:
            self.brain.active_convos[(55, 1)] = {"remaining": 2, "last_active": datetime.now()}
            self.brain.reply_cooldowns[(55, 1)] = datetime.now()
            self.brain.auto_channel_counters[(55, 1)] = 3
            self.brain.context_reset_markers[55] = 111

            deleted = await self.brain.clear_channel_memory_boundary(777, 55, marker_message_id=222)
        finally:
            ai_brain_mod.delete_short_term_facts_for_channel = original_delete

        self.assertEqual(deleted, 4)
        self.assertEqual(calls, [(777, 55, None)])
        self.assertEqual(self.brain.context_reset_markers[55], 222)
        self.assertNotIn((55, 1), self.brain.active_convos)
        self.assertNotIn((55, 1), self.brain.reply_cooldowns)
        self.assertNotIn((55, 1), self.brain.auto_channel_counters)

    async def test_is_reply_to_bot_uses_chain_memory_reference(self):
        bot_id = self.brain.bot.user.id
        self.brain._track_message_id(5000, bot_id)
        channel = _FakeChannel()
        msg = _FakeMessage(
            author_id=1234,
            channel=channel,
            reference=_FakeReference(message_id=5000, resolved=None),
        )
        self.assertTrue(self.brain._is_reply_to_bot(msg))

    async def test_is_reply_to_bot_false_when_reference_not_bot(self):
        self.brain._track_message_id(5001, 7777)
        channel = _FakeChannel()
        msg = _FakeMessage(
            author_id=1234,
            channel=channel,
            reference=_FakeReference(message_id=5001, resolved=None),
        )
        self.assertFalse(self.brain._is_reply_to_bot(msg))


if __name__ == "__main__":
    unittest.main()
