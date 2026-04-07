import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))
sys.path.insert(0, str(ROOT))

from tools.contracts import ToolAvailabilityDecision, ToolPolicyMode
sys.modules.setdefault(
    "bcrypt",
    SimpleNamespace(
        gensalt=lambda *args, **kwargs: b"salt",
        hashpw=lambda value, salt: b"hash",
        checkpw=lambda value, hashed: True,
    ),
)

from tests.helpers.discord_fakes import FakeInteraction, FakeMessage
from discord_bot.cogs.config import Config
from discord_bot.cogs.tools_admin import ToolsAdmin
from utils.admin_panel_views import (
    AdminPanelViewBase,
    AuthRequiredView,
    ConfigAuthModal,
    PaginatedListView,
    PostAuthActionView,
)
from utils.config_panel_ui import ActionMenuView, FeatureGroupView


class _StubService:
    def __init__(self) -> None:
        self.auth_verified = False
        self.cleared = False
        self.removals: list[list[str]] = []

    async def verify_password(self, guild_id: int, user_id: int, password: str) -> bool:
        self.auth_verified = password == "correct"
        return self.auth_verified

    async def remove_items(self, selected: list[str]) -> str:
        self.removals.append(selected)
        return f"Removed {len(selected)} item(s)."

    async def clear_items(self) -> str:
        self.cleared = True
        return "Cleared."


class _TestView(AdminPanelViewBase):
    pass


class _FakeBot:
    def __init__(self) -> None:
        self.tree = SimpleNamespace(add_command=lambda *args, **kwargs: None)


class _FakeEncryption:
    def encrypt(self, value: str) -> str:
        return f"enc:{value}"

    def decrypt(self, value: str) -> str:
        return value.removeprefix("enc:")

    def mask_key(self, value: str) -> str:
        return "****" if value else "Not set"


class _FakeAttachment:
    def __init__(self, content: str, filename: str = "guild.env") -> None:
        self._content = content.encode("utf-8")
        self.filename = filename
        self.size = len(self._content)

    async def read(self) -> bytes:
        return self._content


class PanelViewTests(unittest.IsolatedAsyncioTestCase):
    def _make_config_cog(self) -> Config:
        with patch("discord_bot.cogs.config.get_encryption", return_value=_FakeEncryption()):
            return Config(_FakeBot())

    def _make_tools_cog(self) -> ToolsAdmin:
        with patch("discord_bot.cogs.tools_admin.register_builtin_tools", return_value=None):
            return ToolsAdmin(_FakeBot())

    async def test_invoker_only_enforcement(self):
        view = _TestView(invoker_id=11)
        allowed = await view.interaction_check(FakeInteraction(user_id=11))
        denied_interaction = FakeInteraction(user_id=12)
        denied = await view.interaction_check(denied_interaction)

        self.assertTrue(allowed)
        self.assertFalse(denied)
        self.assertEqual(
            denied_interaction.response.messages[-1]["content"],
            "Only the original admin can use this panel.",
        )

    async def test_timeout_disables_children_and_edits_bound_message(self):
        view = _TestView(invoker_id=11, timeout=1)
        button = view.add_timeout_button("Save")
        self.assertFalse(button.disabled)

        message = FakeMessage()
        view.bind_message(message)
        await view.on_timeout()

        self.assertTrue(button.disabled)
        self.assertEqual(message.edits[-1]["content"], "This admin panel expired. Reopen it to continue.")

    async def test_paginated_list_view_supports_page_navigation_and_remove(self):
        service = _StubService()
        view = PaginatedListView(
            invoker_id=11,
            items=["one", "two", "three", "four"],
            page_size=2,
            on_remove=service.remove_items,
            on_clear=service.clear_items,
        )

        await view.next_page(FakeInteraction(user_id=11))
        self.assertEqual(view.page, 2)

        await view.previous_page(FakeInteraction(user_id=11))
        self.assertEqual(view.page, 1)

        view.selected_values = ["one", "two"]
        remove_interaction = FakeInteraction(user_id=11)
        await view.remove_selected(remove_interaction)

        self.assertEqual(service.removals, [["one", "two"]])
        self.assertEqual(remove_interaction.followup.messages[-1]["content"], "Removed 2 item(s).")

    async def test_paginated_list_view_clear_all_requires_auth_when_configured(self):
        service = _StubService()
        view = PaginatedListView(
            invoker_id=11,
            items=["one", "two"],
            page_size=2,
            on_remove=service.remove_items,
            on_clear=service.clear_items,
            clear_requires_auth=True,
            auth_factory=lambda: AuthRequiredView(
                invoker_id=11,
                title="Auth required",
                service=service,
                launch_label="Continue",
                modal_factory=lambda: None,
            ),
        )

        interaction = FakeInteraction(user_id=11)
        await view.clear_all(interaction)

        self.assertIsInstance(interaction.response.messages[-1]["view"], AuthRequiredView)
        self.assertFalse(service.cleared)

    async def test_auth_required_view_launches_auth_modal(self):
        service = _StubService()
        view = AuthRequiredView(
            invoker_id=11,
            title="Auth required",
            service=service,
            launch_label="Continue to provider edit",
            modal_factory=lambda: object(),
        )

        interaction = FakeInteraction(user_id=11)
        await view.authenticate(interaction)

        self.assertIsInstance(interaction.response.modal, ConfigAuthModal)

    async def test_provider_modal_auth_handoff(self):
        service = _StubService()
        view = AuthRequiredView(
            invoker_id=11,
            title="Auth required",
            service=service,
            launch_label="Continue to provider edit",
            modal_factory=lambda: object(),
        )

        launch_interaction = FakeInteraction(user_id=11)
        await view.authenticate(launch_interaction)
        modal = launch_interaction.response.modal
        modal.password_input._value = "correct"

        submit_interaction = FakeInteraction(user_id=11)
        await modal.on_submit(submit_interaction)

        handoff_view = submit_interaction.response.messages[-1]["view"]
        self.assertIsInstance(handoff_view, PostAuthActionView)
        self.assertTrue(service.auth_verified)

        continue_interaction = FakeInteraction(user_id=11)
        await handoff_view.launch(continue_interaction)
        self.assertIsNotNone(continue_interaction.response.modal)

    async def test_config_panel_command_sends_primary_section_menu(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.config.get_guild_config", AsyncMock(return_value={})):
            await cog.config_panel.callback(cog, interaction)

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], ActionMenuView)
        self.assertIn("Config Panel", payload["embed"].title)
        option_values = [option.value for option in payload["view"]._select.options]
        self.assertIn("url_safety", option_values)

    async def test_config_panel_provider_section_uses_auth_handoff(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.config.has_password", AsyncMock(return_value=True)), patch(
            "discord_bot.cogs.config.is_authenticated",
            AsyncMock(return_value=False),
        ):
            await cog._send_provider_panel(interaction)

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], AuthRequiredView)
        self.assertIn("Provider", payload["embed"].title)

    async def test_provider_model_modal_prefills_current_values_and_examples(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)
        config = {
            "gemini_model": "gemini-2.5-flash-lite",
            "gemini_translate_model": "gemini-2.5-flash",
            "gemini_summarize_model": "gemini-2.5-flash-lite",
            "openrouter_model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "openrouter_fallback_models": "nousresearch/hermes-3-llama-3.1-405b:free,mistralai/mistral-small-3.1-24b-instruct:free",
        }

        with patch("discord_bot.cogs.config.get_guild_config", AsyncMock(return_value=config)):
            await cog._handle_provider_action(interaction, "edit_models")

        modal = interaction.response.modal
        self.assertIsNotNone(modal)
        self.assertEqual(modal.title, "Provider Models")
        self.assertEqual(modal._inputs["general"].default, "gemini-2.5-flash-lite")
        self.assertIn("gemini-2.5-flash", modal._inputs["general"].placeholder)
        self.assertEqual(modal._inputs["translate"].default, "gemini-2.5-flash")
        self.assertEqual(
            modal._inputs["uncensored"].default,
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        )
        self.assertIn("venice", modal._inputs["uncensored"].placeholder)
        self.assertEqual(
            modal._inputs["openrouter_fallback_models"].default,
            "nousresearch/hermes-3-llama-3.1-405b:free,mistralai/mistral-small-3.1-24b-instruct:free",
        )
        self.assertIn("hermes", modal._inputs["openrouter_fallback_models"].placeholder)

    async def test_env_upload_preserves_none_as_explicit_openrouter_fallback_disable(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)
        attachment = _FakeAttachment(
            "OPENROUTER_MODEL=deepseek\nOPENROUTER_FALLBACK_MODELS=none\n"
        )

        with patch.object(cog, "_require_guild", AsyncMock(return_value=True)), patch.object(
            cog,
            "_require_auth",
            AsyncMock(return_value=True),
        ), patch(
            "discord_bot.cogs.config.update_guild_config",
            AsyncMock(),
        ) as update_mock, patch(
            "discord_bot.cogs.config.add_guild_config_audit",
            AsyncMock(),
        ), patch(
            "discord_bot.cogs.config.cleanup_guild_audit",
            AsyncMock(),
        ):
            await cog.env_upload.callback(cog, interaction, attachment)

        update_mock.assert_awaited_once_with(
            interaction.guild.id,
            {
                "openrouter_model": "deepseek/deepseek-chat",
                "openrouter_fallback_models": "none",
            },
        )
        self.assertIn(
            "OPENROUTER_FALLBACK_MODELS=none",
            interaction.response.messages[-1]["content"],
        )

    async def test_tools_manage_command_sends_grouped_toggle_panel(self):
        cog = self._make_tools_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.tools_admin.get_guild_config", AsyncMock(return_value={})):
            await cog.tools_manage(interaction)

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], ActionMenuView)
        self.assertIn("Tools Management", payload["embed"].title)

    async def test_tools_manage_group_opens_feature_group_view(self):
        cog = self._make_tools_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.tools_admin.get_guild_config", AsyncMock(return_value={})):
            await cog._send_feature_group_panel(interaction, "ai_tools")

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], FeatureGroupView)
        self.assertIn("AI tools", payload["embed"].title)

    async def test_tools_inspect_reports_denied_reason(self):
        cog = self._make_tools_cog()
        interaction = FakeInteraction(user_id=11)

        decision = ToolAvailabilityDecision(
            tool_id="rest:web_search",
            public_name="web_search",
            category="discovery",
            candidate=True,
            allowed=False,
            effective_policy_mode=ToolPolicyMode.MANUAL_ONLY,
            primary_reason_code="manual_only",
        )

        with patch("discord_bot.cogs.tools_admin.get_guild_config", AsyncMock(return_value={})), patch(
            "discord_bot.cogs.tools_admin.compute_tool_availability_decisions",
            AsyncMock(return_value=[decision]),
        ), patch(
            "discord_bot.cogs.tools_admin.list_tool_policy_rules",
            AsyncMock(return_value=[]),
        ):
            await cog.tools_inspect.callback(cog, interaction, None)

        payload = interaction.response.messages[-1]
        self.assertIn("Tool Inspection", payload["embed"].title)
        denied_field = next(field for field in payload["embed"].fields if field.name == "Denied")
        self.assertIn("manual_only", denied_field.value)

    async def test_tools_policy_set_tool_uses_descriptor_id(self):
        cog = self._make_tools_cog()
        interaction = FakeInteraction(user_id=11)
        fake_descriptor = SimpleNamespace(tool_id="rest:web_search", public_name="web_search")
        fake_rule = SimpleNamespace(subject_id="rest:web_search", policy_mode=SimpleNamespace(value="manual_only"))
        fake_registry = SimpleNamespace(resolve_descriptor=lambda _: fake_descriptor)

        with patch("discord_bot.cogs.tools_admin.get_tool_registry", return_value=fake_registry), patch(
            "discord_bot.cogs.tools_admin.upsert_tool_policy_rule",
            AsyncMock(return_value=fake_rule),
        ):
            await cog.tools_policy_set_tool.callback(cog, interaction, "web_search", "manual_only")

        self.assertIn("web_search", interaction.response.messages[-1]["content"])
        self.assertIn("manual_only", interaction.response.messages[-1]["content"])

    async def test_tools_debug_raw_capture_enable_calls_helper(self):
        cog = self._make_tools_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.tools_admin.set_debug_capture_window", AsyncMock()) as setter:
            await cog.tools_debug_raw_capture_enable.callback(cog, interaction, 5, "investigate")

        setter.assert_awaited_once()
        self.assertIn("Enabled raw capture for 5 minute", interaction.response.messages[-1]["content"])

    async def test_tools_mcp_register_guild_uses_control_plane_helper(self):
        cog = self._make_tools_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.tools_admin.register_guild_mcp_server", AsyncMock()) as registrar:
            await cog.tools_mcp_register_guild.callback(
                cog,
                interaction,
                "guildfake",
                "\"python\" fake_server.py",
                "{\"TOKEN\":\"abc\"}",
            )

        registrar.assert_awaited_once()
        self.assertIn("Registered guild MCP server `guildfake`", interaction.response.messages[-1]["content"])

    async def test_tools_mcp_list_tools_reports_global_and_guild_inventory(self):
        cog = self._make_tools_cog()
        interaction = FakeInteraction(user_id=11)

        with patch(
            "discord_bot.cogs.tools_admin.list_mcp_tools",
            AsyncMock(
                side_effect=[
                    [{"server_slug": "global", "remote_tool_name": "echo", "approved": 1, "public_name": "echo"}],
                    [{"server_slug": "guild", "remote_tool_name": "sum_numbers", "approved": 0, "public_name": None}],
                ]
            ),
        ):
            await cog.tools_mcp_list_tools.callback(cog, interaction)

        payload = interaction.response.messages[-1]
        self.assertEqual(payload["embed"].title, "MCP Tool Inventory")
        values = [field.value for field in payload["embed"].fields]
        self.assertTrue(any("global:echo [approved]" in value for value in values))
        self.assertTrue(any("guild:sum_numbers [pending]" in value for value in values))

    async def test_config_panel_url_safety_section_opens_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch(
            "discord_bot.cogs.config.get_url_safety_config",
            AsyncMock(
                return_value={
                    "url_safety_enabled": 1,
                    "url_safety_action": "warn",
                    "url_allowlist": "^https://trusted.example$",
                    "url_blocklist": "^https://blocked.example$",
                }
            ),
        ):
            await cog._handle_config_panel_action(interaction, "url_safety")

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], ActionMenuView)
        self.assertIn("URL Safety", payload["embed"].title)

    async def test_tools_toggle_shim_points_to_tools_manage(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.config.get_guild_config", AsyncMock(return_value={"web_search_enabled": 1})):
            await cog.toggle_web_search.callback(cog, interaction)

        self.assertIn("/tools manage", interaction.response.messages[-1]["content"])

    async def test_autorole_manage_opens_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch(
            "discord_bot.cogs.config.get_autorole_config",
            AsyncMock(return_value={"autorole_id": None, "autorole_enabled": 0}),
        ):
            await cog.autorole_manage.callback(cog, interaction)

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], ActionMenuView)
        self.assertIn("Autorole", payload["embed"].title)

    async def test_welcome_manage_opens_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch(
            "discord_bot.cogs.config.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_channel_id": None,
                    "welcome_enabled": 0,
                    "dm_welcome_enabled": 0,
                    "welcome_message_template": None,
                }
            ),
        ):
            await cog.welcome_manage.callback(cog, interaction)

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], ActionMenuView)
        self.assertIn("Welcome", payload["embed"].title)

    async def test_staff_manage_opens_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.config.get_staff_roles", AsyncMock(return_value=[])):
            await cog.staff_manage.callback(cog, interaction)

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], ActionMenuView)
        self.assertIn("Staff", payload["embed"].title)

    async def test_modlog_manage_opens_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch("discord_bot.cogs.config.get_mod_log_channel_id", AsyncMock(return_value=None)):
            await cog.modlog_manage.callback(cog, interaction)

        payload = interaction.response.messages[-1]
        self.assertIsInstance(payload["view"], ActionMenuView)
        self.assertIn("Mod Log", payload["embed"].title)

    async def test_autorole_view_points_to_manage_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)
        guild = interaction.guild
        guild.roles[42] = SimpleNamespace(mention="@Members")

        with patch(
            "discord_bot.cogs.config.get_autorole_config",
            AsyncMock(return_value={"autorole_id": 42, "autorole_enabled": 1}),
        ):
            await cog.autorole_view.callback(cog, interaction)

        self.assertIn("/autorole manage", interaction.response.messages[-1]["content"])

    async def test_welcome_view_message_points_to_manage_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)

        with patch(
            "discord_bot.cogs.config.get_welcome_config",
            AsyncMock(return_value={"welcome_message_template": "Welcome, {member}!"}),
        ):
            await cog.welcome_view_message.callback(cog, interaction)

        self.assertIn("/welcome manage", interaction.response.messages[-1]["content"])

    async def test_staff_list_points_to_manage_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)
        guild = interaction.guild
        guild.roles[42] = SimpleNamespace(mention="@Moderators")

        with patch("discord_bot.cogs.config.get_staff_roles", AsyncMock(return_value=[(42, 1)])):
            await cog.staff_list.callback(cog, interaction)

        self.assertIn("/staff manage", interaction.response.messages[-1]["content"])

    async def test_modlog_view_points_to_manage_panel(self):
        cog = self._make_config_cog()
        interaction = FakeInteraction(user_id=11)
        guild = interaction.guild
        guild.channels[55] = SimpleNamespace(mention="#mod-log")

        with patch("discord_bot.cogs.config.get_mod_log_channel_id", AsyncMock(return_value=55)):
            await cog.modlog_view.callback(cog, interaction)

        self.assertIn("/modlog manage", interaction.response.messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
