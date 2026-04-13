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
from utils.tool_registry import ToolResult  # noqa: E402

sys.modules.pop("utils.rag_store", None)
sys.modules.pop("aiosqlite", None)
sys.modules.pop("pytz", None)


class _FakeGuild:
    def __init__(self):
        self.id = 123
        self.name = "Guild"
        self.owner_id = 9999


class _FakeAuthor:
    def __init__(self, guild: _FakeGuild):
        self.id = 777
        self.guild = guild
        self.display_name = "Tester"
        self.name = "Tester"
        self.bot = False


class _FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.sent = []

    async def send(self, content):
        self.sent.append(content)
        return types.SimpleNamespace(id=1000 + len(self.sent), content=content)


class _FakeMessage:
    def __init__(self, content: str, *, channel_id: int = 999):
        self.id = 111
        self.content = content
        self.guild = _FakeGuild()
        self.author = _FakeAuthor(self.guild)
        self.channel = _FakeChannel(channel_id)
        self.mentions = []
        self.reference = None
        self.attachments = []
        self.reply = AsyncMock(return_value=types.SimpleNamespace(id=9001, content="ok"))


class _FakeBot:
    def __init__(self):
        self.user = types.SimpleNamespace(id=1, display_name="Femmy")

    def get_guild(self, _guild_id: int):
        return None

    def get_user(self, _user_id: int):
        return None


class AIBrainExplicitSearchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        ai_brain_mod.register_builtin_tools = lambda: None
        self.brain = ai_brain_mod.AIBrain(_FakeBot())

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools

    def test_extract_explicit_web_search_query_recognizes_google_and_search_web(self):
        self.assertEqual(
            ai_brain_mod._extract_explicit_web_search_query("search web femboibot"),
            "femboibot",
        )
        self.assertEqual(
            ai_brain_mod._extract_explicit_web_search_query("google cute cats"),
            "cute cats",
        )
        self.assertIsNone(ai_brain_mod._extract_explicit_web_search_query("what is a cat"))

    async def test_maybe_handle_explicit_web_search_executes_tool_and_replies(self):
        original_execute_tool = ai_brain_mod.execute_tool
        original_build_tool_context = self.brain._build_tool_context
        execute_mock = AsyncMock(
            return_value=ToolResult(
                ok=True,
                summary="Web search complete.",
                data={"formatted": "1. [Example](https://example.com)\nSnippet"},
            )
        )
        ai_brain_mod.execute_tool = execute_mock
        self.brain._build_tool_context = lambda **_kwargs: types.SimpleNamespace()
        try:
            message = _FakeMessage("web search femboibot")
            handled = await self.brain._maybe_handle_explicit_web_search(
                message=message,
                guild_config={"web_search_enabled": 1},
            )
        finally:
            ai_brain_mod.execute_tool = original_execute_tool
            self.brain._build_tool_context = original_build_tool_context

        self.assertTrue(handled)
        execute_mock.assert_awaited_once()
        self.assertEqual(execute_mock.await_args.args[0], "web_search")
        self.assertEqual(execute_mock.await_args.args[1], {"query": "femboibot"})
        message.reply.assert_awaited_once_with(
            "1. [Example](https://example.com)\nSnippet",
            mention_author=False,
        )
