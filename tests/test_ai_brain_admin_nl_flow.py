import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

if "utils.rag_store" not in sys.modules:
    rag_store_stub = types.ModuleType("utils.rag_store")

    async def _dummy_get_rag_context(*args, **kwargs):
        return ""

    rag_store_stub.get_rag_context = _dummy_get_rag_context
    sys.modules["utils.rag_store"] = rag_store_stub

if "pytz" not in sys.modules:
    pytz_stub = types.ModuleType("pytz")
    pytz_stub.UnknownTimeZoneError = Exception
    pytz_stub.timezone = lambda _name: None
    sys.modules["pytz"] = pytz_stub

if "aiosqlite" not in sys.modules:
    aiosqlite_stub = types.ModuleType("aiosqlite")

    class _Connection:
        pass

    async def _connect(*args, **kwargs):
        raise RuntimeError("aiosqlite stub should not be used in this test")

    aiosqlite_stub.Connection = _Connection
    aiosqlite_stub.Row = object
    aiosqlite_stub.connect = _connect
    sys.modules["aiosqlite"] = aiosqlite_stub

from cogs import ai_brain as ai_brain_mod  # noqa: E402

sys.modules.pop("utils.rag_store", None)
sys.modules.pop("aiosqlite", None)
sys.modules.pop("pytz", None)


class _FakePermissions:
    administrator = False
    manage_guild = True


class _FakeRole:
    def __init__(self, role_id: int, name: str):
        self.id = role_id
        self.name = name


class _FakeChannelRef:
    def __init__(self, channel_id: int, name: str):
        self.id = channel_id
        self.name = name


class _FakeGuild:
    def __init__(self):
        self.id = 123
        self.name = "Guild"
        self.owner_id = 9999
        self.text_channels = [_FakeChannelRef(222, "highlights"), _FakeChannelRef(333, "logs")]
        self.voice_channels = []
        self.categories = []
        self.roles = [_FakeRole(444, "Members")]

    def get_channel(self, channel_id: int):
        for channel in self.text_channels:
            if channel.id == channel_id:
                return channel
        return None


class _FakeAuthor:
    def __init__(self, guild: _FakeGuild, *, author_id: int = 777, display_name: str = "Admin"):
        self.id = author_id
        self.guild = guild
        self.display_name = display_name
        self.name = display_name
        self.bot = False
        self.guild_permissions = _FakePermissions()
        self.roles = []


class _FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id


class _FakeMessage:
    def __init__(
        self,
        content: str,
        guild: _FakeGuild | None = None,
        channel_id: int = 999,
        *,
        reference=None,
    ):
        self.content = content
        self.guild = guild or _FakeGuild()
        self.author = _FakeAuthor(self.guild)
        self.channel = _FakeChannel(channel_id)
        self.mentions = []
        self.reference = reference
        self.reply = AsyncMock(return_value=types.SimpleNamespace(id=9001, content="ok"))


class _FakeBot:
    def __init__(self):
        self.user = types.SimpleNamespace(id=1, display_name="Femmy")

    def get_guild(self, _guild_id: int):
        return None

    def get_user(self, _user_id: int):
        return None


class AIBrainAdminNLFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        ai_brain_mod.register_builtin_tools = lambda: None
        self.brain = ai_brain_mod.AIBrain(_FakeBot())

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools

    async def test_maybe_handle_admin_nl_request_executes_ready_intent(self):
        original_execute = ai_brain_mod.execute_admin_intent
        execute_mock = AsyncMock(return_value={"success": True, "message": "Autorole set."})
        ai_brain_mod.execute_admin_intent = execute_mock
        try:
            message = _FakeMessage("set the autorole to @Members")
            handled = await self.brain._maybe_handle_admin_nl_request(message)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute

        self.assertTrue(handled)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "autorole.set")
        self.assertEqual(execute_mock.await_args.args[1]["role_id"], 444)
        message.reply.assert_awaited_once_with("Autorole set.", mention_author=False)

    async def test_maybe_handle_admin_nl_request_executes_channel_create_without_legacy_fallback(self):
        original_execute = ai_brain_mod.execute_admin_intent
        execute_mock = AsyncMock(return_value={"success": True, "message": "Created text channel 'announcements'."})
        ai_brain_mod.execute_admin_intent = execute_mock
        try:
            message = _FakeMessage("create channel announcements")
            handled = await self.brain._maybe_handle_admin_nl_request(message)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute

        self.assertTrue(handled)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "channel.create_text")
        self.assertFalse(hasattr(self.brain, "_maybe_handle_channel_request"))

    async def test_maybe_handle_admin_nl_request_executes_role_create_without_legacy_fallback(self):
        original_execute = ai_brain_mod.execute_admin_intent
        execute_mock = AsyncMock(return_value={"success": True, "message": "Created role 'VIP'."})
        ai_brain_mod.execute_admin_intent = execute_mock
        try:
            message = _FakeMessage("create role VIP")
            handled = await self.brain._maybe_handle_admin_nl_request(message)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute

        self.assertTrue(handled)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "role.create")
        self.assertFalse(hasattr(self.brain, "_maybe_handle_role_request"))

    async def test_maybe_handle_admin_nl_request_stores_follow_up_when_slots_missing(self):
        message = _FakeMessage("set up starboard with any emoji at 5 reactions")

        handled = await self.brain._maybe_handle_admin_nl_request(message)

        self.assertTrue(handled)
        pending = self.brain._get_pending_admin_action(message.channel.id, message.author.id)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["intent"], "starboard.configure")
        message.reply.assert_awaited_once_with(
            "Which channel should I use for the starboard?",
            mention_author=False,
        )

    async def test_create_starboard_phrase_stores_missing_follow_up(self):
        message = _FakeMessage("create starboard in #logs")

        handled = await self.brain._maybe_handle_admin_nl_request(message)

        self.assertTrue(handled)
        pending = self.brain._get_pending_admin_action(message.channel.id, message.author.id)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["intent"], "starboard.configure")
        self.assertEqual(pending["missing"], ["emoji_mode", "threshold"])

    async def test_pending_admin_follow_up_executes_completed_request(self):
        original_execute = ai_brain_mod.execute_admin_intent
        execute_mock = AsyncMock(return_value={"success": True, "message": "Starboard configured."})
        ai_brain_mod.execute_admin_intent = execute_mock
        try:
            initial = _FakeMessage("set up starboard with any emoji at 5 reactions")
            await self.brain._maybe_handle_admin_nl_request(initial)
            follow_up = _FakeMessage("use #highlights", guild=initial.guild, channel_id=initial.channel.id)
            follow_up.author.id = initial.author.id
            reply = await self.brain._handle_pending_admin_confirmation(follow_up)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute

        self.assertIsNotNone(reply)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "starboard.configure")
        self.assertEqual(execute_mock.await_args.args[1]["channel_id"], 222)
        follow_up.reply.assert_awaited_once_with("Starboard configured.", mention_author=False)

    async def test_pending_delete_follow_up_prompts_for_confirmation_after_target_is_supplied(self):
        initial = _FakeMessage("delete channel")

        handled = await self.brain._maybe_handle_admin_nl_request(initial)

        self.assertTrue(handled)
        pending = self.brain._get_pending_admin_action(initial.channel.id, initial.author.id)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["intent"], "channel.delete")

        follow_up = _FakeMessage("use #logs", guild=initial.guild, channel_id=initial.channel.id)
        follow_up.author.id = initial.author.id
        reply = await self.brain._handle_pending_admin_confirmation(follow_up)

        self.assertIsNotNone(reply)
        pending = self.brain._get_pending_admin_action(initial.channel.id, initial.author.id)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["params"]["channel_id"], 333)
        follow_up.reply.assert_awaited_once_with(
            'Please confirm this delete action for 333 by replying "confirm".',
            mention_author=False,
        )

    async def test_maybe_handle_admin_nl_request_executes_timeout_through_executor(self):
        original_execute = ai_brain_mod.execute_admin_intent
        original_handle = ai_brain_mod.handle_agentic_actions
        execute_mock = AsyncMock(return_value={"success": True, "message": "Timed out."})
        handle_mock = AsyncMock(return_value=types.SimpleNamespace(id=42, content="done"))
        ai_brain_mod.execute_admin_intent = execute_mock
        ai_brain_mod.handle_agentic_actions = handle_mock
        try:
            message = _FakeMessage("timeout <@666> for 10 minutes")
            handled = await self.brain._maybe_handle_admin_nl_request(message)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute
            ai_brain_mod.handle_agentic_actions = original_handle

        self.assertTrue(handled)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "moderation.timeout")
        handle_mock.assert_not_awaited()

    async def test_maybe_handle_admin_nl_request_executes_ban_through_executor(self):
        original_execute = ai_brain_mod.execute_admin_intent
        original_handle = ai_brain_mod.handle_agentic_actions
        execute_mock = AsyncMock(return_value={"success": True, "message": "Banned."})
        handle_mock = AsyncMock(return_value=types.SimpleNamespace(id=43, content="done"))
        ai_brain_mod.execute_admin_intent = execute_mock
        ai_brain_mod.handle_agentic_actions = handle_mock
        try:
            replied_author = _FakeAuthor(_FakeGuild(), author_id=888, display_name="Raider")
            reference = types.SimpleNamespace(
                message_id=1234,
                resolved=types.SimpleNamespace(author=replied_author),
            )
            message = _FakeMessage("ban them for raids", reference=reference)
            handled = await self.brain._maybe_handle_admin_nl_request(message)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute
            ai_brain_mod.handle_agentic_actions = original_handle

        self.assertTrue(handled)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "moderation.ban")
        self.assertEqual(execute_mock.await_args.args[1]["target_id"], 888)
        handle_mock.assert_not_awaited()

    async def test_maybe_handle_admin_nl_request_executes_delete_through_executor(self):
        original_execute = ai_brain_mod.execute_admin_intent
        original_handle = ai_brain_mod.handle_agentic_actions
        execute_mock = AsyncMock(return_value={"success": True, "message": "Deleted."})
        handle_mock = AsyncMock(return_value=types.SimpleNamespace(id=44, content="done"))
        ai_brain_mod.execute_admin_intent = execute_mock
        ai_brain_mod.handle_agentic_actions = handle_mock
        try:
            initial = _FakeMessage("delete channel #logs")
            await self.brain._maybe_handle_admin_nl_request(initial)
            confirm = _FakeMessage("confirm", guild=initial.guild, channel_id=initial.channel.id)
            confirm.author.id = initial.author.id
            reply = await self.brain._handle_pending_admin_confirmation(confirm)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute
            ai_brain_mod.handle_agentic_actions = original_handle

        self.assertIsNotNone(reply)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "channel.delete")
        handle_mock.assert_not_awaited()

    async def test_manage_guild_user_can_complete_supported_unified_intents_without_legacy_fallbacks(self):
        original_execute = ai_brain_mod.execute_admin_intent
        execute_mock = AsyncMock(return_value={"success": True, "message": "Done."})
        ai_brain_mod.execute_admin_intent = execute_mock
        try:
            for content in ("create channel announcements", "create role VIP", "timeout <@666> for 10 minutes"):
                message = _FakeMessage(content)
                handled = await self.brain._maybe_handle_admin_nl_request(message)
                self.assertTrue(handled)
        finally:
            ai_brain_mod.execute_admin_intent = original_execute

        self.assertFalse(hasattr(self.brain, "_maybe_handle_channel_request"))
        self.assertFalse(hasattr(self.brain, "_maybe_handle_role_request"))
        self.assertFalse(hasattr(self.brain, "_maybe_handle_starboard_setup_request"))
        self.assertEqual(execute_mock.await_count, 3)

    async def test_unified_admin_router_does_not_call_legacy_fallbacks(self):
        original_execute = ai_brain_mod.execute_admin_intent
        execute_mock = AsyncMock(return_value={"success": True, "message": "Done."})
        ai_brain_mod.execute_admin_intent = execute_mock
        try:
            handled = await self.brain._maybe_handle_admin_nl_request(_FakeMessage("create channel announcements"))
        finally:
            ai_brain_mod.execute_admin_intent = original_execute

        self.assertTrue(handled)
        self.assertFalse(hasattr(self.brain, "_maybe_handle_channel_request"))
        self.assertFalse(hasattr(self.brain, "_maybe_handle_role_request"))
        self.assertFalse(hasattr(self.brain, "_maybe_handle_starboard_setup_request"))

    async def test_supported_admin_intents_still_work_after_fallback_removal(self):
        original_execute = ai_brain_mod.execute_admin_intent
        execute_mock = AsyncMock(return_value={"success": True, "message": "Created."})
        ai_brain_mod.execute_admin_intent = execute_mock
        try:
            handled = await self.brain._maybe_handle_admin_nl_request(_FakeMessage("create channel announcements"))
        finally:
            ai_brain_mod.execute_admin_intent = original_execute

        self.assertTrue(handled)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "channel.create_text")

    async def test_informational_admin_question_fails_closed_without_pending_state(self):
        message = _FakeMessage("show me the modlog channel")

        handled = await self.brain._maybe_handle_admin_nl_request(message)

        self.assertTrue(handled)
        self.assertIsNone(self.brain._get_pending_admin_action(message.channel.id, message.author.id))
        message.reply.assert_awaited_once_with(
            "I couldn't map that admin request safely. Please rephrase it as one supported server action.",
            mention_author=False,
        )

    async def test_non_admin_chat_still_falls_through(self):
        message = _FakeMessage("how are you doing today?")

        handled = await self.brain._maybe_handle_admin_nl_request(message)

        self.assertFalse(handled)
        self.assertIsNone(self.brain._get_pending_admin_action(message.channel.id, message.author.id))
        message.reply.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
