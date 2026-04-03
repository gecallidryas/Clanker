import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from cogs.config import Config  # noqa: E402


class _FakeBot(SimpleNamespace):
    def __init__(self):
        super().__init__()


class AIConfigSurfaceTests(unittest.TestCase):
    def test_ai_embed_surfaces_persona_runtime_and_keeps_streaming(self):
        cog = Config(_FakeBot())
        embed = cog._build_ai_embed(
            {
                "ai_multi_persona_enabled": 1,
                "ai_triggered_persona_limit": 2,
                "ai_persona_webhooks_enabled": 0,
                "ai_streaming_enabled": 1,
                "ai_stream_min_flush_chars": 120,
                "ai_stream_max_total_chars": 6000,
            }
        )

        field_map = {field.name: field.value for field in embed.fields}

        self.assertIn("Streaming", field_map)
        self.assertIn("Persona runtime", field_map)
        self.assertIn("Multi-persona", field_map["Persona runtime"])
        self.assertIn("Webhook identity", field_map["Persona runtime"])
        self.assertNotIn("Reply sequences", "\n".join(field_map.keys()))

    def test_features_doc_describes_multi_persona_queue_runtime(self):
        text = (ROOT / "docs" / "FEATURES.md").read_text(encoding="utf-8").lower()

        self.assertIn("stream", text)
        self.assertIn("multi-persona", text)
        self.assertIn("webhook", text)

    def test_reply_sequence_commands_are_not_exposed_on_ai_group(self):
        command_names = [command.name for command in Config.ai_group.commands]

        self.assertFalse(any(name.startswith("reply_sequence") for name in command_names))

    def test_native_config_panel_no_longer_mentions_reply_sequence_controls(self):
        text = (ROOT / "discord_bot" / "utils" / "native_config_panel.py").read_text(encoding="utf-8").lower()

        self.assertNotIn("reply_sequence", text)
