import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from tests.helpers.discord_fakes import FakeGuild, FakeInteraction


class PersonaPanelTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod
        from utils import persona_panel_ui as persona_panel_ui_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.persona_panel_ui = importlib.reload(persona_panel_ui_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_selector_options_group_builtins_and_customs(self):
        guild_id = 41
        await self.db_handler.init_guild_db(guild_id)

        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Velvet")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Velvet",
            mode_key=mode_key,
            bio="Custom bio",
            avatar_path="/tmp/avatar.webp",
            banner_path=None,
            aliases=None,
            normal_prompt="Normal prompt",
            evil_prompt="Evil prompt",
            created_by=9,
        )

        state = await self.persona_panel_ui.load_persona_panel_state(guild_id)
        options = self.persona_panel_ui.build_persona_select_options(state)

        labels = [option.label for option in options]
        self.assertTrue(any(label.startswith("[Built-in]") for label in labels))
        self.assertTrue(any(label.startswith("[Custom]") for label in labels))
        self.assertTrue(any("Velvet" in label for label in labels))

    async def test_activate_persona_updates_mode_and_audits(self):
        guild_id = 42
        await self.db_handler.init_guild_db(guild_id)

        social_cog = SimpleNamespace(_apply_mode_profile_updates=AsyncMock())
        bot = SimpleNamespace(get_cog=lambda name: social_cog if name == "Social" else None)

        result = await self.persona_panel_ui.activate_persona_mode(
            bot=bot,
            guild_id=guild_id,
            user_id=77,
            mode_key="mode_tsundere",
        )

        self.assertEqual(result.mode_key, "mode_tsundere")
        self.assertEqual(await self.db_handler.get_server_mode(guild_id), "mode_tsundere")
        social_cog._apply_mode_profile_updates.assert_awaited_once()

        entries = await self.db_handler.get_guild_config_audit_entries(guild_id, limit=5)
        self.assertEqual(entries[0]["action"], "persona_activate")
        self.assertEqual(entries[0]["category"], "persona_presentation")
        self.assertEqual(entries[0]["target_id"], "mode_tsundere")

    async def test_toggle_evil_mode_updates_state_and_audits(self):
        guild_id = 43
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.set_server_mode(guild_id, "mode_femboy")

        social_cog = SimpleNamespace(_apply_mode_profile_updates=AsyncMock())
        bot = SimpleNamespace(get_cog=lambda name: social_cog if name == "Social" else None)

        result = await self.persona_panel_ui.set_persona_evil_mode(
            bot=bot,
            guild_id=guild_id,
            user_id=88,
            enabled=True,
        )

        self.assertTrue(result.enabled)
        self.assertTrue(await self.db_handler.get_evil_mode(guild_id))
        social_cog._apply_mode_profile_updates.assert_awaited_once()

        entries = await self.db_handler.get_guild_config_audit_entries(guild_id, limit=5)
        self.assertEqual(entries[0]["action"], "persona_toggle_evil")
        self.assertEqual(entries[0]["category"], "persona_presentation")
        self.assertEqual(entries[0]["new_value"], "true")

    async def test_delete_active_custom_persona_falls_back_to_default(self):
        guild_id = 44
        await self.db_handler.init_guild_db(guild_id)

        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Nightglass")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Nightglass",
            mode_key=mode_key,
            bio="Custom bio",
            avatar_path="/tmp/nightglass-avatar.webp",
            banner_path="/tmp/nightglass-banner.webp",
            aliases=None,
            normal_prompt="Normal prompt",
            evil_prompt="Evil prompt",
            created_by=10,
        )
        await self.db_handler.set_server_mode(guild_id, mode_key)
        await self.db_handler.set_evil_mode(guild_id, True)

        social_cog = SimpleNamespace(_apply_mode_profile_updates=AsyncMock())
        bot = SimpleNamespace(get_cog=lambda name: social_cog if name == "Social" else None)

        deleted = await self.persona_panel_ui.delete_persona_with_fallback(
            bot=bot,
            guild_id=guild_id,
            user_id=99,
            mode_key=mode_key,
        )

        self.assertTrue(deleted)
        self.assertEqual(await self.db_handler.get_server_mode(guild_id), "mode_default")
        self.assertFalse(await self.db_handler.get_evil_mode(guild_id))
        self.assertIsNone(await self.db_handler.get_custom_persona_by_mode_key(guild_id, mode_key))
        social_cog._apply_mode_profile_updates.assert_awaited()

        entries = await self.db_handler.get_guild_config_audit_entries(guild_id, limit=10)
        actions = [entry["action"] for entry in entries]
        self.assertIn("persona_activate", actions)
        self.assertIn("persona_delete", actions)

    async def test_delete_button_requires_auth_handoff(self):
        guild_id = 45
        await self.db_handler.init_guild_db(guild_id)

        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Cipher")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Cipher",
            mode_key=mode_key,
            bio="Custom bio",
            avatar_path=None,
            banner_path=None,
            aliases=None,
            normal_prompt="Normal prompt",
            evil_prompt=None,
            created_by=11,
        )

        bot = SimpleNamespace(get_cog=lambda name: None)
        view = self.persona_panel_ui.PersonaManageView(bot=bot, guild_id=guild_id, invoker_id=5)
        view.selected_mode_key = mode_key
        await view.load()

        interaction = FakeInteraction(user_id=5, guild=FakeGuild(id=guild_id))
        with patch.object(self.persona_panel_ui, "_has_password", AsyncMock(return_value=True)):
            with patch.object(self.persona_panel_ui, "_is_authenticated", AsyncMock(return_value=False)):
                await view.delete_persona(interaction)

        self.assertEqual(len(interaction.response.messages), 1)
        payload = interaction.response.messages[0]
        self.assertIn("Authenticate to delete", payload["content"])
        self.assertIsInstance(payload["view"], self.persona_panel_ui.AuthPromptView)


if __name__ == "__main__":
    unittest.main()
