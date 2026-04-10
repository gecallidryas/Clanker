import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cogs.ai_brain import AIBrain


class PersonaPromptDialogueTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_prompt_prefers_custom_persona_dialogues(self) -> None:
        brain = AIBrain(bot=SimpleNamespace())
        custom_persona = {
            "normal_prompt": "persona prompt",
            "sample_dialogues_json": json.dumps(["first line", "second line"]),
        }

        parsed = brain._persona_sample_dialogues_from_record(custom_persona)
        self.assertEqual(parsed, ["first line", "second line"])

    async def test_resolve_sample_dialogues_prefers_custom_persona_dialogues(self) -> None:
        brain = AIBrain(bot=SimpleNamespace())
        custom_persona = {
            "normal_prompt": "persona prompt",
            "sample_dialogues_json": json.dumps(["first line", "second line"]),
        }

        with patch(
            "cogs.ai_brain.get_custom_persona_by_mode_key",
            AsyncMock(return_value=custom_persona),
        ), patch(
            "cogs.ai_brain.get_sample_dialogues",
            AsyncMock(return_value=[{"speaker": "Guild", "dialogue": "fallback"}]),
        ):
            parsed = await brain._resolve_sample_dialogue_lines(123, "custom_123_test")

        self.assertEqual(parsed, ["first line", "second line"])


if __name__ == "__main__":
    unittest.main()
