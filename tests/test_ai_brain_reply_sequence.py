import sys
import types
import unittest
from datetime import datetime, timedelta
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

from cogs import ai_brain as ai_brain_mod  # noqa: E402


class _FakeBot:
    def __init__(self, bot_user_id: int = 999):
        self.user = types.SimpleNamespace(id=bot_user_id, display_name="Femmy")

    def get_guild(self, _guild_id: int):
        return None

    def get_user(self, _user_id: int):
        return None


class _FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id


class _FakeReference:
    def __init__(self, message_id=None, resolved=None):
        self.message_id = message_id
        self.resolved = resolved


class _FakeMessage:
    def __init__(self, author_id: int, channel_id: int, reply_to_message_id: int | None = None):
        self.author = types.SimpleNamespace(id=author_id)
        self.channel = _FakeChannel(channel_id)
        self.reference = (
            _FakeReference(message_id=reply_to_message_id, resolved=None)
            if reply_to_message_id is not None
            else None
        )


class AIBrainReplySequenceTests(unittest.TestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        ai_brain_mod.register_builtin_tools = lambda: None
        self.brain = ai_brain_mod.AIBrain(_FakeBot())
        self.guild_config = {
            "reply_sequence_enabled": 1,
            "reply_sequence_timeout_seconds": 300,
            "reply_sequence_hard_max_stages": 4,
            "reply_sequence_allow_gif": 1,
            "reply_sequence_allow_sticker": 1,
            "reply_sequence_allow_emoji_only": 1,
        }

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools

    def test_missing_control_block_defaults_to_stop(self):
        visible, control = self.brain._extract_reply_sequence_control("hello there")

        self.assertEqual(visible, "hello there")
        self.assertFalse(control.continue_sequence)
        self.assertEqual(control.next_payload, "stop")

    def test_malformed_control_block_defaults_to_stop(self):
        visible, control = self.brain._extract_reply_sequence_control(
            "hiya\n```reply_sequence\n{not valid json}\n```"
        )

        self.assertEqual(visible, "hiya")
        self.assertFalse(control.continue_sequence)
        self.assertEqual(control.next_payload, "stop")

    def test_no_sequence_stop_behavior_does_not_store_session(self):
        control = ai_brain_mod.ReplySequenceControl(
            continue_sequence=False,
            next_payload="stop",
        )

        session = self.brain._store_reply_sequence_session(
            guild_id=1,
            channel_id=10,
            user_id=20,
            mode_key="mode_femboy",
            root_user_message_id=100,
            last_bot_message_id=200,
            stage_index=1,
            current_payload="text",
            guild_config=self.guild_config,
            control=control,
            now=datetime.now(),
        )

        self.assertIsNone(session)
        self.assertEqual(self.brain.reply_sequence_sessions, {})

    def test_valid_continuation_flow_updates_session(self):
        now = datetime.now()
        open_control = ai_brain_mod.ReplySequenceControl(
            continue_sequence=True,
            next_payload="emoji_only",
            remaining_desired_turns=2,
            tone_shift="lighter",
        )

        session = self.brain._store_reply_sequence_session(
            guild_id=1,
            channel_id=10,
            user_id=20,
            mode_key="mode_femboy",
            root_user_message_id=100,
            last_bot_message_id=200,
            stage_index=1,
            current_payload="text",
            guild_config=self.guild_config,
            control=open_control,
            now=now,
        )
        self.assertIsNotNone(session)
        self.assertEqual(session.next_payload, "emoji_only")

        incoming = _FakeMessage(author_id=20, channel_id=10, reply_to_message_id=200)
        matched = self.brain._match_reply_sequence_trigger(
            incoming,
            current_mode="mode_femboy",
            now=now + timedelta(seconds=5),
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched.last_bot_message_id, 200)

        next_control = ai_brain_mod.ReplySequenceControl(
            continue_sequence=True,
            next_payload="gif",
            remaining_desired_turns=1,
            caption="hehe",
            media_query="cute smug reaction",
        )
        updated = self.brain._complete_reply_sequence_turn(
            matched,
            last_bot_message_id=201,
            current_payload="emoji_only",
            guild_config=self.guild_config,
            control=next_control,
            now=now + timedelta(seconds=6),
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.stage_index, 2)
        self.assertEqual(updated.last_payload_type, "emoji_only")
        self.assertEqual(updated.last_bot_message_id, 201)
        self.assertEqual(updated.next_payload, "gif")
        self.assertEqual(updated.caption, "hehe")

    def test_same_user_must_reply_to_latest_bot_message(self):
        now = datetime.now()
        control = ai_brain_mod.ReplySequenceControl(
            continue_sequence=True,
            next_payload="text",
            remaining_desired_turns=1,
        )
        self.brain._store_reply_sequence_session(
            guild_id=1,
            channel_id=10,
            user_id=20,
            mode_key="mode_femboy",
            root_user_message_id=100,
            last_bot_message_id=200,
            stage_index=1,
            current_payload="text",
            guild_config=self.guild_config,
            control=control,
            now=now,
        )

        invalid = _FakeMessage(author_id=20, channel_id=10, reply_to_message_id=199)
        matched = self.brain._match_reply_sequence_trigger(
            invalid,
            current_mode="mode_femboy",
            now=now + timedelta(seconds=1),
        )

        self.assertIsNone(matched)
        self.assertNotIn((10, 20), self.brain.reply_sequence_sessions)

    def test_timeout_reset_discards_session(self):
        now = datetime.now()
        control = ai_brain_mod.ReplySequenceControl(
            continue_sequence=True,
            next_payload="text",
            remaining_desired_turns=1,
        )
        self.brain._store_reply_sequence_session(
            guild_id=1,
            channel_id=10,
            user_id=20,
            mode_key="mode_femboy",
            root_user_message_id=100,
            last_bot_message_id=200,
            stage_index=1,
            current_payload="text",
            guild_config=self.guild_config,
            control=control,
            now=now,
        )

        session = self.brain._get_reply_sequence_session(
            10,
            20,
            current_mode="mode_femboy",
            now=now + timedelta(seconds=301),
        )

        self.assertIsNone(session)
        self.assertNotIn((10, 20), self.brain.reply_sequence_sessions)

    def test_mode_change_reset_discards_session(self):
        control = ai_brain_mod.ReplySequenceControl(
            continue_sequence=True,
            next_payload="text",
            remaining_desired_turns=1,
        )
        self.brain._store_reply_sequence_session(
            guild_id=1,
            channel_id=10,
            user_id=20,
            mode_key="mode_femboy",
            root_user_message_id=100,
            last_bot_message_id=200,
            stage_index=1,
            current_payload="text",
            guild_config=self.guild_config,
            control=control,
            now=datetime.now(),
        )

        session = self.brain._get_reply_sequence_session(
            10,
            20,
            current_mode="mode_oneesan",
            now=datetime.now(),
        )

        self.assertIsNone(session)
        self.assertNotIn((10, 20), self.brain.reply_sequence_sessions)

    def test_payload_fallback_behavior(self):
        allowed = {"text", "sticker", "gif", "emoji_only"}

        self.assertEqual(
            self.brain._resolve_reply_sequence_payload(
                requested_payload="sticker",
                allowed_payloads=allowed,
                sticker_available=False,
                gif_available=True,
            ),
            "gif",
        )
        self.assertEqual(
            self.brain._resolve_reply_sequence_payload(
                requested_payload="gif",
                allowed_payloads=allowed,
                sticker_available=True,
                gif_available=False,
            ),
            "sticker",
        )
        self.assertEqual(
            self.brain._resolve_reply_sequence_payload(
                requested_payload="gif",
                allowed_payloads={"text"},
                sticker_available=False,
                gif_available=False,
            ),
            "text",
        )

    def test_build_prompt_does_not_emit_reply_sequence_runtime_instructions(self):
        async def _run():
            original_get_server_mode = ai_brain_mod.get_server_mode
            original_get_evil_mode = ai_brain_mod.get_evil_mode
            original_get_guild_config = ai_brain_mod.get_guild_config
            original_get_personal_memories = ai_brain_mod.get_personal_memories
            original_get_channel_recency_summary = ai_brain_mod.get_channel_recency_summary
            original_get_guild_recency_summary = ai_brain_mod.get_guild_recency_summary
            original_get_server_memory = ai_brain_mod.get_server_memory
            original_get_persona_attributes = ai_brain_mod.get_persona_attributes
            original_get_sample_dialogues = ai_brain_mod.get_sample_dialogues
            original_get_mention_lookup_personal_memories = ai_brain_mod.get_mention_lookup_personal_memories
            original_get_strict_alias = ai_brain_mod.get_strict_alias
            original_load_persona = self.brain._load_persona
            original_get_user_gender = self.brain.get_user_gender
            try:
                async def _server_mode(_guild_id):
                    return "mode_femboy"

                async def _evil_mode(_guild_id):
                    return False

                ai_brain_mod.get_server_mode = _server_mode
                ai_brain_mod.get_evil_mode = _evil_mode

                async def _guild_config(_guild_id):
                    return {
                        "reply_sequence_enabled": 1,
                        "reply_sequence_allow_gif": 1,
                        "reply_sequence_allow_sticker": 1,
                        "reply_sequence_allow_emoji_only": 1,
                    }

                async def _empty_list(*_args, **_kwargs):
                    return []

                async def _empty_text(*_args, **_kwargs):
                    return ""

                ai_brain_mod.get_guild_config = _guild_config
                ai_brain_mod.get_personal_memories = _empty_list
                ai_brain_mod.get_channel_recency_summary = _empty_list
                ai_brain_mod.get_guild_recency_summary = _empty_list
                ai_brain_mod.get_server_memory = _empty_list
                ai_brain_mod.get_persona_attributes = _empty_list
                ai_brain_mod.get_sample_dialogues = _empty_list
                ai_brain_mod.get_mention_lookup_personal_memories = _empty_list
                ai_brain_mod.get_strict_alias = _empty_text
                self.brain._load_persona = _empty_text
                self.brain.get_user_gender = _empty_text

                prompt = await self.brain.build_prompt(
                    guild_id=1,
                    user_id=2,
                    message="hello there",
                    context="User: hi",
                    channel_id=99,
                    allow_tools=False,
                    affection_data={
                        "affection_level": "stranger",
                        "affection_points": 0,
                        "total_interactions": 0,
                    },
                )
            finally:
                ai_brain_mod.get_server_mode = original_get_server_mode
                ai_brain_mod.get_evil_mode = original_get_evil_mode
                ai_brain_mod.get_guild_config = original_get_guild_config
                ai_brain_mod.get_personal_memories = original_get_personal_memories
                ai_brain_mod.get_channel_recency_summary = original_get_channel_recency_summary
                ai_brain_mod.get_guild_recency_summary = original_get_guild_recency_summary
                ai_brain_mod.get_server_memory = original_get_server_memory
                ai_brain_mod.get_persona_attributes = original_get_persona_attributes
                ai_brain_mod.get_sample_dialogues = original_get_sample_dialogues
                ai_brain_mod.get_mention_lookup_personal_memories = original_get_mention_lookup_personal_memories
                ai_brain_mod.get_strict_alias = original_get_strict_alias
                self.brain._load_persona = original_load_persona
                self.brain.get_user_gender = original_get_user_gender

            self.assertNotIn("reply_sequence", prompt)
            self.assertNotIn("Reply sequence rules", prompt)

        import asyncio

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
