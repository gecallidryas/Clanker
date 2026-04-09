import sys
import types
import asyncio
import unittest
from pathlib import Path

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

from cogs.ai_brain import _is_processing_ack_response  # noqa: E402
from cogs import ai_brain as ai_brain_mod  # noqa: E402

# The stub is only needed while importing ai_brain for this test module.
sys.modules.pop("utils.rag_store", None)


def test_processing_ack_detects_interim_request_message():
    text = "I am processing the request for news regarding maneaters in Buffalo, New York."
    assert _is_processing_ack_response(text) is True


def test_processing_ack_ignores_substantive_result_messages():
    text = (
        "I found 5 results about maneaters in Buffalo. "
        "Top source says the incident happened near Delaware Park."
    )
    assert _is_processing_ack_response(text) is False


def test_processing_ack_ignores_messages_with_links():
    text = "I'm processing this now: https://example.com/article"
    assert _is_processing_ack_response(text) is False


def test_time_awareness_prompt_instructions_reference_get_current_time():
    section = ai_brain_mod.section_from_lines(
        "TIME AWARENESS",
        ai_brain_mod.TIME_AWARENESS_TOOL_LINES,
    )
    assert section is not None
    assert "get_current_time" in section.body
    assert "America/Denver" in section.body


class _FakeContextBuffer:
    def __init__(self):
        self.entries = []

    def add_message(self, message_id, author_id, author_name, content, **kwargs):
        self.entries.append(
            {
                "message_id": message_id,
                "author_id": author_id,
                "author_name": author_name,
                "content": content,
            }
        )

    def get_context(self, min_message_id=None):
        return f"snapshot:{len(self.entries)}"

    def get_context_with_appended_message(
        self,
        message_id,
        user_id,
        username,
        content,
        reply_to_username=None,
        media=None,
        min_message_id=None,
    ):
        return f"snapshot:{len(self.entries) + 1}"


class _FakeTyping:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeGuildPermissions:
    administrator = False
    manage_guild = False


class _FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self.name = "Test Guild"
        self.owner_id = 9999


class _FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.sent = []

    async def send(self, content):
        self.sent.append(content)
        return types.SimpleNamespace(
            id=9000 + len(self.sent),
            author=types.SimpleNamespace(id=999, display_name="Femmy"),
            display_name="Femmy",
            content=content,
        )

    def typing(self):
        return _FakeTyping()


class _FakeMember:
    def __init__(self, user_id: int, guild: _FakeGuild):
        self.id = user_id
        self.guild = guild
        self.display_name = "Tester"
        self.bot = False
        self.mention = f"<@{user_id}>"
        self.guild_permissions = _FakeGuildPermissions()


class _FakeMessage:
    def __init__(self, guild_id: int = 123, channel_id: int = 456, author_id: int = 789):
        self.id = 1111
        self.guild = _FakeGuild(guild_id)
        self.channel = _FakeChannel(channel_id)
        self.author = _FakeMember(author_id, self.guild)
        self.content = "hey femboy and oneesan"
        self.attachments = []
        self.mentions = []
        self.reference = None

    async def reply(self, content, mention_author=False):
        return types.SimpleNamespace(
            id=8000,
            author=types.SimpleNamespace(id=999, display_name="Femmy"),
            display_name="Femmy",
            content=content,
        )


class _FakeBot:
    def __init__(self):
        self.user = types.SimpleNamespace(id=999, display_name="Femmy")

    def get_guild(self, _guild_id: int):
        return None

    def get_user(self, _user_id: int):
        return None


class AIBrainMultiPersonaRuntimeTests(unittest.TestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        ai_brain_mod.register_builtin_tools = lambda: None
        self.brain = ai_brain_mod.AIBrain(_FakeBot())

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools

    def test_on_message_streams_primary_persona_and_queues_followups_with_frozen_context(self):
        async def _run():
            message = _FakeMessage()
            context = _FakeContextBuffer()
            prompt_calls = []
            streaming_modes = []
            stat_calls = []

            async def _fake_build_prompt(
                guild_id,
                user_id,
                user_message,
                context_snapshot,
                **kwargs,
            ):
                prompt_calls.append(
                    {
                        "mode": kwargs.get("mode_override"),
                        "context": context_snapshot,
                    }
                )
                return f"prompt:{kwargs.get('mode_override')}:{context_snapshot}"

            async def _fake_handle_streaming_turn(**kwargs):
                mode = kwargs["mode"]
                streaming_modes.append(mode)
                message_id = 7000 + len(streaming_modes)
                sent = types.SimpleNamespace(
                    id=message_id,
                    author=types.SimpleNamespace(id=999, display_name=mode),
                    display_name=mode,
                    content=f"response:{mode}",
                )
                return sent, f"raw:{mode}", None, 0

            async def _fake_increment_stat(name, guild_id=None):
                stat_calls.append((name, guild_id))

            async def _acquire(_user_id):
                return True

            async def _return_none(*args, **kwargs):
                return None

            async def _return_false(*args, **kwargs):
                return False

            async def _return_empty_list(*args, **kwargs):
                return []

            async def _return_empty_tuple(*args, **kwargs):
                return "", None

            async def _fake_get_triggered_modes_in_order(_guild_id, _content):
                return ["mode_femboy", "mode_oneesan"]

            original_acquire = ai_brain_mod.ai_limiter.acquire
            original_increment_stat = ai_brain_mod.increment_stat
            original_get_server_mode = ai_brain_mod.get_server_mode
            original_get_active_persona_modes = ai_brain_mod.get_active_persona_modes
            original_get_guild_config = ai_brain_mod.get_guild_config
            original_get_affection_by_mode = ai_brain_mod.get_affection_by_mode
            original_get_personal_memory_privacy = ai_brain_mod.get_personal_memory_privacy
            try:
                ai_brain_mod.ai_limiter.acquire = _acquire
                ai_brain_mod.increment_stat = _fake_increment_stat
                ai_brain_mod.get_server_mode = _return_none
                ai_brain_mod.get_active_persona_modes = _return_none
                ai_brain_mod.get_guild_config = _return_none
                ai_brain_mod.get_affection_by_mode = _return_none
                ai_brain_mod.get_personal_memory_privacy = _return_none

                async def _fake_get_server_mode(_guild_id):
                    return "mode_femboy"

                async def _fake_get_active_persona_modes(_guild_id):
                    return ["mode_femboy", "mode_oneesan"]

                async def _fake_get_guild_config(_guild_id):
                    return {
                        "ai_multi_persona_enabled": 1,
                        "ai_triggered_persona_limit": 2,
                        "ai_streaming_enabled": 1,
                        "reply_sequence_enabled": 0,
                        "ai_persona_webhooks_enabled": 1,
                        "ai_reply_cooldown_seconds": 0,
                        "ai_reply_cooldown_type": "off",
                        "ai_self_reply_limit": 3,
                        "ai_channel_whitelist": "",
                        "emoji_usage_enabled": 1,
                    }

                async def _fake_get_affection_by_mode(_guild_id, _user_id, _mode):
                    return {
                        "affection_level": "stranger",
                        "affection_points": 0,
                        "total_interactions": 0,
                    }

                ai_brain_mod.get_server_mode = _fake_get_server_mode
                ai_brain_mod.get_active_persona_modes = _fake_get_active_persona_modes
                ai_brain_mod.get_guild_config = _fake_get_guild_config
                ai_brain_mod.get_affection_by_mode = _fake_get_affection_by_mode

                self.brain.get_context = lambda _channel_id: context
                self.brain._handle_pending_agentic_confirmation = _return_none
                self.brain._handle_pending_admin_confirmation = _return_none
                self.brain._track_message_id = lambda *args, **kwargs: None
                self.brain._cancel_interrupted_reply_sequences = lambda *args, **kwargs: None
                self.brain._is_reply_to_bot = lambda *_args, **_kwargs: False
                self.brain._get_triggered_modes_in_order = _fake_get_triggered_modes_in_order
                self.brain._maybe_handle_starboard_setup_request = _return_false
                self.brain._maybe_handle_channel_request = _return_false
                self.brain._maybe_handle_role_request = _return_false
                self.brain._maybe_handle_admin_nl_request = _return_false
                self.brain._has_video_attachment = lambda *_args, **_kwargs: False
                self.brain._has_image_attachment = lambda *_args, **_kwargs: False
                self.brain._resolve_reply_to = lambda *_args, **_kwargs: (None, None)
                self.brain._is_mention_only = lambda *_args, **_kwargs: False
                self.brain._get_wellbeing_prompt = _return_empty_tuple
                self.brain._get_reply_context = _return_none
                self.brain.build_prompt = _fake_build_prompt
                self.brain._prompt_to_chat_payload = lambda _prompt: ("system", [])
                self.brain._build_stream_tool_schemas = _return_empty_list
                self.brain._handle_streaming_turn = _fake_handle_streaming_turn
                self.brain._refresh_conversation = lambda *args, **kwargs: None
                self.brain.turn_coordinator.debounce_window = 0.0

                await self.brain.on_message(message)
                turn_key = self.brain._turn_key_for_message(message)
                pending_task = self.brain.pending_turn_tasks.get(turn_key)
                if pending_task is not None:
                    await pending_task
                active_task = self.brain.active_turn_tasks.get(turn_key)
                if active_task is not None:
                    await active_task

                self.assertEqual(streaming_modes, ["mode_femboy", "mode_oneesan"])
                self.assertEqual(
                    prompt_calls,
                    [
                        {"mode": "mode_femboy", "context": "snapshot:1"},
                        {"mode": "mode_oneesan", "context": "snapshot:1"},
                    ],
                )
                self.assertEqual(stat_calls, [("messages_processed", message.guild.id)])
            finally:
                ai_brain_mod.ai_limiter.acquire = original_acquire
                ai_brain_mod.increment_stat = original_increment_stat
                ai_brain_mod.get_server_mode = original_get_server_mode
                ai_brain_mod.get_active_persona_modes = original_get_active_persona_modes
                ai_brain_mod.get_guild_config = original_get_guild_config
                ai_brain_mod.get_affection_by_mode = original_get_affection_by_mode
                ai_brain_mod.get_personal_memory_privacy = original_get_personal_memory_privacy

        asyncio.run(_run())
