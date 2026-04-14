import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from utils.persona_panel_ui import (
    PersonaEntry,
    PersonaManageView,
    PersonaPanelState,
    load_persona_panel_state,
)


class PersonaManageCreateTests(unittest.IsolatedAsyncioTestCase):
    async def test_manage_create_reuses_persona_creation_wizard(self) -> None:
        persona_cog = SimpleNamespace(_open_basic_modal=AsyncMock())
        bot = Mock()
        bot.get_cog.return_value = persona_cog

        view = PersonaManageView(bot=bot, guild_id=123, invoker_id=456)
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=123),
            user=SimpleNamespace(
                id=456,
                guild_permissions=SimpleNamespace(manage_guild=True),
            ),
            response=SimpleNamespace(
                send_message=AsyncMock(),
                send_modal=AsyncMock(),
            ),
        )

        await view.create_persona(interaction)

        persona_cog._open_basic_modal.assert_awaited_once_with(interaction)
        interaction.response.send_modal.assert_not_awaited()
        interaction.response.send_message.assert_not_awaited()

    async def test_manage_edit_details_reuses_persona_asset_edit_wizard(self) -> None:
        persona_cog = SimpleNamespace(_open_edit_modal_by_mode_key=AsyncMock())
        bot = Mock()
        bot.get_cog.return_value = persona_cog

        view = PersonaManageView(bot=bot, guild_id=123, invoker_id=456)
        view.state = PersonaPanelState(
            guild_id=123,
            active_mode="mode_default",
            evil_mode_enabled=False,
            entries=(
                PersonaEntry(
                    mode_key="custom_test",
                    display_name="Test Persona",
                    group_label="Custom",
                    description="Custom persona",
                    is_custom=True,
                    bio="bio",
                    aliases=("test",),
                    normal_prompt="normal",
                    evil_prompt="evil",
                    avatar_path="avatar.webp",
                    banner_path="banner.webp",
                ),
            ),
        )
        view.selected_mode_key = "custom_test"

        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=123),
            user=SimpleNamespace(
                id=456,
                guild_permissions=SimpleNamespace(manage_guild=True),
            ),
            response=SimpleNamespace(
                send_message=AsyncMock(),
                send_modal=AsyncMock(),
            ),
        )

        await view.edit_details(interaction)

        persona_cog._open_edit_modal_by_mode_key.assert_awaited_once_with(
            interaction,
            "custom_test",
        )
        interaction.response.send_modal.assert_not_awaited()
        interaction.response.send_message.assert_not_awaited()

    async def test_load_persona_panel_state_decodes_custom_persona_aliases(self) -> None:
        with patch(
            "utils.persona_panel_ui.get_server_mode",
            AsyncMock(return_value="mode_default"),
        ), patch(
            "utils.persona_panel_ui.get_evil_mode",
            AsyncMock(return_value=False),
        ), patch(
            "utils.persona_panel_ui.get_guild_custom_personas",
            AsyncMock(
                return_value=[
                    {
                        "mode_key": "custom_test",
                        "name": "Target",
                        "bio": "bio",
                        "aliases": '["target", "mirror"]',
                        "normal_prompt": "normal",
                        "evil_prompt": None,
                        "avatar_path": None,
                        "banner_path": None,
                    }
                ]
            ),
        ):
            state = await load_persona_panel_state(123)

        custom_entries = [entry for entry in state.entries if entry.mode_key == "custom_test"]
        self.assertEqual(len(custom_entries), 1)
        self.assertEqual(custom_entries[0].aliases, ("target", "mirror"))


if __name__ == "__main__":
    unittest.main()
