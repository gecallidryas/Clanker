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


class _FakeGuild:
    id = 123
    owner_id = 9999


class _FakeAuthor:
    def __init__(self):
        self.id = 777
        self.guild = _FakeGuild()
        self.guild_permissions = _FakePermissions()
        self.bot = False


class _FakeChannel:
    id = 999


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content
        self.guild = _FakeGuild()
        self.author = _FakeAuthor()
        self.channel = _FakeChannel()
        self.reply = AsyncMock(return_value=types.SimpleNamespace(id=9001, content="ok"))


class _FakeBot:
    user = types.SimpleNamespace(id=1, display_name="Femmy")


class AIBrainAdminIntentBypassTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        self._orig_member_type = ai_brain_mod.discord.Member
        ai_brain_mod.register_builtin_tools = lambda: None
        ai_brain_mod.discord.Member = _FakeAuthor
        self.brain = ai_brain_mod.AIBrain(_FakeBot())

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools
        ai_brain_mod.discord.Member = self._orig_member_type

    async def test_handle_admin_actions_rejects_supported_starboard_admin_action(self):
        original_execute = ai_brain_mod.execute_admin_action
        execute_mock = AsyncMock(return_value={"success": True, "message": "should not run"})
        ai_brain_mod.execute_admin_action = execute_mock
        try:
            message = _FakeMessage("please set up starboard")
            response = "```admin_action\n{\"action\":\"STARBOARD_SETUP\",\"params\":{\"channel_id\":333}}\n```"
            sent = await ai_brain_mod.handle_admin_actions(self.brain, message, response)
        finally:
            ai_brain_mod.execute_admin_action = original_execute

        self.assertIsNotNone(sent)
        execute_mock.assert_not_awaited()
        message.reply.assert_awaited_once_with(
            "Supported admin actions must be requested directly in chat. Please rephrase the request.",
            mention_author=False,
        )

    async def test_handle_admin_actions_rejects_supported_modlog_admin_action(self):
        original_execute = ai_brain_mod.execute_admin_action
        execute_mock = AsyncMock(return_value={"success": True, "message": "should not run"})
        ai_brain_mod.execute_admin_action = execute_mock
        try:
            message = _FakeMessage("set modlog")
            response = "```admin_action\n{\"action\":\"CONFIG_LOG\",\"params\":{\"channel_id\":333}}\n```"
            sent = await ai_brain_mod.handle_admin_actions(self.brain, message, response)
        finally:
            ai_brain_mod.execute_admin_action = original_execute

        self.assertIsNotNone(sent)
        execute_mock.assert_not_awaited()
        message.reply.assert_awaited_once_with(
            "Supported admin actions must be requested directly in chat. Please rephrase the request.",
            mention_author=False,
        )


def test_admin_intent_detects_starboard_setup_text():
    assert ai_brain_mod._is_admin_intent_content(
        "Can you set up starboard for this channel and send posts there?"
    )


def test_admin_intent_detects_channel_role_management_text():
    assert ai_brain_mod._is_admin_intent_content("Please create channel announcements and delete role temp")


def test_admin_intent_detects_read_only_supported_surface_questions():
    assert ai_brain_mod._is_admin_intent_content("what is the welcome message in #logs?")
    assert ai_brain_mod._is_admin_intent_content("show me the modlog channel")
    assert ai_brain_mod._is_admin_intent_content("what is the url safety action?")


def test_admin_intent_ignores_regular_chat():
    assert not ai_brain_mod._is_admin_intent_content("how are you doing today?")
