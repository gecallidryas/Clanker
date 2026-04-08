import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))
sys.path.insert(0, str(ROOT))

if "utils.rag_store" not in sys.modules:
    rag_store_stub = types.ModuleType("utils.rag_store")

    async def _dummy_get_rag_context(*args, **kwargs):
        return ""

    rag_store_stub.get_rag_context = _dummy_get_rag_context
    sys.modules["utils.rag_store"] = rag_store_stub

from cogs import ai_brain as ai_brain_mod

sys.modules.pop("utils.rag_store", None)


class _FakeBot:
    def __init__(self):
        self.user = types.SimpleNamespace(id=999, display_name="Femmy")

    def get_user(self, user_id: int):
        if user_id == 222:
            return types.SimpleNamespace(id=222, display_name="Target User")
        return None

    def get_guild(self, _guild_id: int):
        return None


class _FakeMember:
    id = 111
    display_name = "Prompt User"


class AIBrainPromptContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_response_uses_openrouter_when_selected_for_normal_mode(self):
        brain = ai_brain_mod.AIBrain(_FakeBot())

        with patch(
            "cogs.ai_brain.get_guild_config",
            AsyncMock(return_value={"normal_text_provider": "openrouter"}),
        ), patch(
            "cogs.ai_brain.get_evil_mode",
            AsyncMock(return_value=False),
        ), patch(
            "cogs.ai_brain.generate_guild_openrouter_text",
            AsyncMock(return_value=("openrouter reply", "openrouter")),
        ) as openrouter_mock, patch(
            "cogs.ai_brain.generate_guild_custom_text",
            AsyncMock(return_value=("custom reply", "custom")),
        ) as custom_mock, patch(
            "cogs.ai_brain.generate_guild_gemini_text",
            AsyncMock(return_value=("gemini reply", "gemini")),
        ) as gemini_mock:
            response = await brain.generate_response("hello", guild_id=123, allow_evil=False)

        self.assertEqual(response, "openrouter reply")
        openrouter_mock.assert_awaited_once()
        custom_mock.assert_not_awaited()
        gemini_mock.assert_not_awaited()

    async def test_build_prompt_includes_regular_aliases_for_current_and_mentioned_users(self):
        brain = ai_brain_mod.AIBrain(_FakeBot())

        with patch("cogs.ai_brain.register_builtin_tools", return_value=None), patch(
            "cogs.ai_brain.get_server_mode",
            AsyncMock(return_value="mode_femboy"),
        ), patch(
            "cogs.ai_brain.get_evil_mode",
            AsyncMock(return_value=False),
        ), patch.object(
            brain,
            "_load_persona",
            AsyncMock(return_value="persona prompt"),
        ), patch(
            "cogs.ai_brain.get_guild_config",
            AsyncMock(return_value={"normal_text_provider": "gemini"}),
        ), patch(
            "cogs.ai_brain.get_personal_memories",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_channel_recency_summary",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_guild_recency_summary",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_mention_lookup_personal_memories",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_server_memory",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_persona_attributes",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_sample_dialogues",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_affection_by_mode",
            AsyncMock(return_value={"affection_level": "friend", "affection_points": 250}),
        ), patch.object(
            brain,
            "get_user_gender",
            AsyncMock(return_value="unknown"),
        ), patch(
            "cogs.ai_brain.get_strict_alias",
            AsyncMock(return_value=None),
        ), patch(
            "cogs.ai_brain.get_aliases",
            AsyncMock(side_effect=[["pj", "promptkid"], ["target-alias"]]),
        ), patch.object(
            brain,
            "_build_expression_prompt_context",
            AsyncMock(return_value=([], [], [])),
        ), patch(
            "cogs.ai_brain.render_prompt_tool_definitions",
            AsyncMock(return_value=""),
        ):
            prompt = await brain.build_prompt(
                123,
                111,
                "Tell me about <@222>.",
                "ctx",
                channel_id=999,
                member=_FakeMember(),
                mode_override="mode_femboy",
            )

        self.assertIn("Current user aliases: pj, promptkid", prompt)
        self.assertIn("Target User aliases: target-alias", prompt)

    async def test_build_prompt_adds_oneesan_brevity_guidance(self):
        brain = ai_brain_mod.AIBrain(_FakeBot())

        with patch("cogs.ai_brain.register_builtin_tools", return_value=None), patch(
            "cogs.ai_brain.get_server_mode",
            AsyncMock(return_value="mode_oneesan"),
        ), patch(
            "cogs.ai_brain.get_evil_mode",
            AsyncMock(return_value=False),
        ), patch.object(
            brain,
            "_load_persona",
            AsyncMock(return_value="persona prompt"),
        ), patch(
            "cogs.ai_brain.get_guild_config",
            AsyncMock(return_value={"normal_text_provider": "gemini"}),
        ), patch(
            "cogs.ai_brain.get_personal_memories",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_channel_recency_summary",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_guild_recency_summary",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_mention_lookup_personal_memories",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_server_memory",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_persona_attributes",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_sample_dialogues",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_affection_by_mode",
            AsyncMock(return_value={"affection_level": "friend", "affection_points": 250}),
        ), patch.object(
            brain,
            "get_user_gender",
            AsyncMock(return_value="unknown"),
        ), patch(
            "cogs.ai_brain.get_strict_alias",
            AsyncMock(return_value=None),
        ), patch(
            "cogs.ai_brain.get_aliases",
            AsyncMock(return_value=[]),
        ), patch.object(
            brain,
            "_build_expression_prompt_context",
            AsyncMock(return_value=([], [], [])),
        ), patch(
            "cogs.ai_brain.render_prompt_tool_definitions",
            AsyncMock(return_value=""),
        ):
            prompt = await brain.build_prompt(
                123,
                111,
                "hello",
                "ctx",
                channel_id=999,
                member=_FakeMember(),
                mode_override="mode_oneesan",
            )

        self.assertIn("avoid rambling", prompt.lower())


if __name__ == "__main__":
    unittest.main()
