"""
Guild configuration commands for API keys and models.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from dotenv.main import parse_stream

from utils.auth import (
    has_password,
    set_password,
    verify_and_create_session,
    is_authenticated,
    cleanup_expired_sessions,
)
from utils.db_handler import (
    get_guild_config,
    update_guild_config,
    clear_guild_keys,
    add_guild_config_audit,
    cleanup_guild_audit,
    get_evil_mode,
    set_evil_mode,
    get_server_mode,
    add_staff_role,
    remove_staff_role,
    get_staff_roles,
    get_mod_log_channel_id,
    set_mod_log_channel_id,
    get_autorole_config,
    set_autorole_id,
    set_autorole_enabled,
    get_welcome_config,
    set_welcome_channel_id,
    set_welcome_enabled,
    set_welcome_message_template,
    set_dm_welcome_message,
    set_dm_welcome_enabled,
    get_dm_welcome_enabled,
    get_url_safety_config,
    set_url_safety_config,
)
from utils.encryption import get_encryption
from utils.guild_ai import (
    RECOMMENDED_GEMINI_MODELS,
    RECOMMENDED_OPENROUTER_MODELS,
)
from utils.api_manager import normalize_openrouter_model, normalize_gemini_model, OPENROUTER_MODELS
from utils.rate_limiter import RateLimiter
from utils.logger import get_logger
from utils.i18n import get_locale_from_interaction, t
from utils.admin_panel_logic import ConfigAction, diff_toggle_states, reconcile_id_lists, requires_auth
from utils.admin_panel_views import AuthRequiredView
from utils.config_panel_ui import (
    ActionMenuView,
    ActionOption,
    ChannelListEditorView,
    FeatureGroupView,
    FeatureOption,
    PaginatedListEditorView,
    SingleChannelPickerView,
    SingleRolePickerView,
)

logger = get_logger(__name__)

ENV_TO_DB = {
    "GEMINI_API_KEY": "gemini_api_key",
    "GEMINI_API_KEY_2": "gemini_api_key_2",
    "GEMINI_API_KEY_3": "gemini_api_key_3",
    "GEMINI_API_KEY_4": "gemini_api_key_4",
    "GEMINI_API_KEY_5": "gemini_api_key_5",
    "GEMINI_TRANSLATE_KEY": "gemini_translate_key",
    "GEMINI_TRANSLATE_KEY_2": "gemini_translate_key_2",
    "GEMINI_TRANSLATE_KEY_3": "gemini_translate_key_3",
    "GEMINI_TRANSLATE_KEY_4": "gemini_translate_key_4",
    "GEMINI_TRANSLATE_KEY_5": "gemini_translate_key_5",
    "GEMINI_SUMMARIZE_KEY": "gemini_summarize_key",
    "GEMINI_SUMMARIZE_KEY_2": "gemini_summarize_key_2",
    "GEMINI_SUMMARIZE_KEY_3": "gemini_summarize_key_3",
    "GEMINI_SUMMARIZE_KEY_4": "gemini_summarize_key_4",
    "GEMINI_SUMMARIZE_KEY_5": "gemini_summarize_key_5",
    "GEMINI_KEY_TYPE": "gemini_key_type",
    "GEMINI_PROFILE_KEY": "gemini_profile_key",
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "OPENROUTER_API_KEY_2": "openrouter_api_key_2",
    "OPENROUTER_API_KEY_3": "openrouter_api_key_3",
    "OPENROUTER_API_KEY_4": "openrouter_api_key_4",
    "OPENROUTER_API_KEY_5": "openrouter_api_key_5",
    "GEMINI_MODEL": "gemini_model",
    "OPENROUTER_MODEL": "openrouter_model",
    "OPENROUTER_FALLBACK_MODELS": "openrouter_fallback_models",
    "BRAVE_API_KEY": "brave_api_key",
    "REPLICATE_API_KEY": "replicate_api_key",
    "TENOR_API_KEY": "tenor_api_key",
    "TENOR_CLIENT_KEY": "tenor_client_key",
    "IMAGE_PROVIDER": "image_provider",
    "IMAGE_MODEL": "image_model",
    "CUSTOM_ENDPOINT_URL": "custom_endpoint_url",
    "CUSTOM_ENDPOINT_API_KEY": "custom_endpoint_api_key",
    "CUSTOM_MODEL_NAME": "custom_model_name",
    "CUSTOM_MODEL_CAPABILITIES": "custom_model_capabilities",
    "CUSTOM_ENDPOINT_ENABLED": "custom_endpoint_enabled",
}

ALLOWED_ENV_KEYS = set(ENV_TO_DB.keys())
KEY_ENV_KEYS = {
    key for key in ENV_TO_DB.keys()
    if key.endswith("_KEY") or "_KEY_" in key or key.endswith("_API_KEY") or "_API_KEY_" in key
}

CATEGORY_FIELDS = {
    "general": [
        "gemini_api_key",
        "gemini_api_key_2",
        "gemini_api_key_3",
        "gemini_api_key_4",
        "gemini_api_key_5",
    ],
    "translate": [
        "gemini_translate_key",
        "gemini_translate_key_2",
        "gemini_translate_key_3",
        "gemini_translate_key_4",
        "gemini_translate_key_5",
    ],
    "summarize": [
        "gemini_summarize_key",
        "gemini_summarize_key_2",
        "gemini_summarize_key_3",
        "gemini_summarize_key_4",
        "gemini_summarize_key_5",
    ],
    "profile": [
        "gemini_profile_key",
    ],
    "uncensored": [
        "openrouter_api_key",
        "openrouter_api_key_2",
        "openrouter_api_key_3",
        "openrouter_api_key_4",
        "openrouter_api_key_5",
    ],
}

CONFIG_TOGGLE_OPTIONS = [
    ("web_search_enabled", "Web search"),
    ("image_gen_enabled", "Image generation"),
    ("sticker_usage_enabled", "Sticker usage"),
    ("emoji_usage_enabled", "Emoji usage"),
    ("pin_message_enabled", "Pin message"),
    ("self_teaching_enabled", "Self teaching"),
    ("youtube_enabled", "YouTube processing"),
    ("profile_peek_enabled", "Profile peek"),
    ("rag_enabled", "RAG retrieval"),
    ("gif_responses_enabled", "GIF responses"),
    ("url_safety_enabled", "URL safety"),
]

FEATURE_GROUPS = {
    "ai_tools": {
        "title": "AI tools",
        "description": "Search, generation, retrieval, and analysis tools.",
        "keys": [
            "web_search_enabled",
            "image_gen_enabled",
            "youtube_enabled",
            "profile_peek_enabled",
            "rag_enabled",
        ],
    },
    "expression_media": {
        "title": "Expression and media",
        "description": "Emoji, stickers, GIFs, and pins.",
        "keys": [
            "sticker_usage_enabled",
            "emoji_usage_enabled",
            "gif_responses_enabled",
            "pin_message_enabled",
        ],
    },
    "memory_learning": {
        "title": "Memory and learning",
        "description": "Persistent learning and teaching features.",
        "keys": [
            "self_teaching_enabled",
        ],
    },
    "conversation": {
        "title": "Conversation",
        "description": "Reply flow and safety capabilities.",
        "keys": [
            "url_safety_enabled",
        ],
    },
}

TOGGLE_LABELS = dict(CONFIG_TOGGLE_OPTIONS)


class InlineAuthService:
    async def verify_password(self, guild_id: int, user_id: int, password: str) -> bool:
        return await verify_and_create_session(guild_id, user_id, password)


class CallbackFormModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str,
        fields: Sequence[dict[str, Any]],
        on_submit_callback: Callable[[discord.Interaction, dict[str, str]], Awaitable[None]],
    ) -> None:
        super().__init__(title=title[:45])
        self._on_submit_callback = on_submit_callback
        self._inputs: dict[str, discord.ui.TextInput] = {}
        for field in fields:
            input_item = discord.ui.TextInput(
                label=field["label"],
                default=field.get("default"),
                placeholder=field.get("placeholder"),
                required=field.get("required", True),
                style=field.get("style", discord.TextStyle.short),
                max_length=field.get("max_length"),
            )
            self._inputs[field["key"]] = input_item
            self.add_item(input_item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        values = {key: item.value for key, item in self._inputs.items()}
        await self._on_submit_callback(interaction, values)


class ConfigToggleView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the command invoker can use this panel.",
                ephemeral=True,
            )
            return False
        return True

    async def build_embed(self) -> discord.Embed:
        config = await get_guild_config(self.guild_id)
        lines = []
        for key, label in CONFIG_TOGGLE_OPTIONS:
            enabled = bool(config.get(key) or 0)
            state = "ON" if enabled else "OFF"
            lines.append(f"{label}: **{state}**")
        embed = discord.Embed(
            title="Config Toggles",
            description="\n".join(lines) if lines else "No toggles available.",
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Select a toggle to switch it on or off.")
        return embed

    @discord.ui.select(
        placeholder="Toggle a feature",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=label, value=key)
            for key, label in CONFIG_TOGGLE_OPTIONS
        ],
    )
    async def toggle_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ):
        key = select.values[0]
        config = await get_guild_config(self.guild_id)
        enabled = bool(config.get(key) or 0)
        await update_guild_config(self.guild_id, {key: 0 if enabled else 1})
        await add_guild_config_audit(self.guild_id, interaction.user.id, f"{key}_ui")
        embed = await self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class ManageConfirmView(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        summary: str,
        on_confirm: Callable[[], Awaitable[str]],
    ):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.summary = summary
        self.on_confirm = on_confirm
        self.completed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the command invoker can confirm this action.",
                ephemeral=True,
            )
            return False
        return True

    def _disable_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.completed:
            await interaction.response.send_message("This confirmation is already resolved.", ephemeral=True)
            return
        self.completed = True
        self._disable_buttons()
        await interaction.response.edit_message(view=self)
        try:
            result = await self.on_confirm()
            await interaction.followup.send(result, ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"Action failed: {exc}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.completed:
            await interaction.response.send_message("This confirmation is already resolved.", ephemeral=True)
            return
        self.completed = True
        self._disable_buttons()
        await interaction.response.edit_message(content=f"Cancelled: {self.summary}", view=self)


class Config(commands.Cog):
    # Main config group
    config = app_commands.Group(name="config", description="Guild configuration")
    
    # Subgroups under /config
    password_group = app_commands.Group(name="password", description="Manage guild config password", parent=config)
    keys_group = app_commands.Group(name="keys", description="View or manage stored API keys", parent=config)
    model_group = app_commands.Group(name="model", description="View or set models", parent=config)
    env_group = app_commands.Group(name="env", description="Upload or retrieve guild env template", parent=config)
    toggle_group = app_commands.Group(name="toggle", description="Toggle guild features", parent=config)
    ai_group = app_commands.Group(name="ai", description="Configure AI reply behavior", parent=config)
    url_safety_group = app_commands.Group(
        name="url_safety",
        description="Configure URL safety checks",
        parent=config,
    )
    custom_endpoint_group = app_commands.Group(
        name="custom_endpoint",
        description="Configure custom OpenAI-compatible endpoint",
        parent=config,
    )
    
    # Standalone top-level groups
    staff_group = app_commands.Group(name="staff", description="Manage bot staff roles")
    modlog_group = app_commands.Group(name="modlog", description="Moderation log channel")
    autorole_group = app_commands.Group(name="autorole", description="Auto-role settings")
    welcome_group = app_commands.Group(name="welcome", description="Welcome message settings")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.encryption = get_encryption()
        self.auth_limiter = RateLimiter(rate=5, per=60)

    async def _rate_limit(self, guild_id: int, user_id: int) -> bool:
        key = f"{guild_id}:{user_id}"
        return await self.auth_limiter.acquire(key)

    async def _require_guild(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(
                t("common.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return False
        return True

    async def _require_auth(self, interaction: discord.Interaction) -> bool:
        if not await is_authenticated(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message(
                t("config.auth.required", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return False
        return True

    async def _send_manage_mod_log(
        self,
        guild: discord.Guild,
        actor: discord.abc.User,
        action: str,
        target: str,
    ) -> None:
        channel_id = await get_mod_log_channel_id(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        embed = discord.Embed(
            title="Management Action",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="Moderator", value=f"{actor} ({actor.id})", inline=True)
        embed.add_field(name="Target", value=target, inline=False)
        try:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            logger.warning("Missing permissions to send manage mod log in %s", guild.name)
        except Exception as exc:
            logger.warning("Failed to send manage mod log in %s: %s", guild.name, exc)

    def _format_key(self, value: Optional[str]) -> str:
        if not value:
            return "Not set"
        try:
            decrypted = self.encryption.decrypt(value)
        except Exception:
            return "Invalid key (decrypt failed)"
        return self.encryption.mask_key(decrypted)

    def _resolve_category_field(self, category: str, slot: int) -> Optional[str]:
        category_key = category.lower().strip()
        if category_key in ("summary", "summarisation", "summarise"):
            category_key = "summarize"
        fields = CATEGORY_FIELDS.get(category_key)
        if not fields:
            return None
        if slot < 1 or slot > len(fields):
            return None
        return fields[slot - 1]

    def _parse_id_list_field(self, raw: Optional[str]) -> list[int]:
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = []
        if not isinstance(data, list):
            return []
        parsed: list[int] = []
        for item in data:
            try:
                parsed.append(int(item))
            except (TypeError, ValueError):
                continue
        return list(dict.fromkeys(parsed))

    async def _set_multi_persona_enabled(self, guild_id: int, user_id: int, enabled: bool) -> dict[str, Any]:
        await update_guild_config(guild_id, {"ai_multi_persona_enabled": int(bool(enabled))})
        await add_guild_config_audit(
            guild_id,
            user_id,
            "ai_multi_persona_enabled_set",
            field="ai_multi_persona_enabled",
            new_value=str(int(bool(enabled))),
        )
        return await get_guild_config(guild_id)

    async def _set_triggered_persona_limit(self, guild_id: int, user_id: int, limit: int) -> dict[str, Any]:
        normalized = max(1, int(limit))
        await update_guild_config(guild_id, {"ai_triggered_persona_limit": normalized})
        await add_guild_config_audit(
            guild_id,
            user_id,
            "ai_triggered_persona_limit_set",
            field="ai_triggered_persona_limit",
            new_value=str(normalized),
        )
        return await get_guild_config(guild_id)

    async def _set_persona_webhooks_enabled(self, guild_id: int, user_id: int, enabled: bool) -> dict[str, Any]:
        await update_guild_config(guild_id, {"ai_persona_webhooks_enabled": int(bool(enabled))})
        await add_guild_config_audit(
            guild_id,
            user_id,
            "ai_persona_webhooks_enabled_set",
            field="ai_persona_webhooks_enabled",
            new_value=str(int(bool(enabled))),
        )
        return await get_guild_config(guild_id)

    async def _send_panel_response(
        self,
        interaction: discord.Interaction,
        *,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        view: Optional[discord.ui.View] = None,
    ) -> None:
        await interaction.response.send_message(
            content=content,
            embed=embed,
            view=view,
            ephemeral=True,
        )
        original_response = getattr(interaction, "original_response", None)
        if view is not None and hasattr(view, "bind_message") and callable(original_response):
            try:
                message = await original_response()
                view.bind_message(message)
            except Exception:
                pass

    async def _auth_status(self, guild_id: int, user_id: int) -> tuple[bool, bool]:
        password_configured = await has_password(guild_id)
        authenticated = await is_authenticated(guild_id, user_id) if password_configured else False
        return password_configured, authenticated

    async def _ensure_action_auth(
        self,
        interaction: discord.Interaction,
        *,
        action: ConfigAction | str,
    ) -> bool:
        action_key = action.value if isinstance(action, ConfigAction) else str(action)
        if not requires_auth(action_key):
            return True
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if not password_configured:
            await interaction.response.send_message(
                "This change requires a config password first. Use `/config password set`, then reopen `/config panel`.",
                ephemeral=True,
            )
            return False
        if not authenticated:
            await interaction.response.send_message(
                "Authentication required. Use `/config auth` and then reopen `/config panel`.",
                ephemeral=True,
            )
            return False
        return True

    def _panel_guidance(self, panel_name: str) -> str:
        return f"Primary admin surface: `{panel_name}`."

    def _manage_panel_hint(self, *commands: str) -> str:
        joined = " or ".join(f"`{command}`" for command in commands if command)
        if not joined:
            return ""
        return f" Use {joined} for future edits."

    def _tools_panel_hint(self) -> str:
        return " Use `/tools manage` or `/config panel` for grouped edits."

    @staticmethod
    def _format_pattern_summary(raw: Optional[str], *, empty: str = "Not set") -> str:
        if not raw:
            return empty
        lines = [line.strip() for line in raw.replace(",", "\n").splitlines() if line.strip()]
        if not lines:
            return empty
        if len(lines) > 4:
            return "\n".join(lines[:4]) + "\n..."
        return "\n".join(lines)

    def _build_config_panel_embed(self, config: dict[str, Any]) -> discord.Embed:
        enabled_count = 0
        for key, _label in CONFIG_TOGGLE_OPTIONS:
            enabled_count += int(bool(config.get(key, 1)))
        embed = discord.Embed(
            title="Config Panel",
            description="Discord-native admin panels for capabilities, AI, routing, and provider settings.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Capabilities", value=f"{enabled_count}/{len(CONFIG_TOGGLE_OPTIONS)} enabled", inline=True)
        embed.add_field(
            name="AI routing",
            value=(
                f"Whitelist: {len(self._parse_id_list_field(config.get('ai_channel_whitelist')))}\n"
                f"Auto channels: {len(self._parse_id_list_field(config.get('ai_auto_channels')))}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Provider overview",
            value=(
                f"Gemini: {self._format_key(config.get('gemini_api_key'))}\n"
                f"OpenRouter: {self._format_key(config.get('openrouter_api_key'))}"
            ),
            inline=False,
        )
        embed.set_footer(text="Choose a section below. High-risk edits ask for auth at submit time.")
        return embed

    def _config_panel_options(self) -> list[ActionOption]:
        return [
            ActionOption("Capabilities", "capabilities", "Grouped bulk toggles for bot features"),
            ActionOption("AI Settings", "ai_settings", "Reply policy, channel routing, streaming, and thought logs"),
            ActionOption("Providers and Models", "providers", "Masked provider overview and secret/model editors"),
            ActionOption("Welcome", "welcome", "Welcome channel and message settings"),
            ActionOption("Autorole", "autorole", "Join role configuration"),
            ActionOption("URL Safety", "url_safety", "Action, allowlist, and blocklist controls"),
            ActionOption("Mod Log", "modlog", "Moderation log channel settings"),
            ActionOption("Staff", "staff", "Bot staff role management"),
        ]

    async def _handle_config_panel_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "capabilities":
            await self._send_capabilities_panel(interaction)
            return
        if value == "ai_settings":
            await self._send_ai_panel(interaction)
            return
        if value == "providers":
            await self._send_provider_panel(interaction)
            return
        if value == "welcome":
            await self._send_welcome_panel(interaction)
            return
        if value == "autorole":
            await self._send_autorole_panel(interaction)
            return
        if value == "url_safety":
            await self._send_url_safety_panel(interaction)
            return
        if value == "modlog":
            await self._send_modlog_panel(interaction)
            return
        if value == "staff":
            await self._send_staff_panel(interaction)
            return
        await interaction.response.send_message("Unknown config section.", ephemeral=True)

    def _feature_group_options(self, group_key: str, config: dict[str, Any]) -> list[FeatureOption]:
        group = FEATURE_GROUPS[group_key]
        return [
            FeatureOption(
                key=key,
                label=TOGGLE_LABELS.get(key, key.replace("_", " ").title()),
                enabled=bool(int(config.get(key, 1))),
            )
            for key in group["keys"]
        ]

    async def _apply_feature_group_changes(
        self,
        guild_id: int,
        user_id: int,
        updates: dict[str, bool],
    ) -> str:
        current = await get_guild_config(guild_id)
        normalized_updates = {key: int(value) for key, value in updates.items()}
        diff = diff_toggle_states(current, normalized_updates)
        if not diff:
            return "No capability changes to save."
        await update_guild_config(guild_id, normalized_updates)
        await add_guild_config_audit(
            guild_id,
            user_id,
            ConfigAction.TOGGLE_CAPABILITY.value,
            summary="Bulk capability update",
            detail={"changes": diff},
        )
        labels = ", ".join(
            f"{TOGGLE_LABELS.get(key, key)}={'ON' if values['new'] else 'OFF'}"
            for key, values in diff.items()
        )
        return f"Saved capability updates: {labels}."

    async def _send_capabilities_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        current_mode = await get_server_mode(interaction.guild.id)
        evil_enabled = await get_evil_mode(interaction.guild.id)
        embed = discord.Embed(
            title="Capabilities",
            description="Grouped bulk toggles replace the old tiny on/off commands.",
            color=discord.Color.green(),
        )
        for group_key, group in FEATURE_GROUPS.items():
            enabled = sum(int(bool(config.get(key, 1))) for key in group["keys"])
            embed.add_field(
                name=group["title"],
                value=f"{group['description']}\nEnabled: {enabled}/{len(group['keys'])}",
                inline=False,
            )
        evil_status = "Disabled in default mode" if current_mode == "mode_default" else ("Enabled" if evil_enabled else "Disabled")
        embed.add_field(
            name="Evil Mode",
            value=f"Current mode: {current_mode}\nStatus: {evil_status}",
            inline=False,
        )
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                *[
                    ActionOption(group["title"], group_key, group["description"])
                    for group_key, group in FEATURE_GROUPS.items()
                ],
                ActionOption("Evil Mode", "evil_mode", "Manage evil mode inside the panel"),
            ],
            on_action=lambda panel_interaction, value: self._handle_capabilities_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_capabilities_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "evil_mode":
            await self._send_evil_mode_panel(interaction)
            return
        await self._send_feature_group_panel(interaction, value)

    async def _send_feature_group_panel(self, interaction: discord.Interaction, group_key: str) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        group = FEATURE_GROUPS[group_key]
        embed = discord.Embed(
            title=group["title"],
            description=group["description"],
            color=discord.Color.green(),
        )
        embed.set_footer(text=self._panel_guidance("/config panel"))
        view = FeatureGroupView(
            invoker_id=interaction.user.id,
            title=group["title"],
            options=self._feature_group_options(group_key, config),
            apply_changes=lambda updates: self._apply_feature_group_changes(
                interaction.guild.id,
                interaction.user.id,
                updates,
            ),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _send_evil_mode_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        current_mode = await get_server_mode(interaction.guild.id)
        enabled = await get_evil_mode(interaction.guild.id)
        status = "Disabled in default mode" if current_mode == "mode_default" else ("Enabled" if enabled else "Disabled")
        embed = discord.Embed(
            title="Evil Mode",
            description="Manage evil mode from the panel instead of a dedicated slash toggle.",
            color=discord.Color.dark_red(),
        )
        embed.add_field(name="Server mode", value=current_mode, inline=False)
        embed.add_field(name="Status", value=status, inline=False)
        embed.set_footer(text=self._panel_guidance("/config toggle manage"))
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Enable", "enable", "Turn evil mode on for the current non-default mode"),
                ActionOption("Disable", "disable", "Turn evil mode off"),
            ],
            on_action=lambda panel_interaction, value: self._handle_evil_mode_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_evil_mode_action(self, interaction: discord.Interaction, value: str) -> None:
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        current_mode = await get_server_mode(interaction.guild.id)
        if current_mode == "mode_default":
            await set_evil_mode(interaction.guild.id, False)
            await interaction.response.send_message("Evil Mode is disabled in default mode.", ephemeral=True)
            return
        if value == "enable":
            await set_evil_mode(interaction.guild.id, True)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "evil_mode_on")
            await interaction.response.send_message("Evil Mode enabled.", ephemeral=True)
            return
        if value == "disable":
            await set_evil_mode(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "evil_mode_off")
            await interaction.response.send_message("Evil Mode disabled.", ephemeral=True)
            return
        await interaction.response.send_message("Unknown evil mode action.", ephemeral=True)

    def _build_ai_embed(self, config: dict[str, Any]) -> discord.Embed:
        whitelist_ids = self._parse_id_list_field(config.get("ai_channel_whitelist"))
        auto_ids = self._parse_id_list_field(config.get("ai_auto_channels"))
        embed = discord.Embed(
            title="AI Settings",
            description="Reply policy, persona queue routing, streaming, and thought/debug logging.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Reply policy",
            value=(
                f"Cooldown: {int(config.get('ai_reply_cooldown_seconds') or 0)}s\n"
                f"Scope: {config.get('ai_reply_cooldown_type') or 'off'}\n"
                f"Self-reply limit: {int(config.get('ai_self_reply_limit') or 3)}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Routing",
            value=(
                f"Whitelist: {len(whitelist_ids)} channel(s)\n"
                f"Auto channels: {len(auto_ids)} channel(s)\n"
                f"Auto threshold: {int(config.get('ai_auto_threshold') or 0)}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Persona runtime",
            value=(
                f"Multi-persona: {bool(config.get('ai_multi_persona_enabled', 0))}\n"
                f"Triggered limit: {int(config.get('ai_triggered_persona_limit') or 1)}\n"
                f"Webhook identity: {bool(config.get('ai_persona_webhooks_enabled', 1))}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Streaming",
            value=(
                f"Enabled: {bool(config.get('ai_streaming_enabled', 1))}\n"
                f"Min flush: {int(config.get('ai_stream_min_flush_chars') or 120)}\n"
                f"Max chars: {int(config.get('ai_stream_max_total_chars') or 6000)}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Thought logs",
            value=(
                f"Level: {config.get('ai_thought_log_level') or 'off'}\n"
                f"Channel: {config.get('ai_thought_channel_id') or 'None'}\n"
                f"Reuse mod-log: {bool(config.get('ai_thought_log_allow_mod_log') or 0)}"
            ),
            inline=False,
        )
        return embed

    def _ai_panel_options(self) -> list[ActionOption]:
        return [
            ActionOption("Reply Policy", "reply_policy", "Cooldown, scope, self-reply, and threshold"),
            ActionOption("Streaming", "streaming", "Streaming toggle and budget controls"),
            ActionOption("Channel Whitelist", "whitelist", "Bulk add/remove/clear AI reply whitelist channels"),
            ActionOption("Auto Channels", "auto_channels", "Bulk add/remove/clear auto-response channels"),
            ActionOption("Thought Logs", "thought_logs", "Thought/debug log channel and level"),
        ]

    async def _send_ai_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=self._ai_panel_options(),
            on_action=lambda panel_interaction, value: self._handle_ai_panel_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=self._build_ai_embed(config), view=view)

    async def _handle_ai_panel_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "reply_policy":
            await interaction.response.send_modal(self._build_ai_reply_modal())
            return
        if value == "streaming":
            await interaction.response.send_modal(self._build_ai_streaming_modal())
            return
        if value == "whitelist":
            await self._send_ai_channel_list_panel(interaction, field="ai_channel_whitelist", title="AI Channel Whitelist")
            return
        if value == "auto_channels":
            await self._send_ai_channel_list_panel(interaction, field="ai_auto_channels", title="AI Auto Channels")
            return
        if value == "thought_logs":
            await self._send_ai_thought_logs_panel(interaction)
            return
        await interaction.response.send_message("Unknown AI settings action.", ephemeral=True)

    def _build_ai_reply_modal(self) -> CallbackFormModal:
        return CallbackFormModal(
            title="AI Reply Policy",
            fields=[
                {"key": "cooldown_seconds", "label": "Cooldown seconds", "default": "0", "required": True},
                {"key": "cooldown_type", "label": "Cooldown scope", "default": "off", "required": True},
                {"key": "self_reply_limit", "label": "Self-reply limit", "default": "3", "required": True},
                {"key": "auto_threshold", "label": "Auto-channel threshold", "default": "0", "required": True},
            ],
            on_submit_callback=lambda modal_interaction, values: self._save_ai_reply_policy(modal_interaction, values),
        )

    async def _save_ai_reply_policy(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        valid_scopes = {"off", "per_user", "per_channel", "server_wide", "strict_server_wide"}
        scope = (values.get("cooldown_type") or "off").strip().lower()
        if scope not in valid_scopes:
            await interaction.response.send_message("Invalid cooldown scope.", ephemeral=True)
            return
        try:
            cooldown = int(values.get("cooldown_seconds") or 0)
            self_reply_limit = int(values.get("self_reply_limit") or 3)
            auto_threshold = int(values.get("auto_threshold") or 0)
        except ValueError:
            await interaction.response.send_message("Reply settings must use numeric values.", ephemeral=True)
            return
        if cooldown < 0 or cooldown > 3600 or self_reply_limit < 1 or self_reply_limit > 20 or auto_threshold < 0 or auto_threshold > 20:
            await interaction.response.send_message("Reply settings are out of range.", ephemeral=True)
            return
        updates = {
            "ai_reply_cooldown_seconds": cooldown,
            "ai_reply_cooldown_type": scope,
            "ai_self_reply_limit": self_reply_limit,
            "ai_auto_threshold": auto_threshold,
        }
        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "ai_settings_save",
            summary="AI reply policy updated",
            detail={"updates": updates},
        )
        await interaction.response.send_message(
            "AI reply policy updated. Use `/config panel` to review the full summary.",
            ephemeral=True,
        )

    def _build_ai_streaming_modal(self) -> CallbackFormModal:
        return CallbackFormModal(
            title="AI Streaming",
            fields=[
                {"key": "enabled", "label": "Enabled (on/off)", "default": "on", "required": True},
                {"key": "min_flush_chars", "label": "Min flush chars", "default": "120", "required": True},
                {"key": "stall_seconds", "label": "Stall seconds", "default": "2.0", "required": True},
                {"key": "min_interval_seconds", "label": "Min interval seconds", "default": "1.0", "required": True},
                {"key": "max_total_chars", "label": "Max total chars", "default": "6000", "required": True},
            ],
            on_submit_callback=lambda modal_interaction, values: self._save_ai_streaming_settings(modal_interaction, values),
        )

    async def _save_ai_streaming_settings(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        enabled_value = (values.get("enabled") or "").strip().lower()
        if enabled_value not in {"on", "off", "enable", "disable", "true", "false"}:
            await interaction.response.send_message("Streaming enabled must be `on` or `off`.", ephemeral=True)
            return
        try:
            min_flush = int(values.get("min_flush_chars") or 120)
            stall_seconds = float(values.get("stall_seconds") or 2.0)
            min_interval = float(values.get("min_interval_seconds") or 1.0)
            max_total_chars = int(values.get("max_total_chars") or 6000)
        except ValueError:
            await interaction.response.send_message("Streaming settings must be numeric.", ephemeral=True)
            return
        updates = {
            "ai_streaming_enabled": int(enabled_value in {"on", "enable", "true"}),
            "ai_stream_min_flush_chars": min_flush,
            "ai_stream_stall_seconds": stall_seconds,
            "ai_stream_min_interval_seconds": min_interval,
            "ai_stream_max_total_chars": max_total_chars,
        }
        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "ai_settings_save",
            summary="AI streaming settings updated",
            detail={"updates": updates},
        )
        await interaction.response.send_message("AI streaming settings updated.", ephemeral=True)

    async def _apply_channel_list_update(
        self,
        guild_id: int,
        user_id: int,
        *,
        field: str,
        add: Optional[list[str]] = None,
        remove: Optional[list[str]] = None,
        clear: bool = False,
        action: str,
    ) -> str:
        config = await get_guild_config(guild_id)
        current_ids = self._parse_id_list_field(config.get(field))
        result = reconcile_id_lists(current_ids, add=add or [], remove=remove or [], clear=clear)
        value = None if not result.updated else json.dumps(result.updated)
        await update_guild_config(guild_id, {field: value})
        await add_guild_config_audit(
            guild_id,
            user_id,
            action,
            field=field,
            summary=f"{field} updated",
            detail={
                "updated": result.updated,
                "added": result.added,
                "removed": result.removed,
                "cleared": result.cleared,
            },
        )
        if clear:
            return f"Cleared all entries from `{field}`."
        if add:
            return f"Added {len(result.added)} channel(s) to `{field}`."
        if remove:
            return f"Removed {len(result.removed)} channel(s) from `{field}`."
        return f"Updated `{field}`."

    async def _send_ai_channel_list_panel(self, interaction: discord.Interaction, *, field: str, title: str) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        channel_ids = self._parse_id_list_field(config.get(field))
        embed = discord.Embed(
            title=title,
            description="Bulk add/remove channels here instead of separate add/remove slash commands.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Current channels",
            value=", ".join(f"<#{channel_id}>" for channel_id in channel_ids) if channel_ids else "None",
            inline=False,
        )
        action_name = "ai_whitelist_save" if field == "ai_channel_whitelist" else "ai_auto_channels_save"
        view = ChannelListEditorView(
            invoker_id=interaction.user.id,
            entries=[str(channel_id) for channel_id in channel_ids],
            apply_add=lambda selected: self._apply_channel_list_update(
                interaction.guild.id,
                interaction.user.id,
                field=field,
                add=selected,
                action=action_name,
            ),
            apply_remove=lambda selected: self._apply_channel_list_update(
                interaction.guild.id,
                interaction.user.id,
                field=field,
                remove=selected,
                action=action_name,
            ),
            apply_clear=lambda: self._apply_channel_list_update(
                interaction.guild.id,
                interaction.user.id,
                field=field,
                clear=True,
                action="clear_all",
            ),
            requires_clear_auth=False,
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _send_ai_thought_logs_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        embed = discord.Embed(
            title="AI Thought Logs",
            description="Set the thought/debug log level or choose a dedicated channel.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Level", value=config.get("ai_thought_log_level") or "off", inline=False)
        embed.add_field(
            name="Dedicated channel",
            value=f"<#{config.get('ai_thought_channel_id')}>" if config.get("ai_thought_channel_id") else "None",
            inline=False,
        )
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Edit Log Settings", "edit", "Level and mod-log reuse"),
                ActionOption("Choose Channel", "set_channel", "Pick the dedicated thought/debug channel"),
                ActionOption("Clear Channel", "clear_channel", "Remove the dedicated thought/debug channel"),
            ],
            on_action=lambda panel_interaction, value: self._handle_ai_thought_logs_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_ai_thought_logs_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "edit":
            modal = CallbackFormModal(
                title="Thought Log Settings",
                fields=[
                    {"key": "level", "label": "Level", "default": "off", "required": True},
                    {"key": "allow_mod_log", "label": "Reuse mod-log (on/off)", "default": "off", "required": True},
                ],
                on_submit_callback=lambda modal_interaction, values: self._save_ai_thought_logs(modal_interaction, values),
            )
            await interaction.response.send_modal(modal)
            return
        if value == "set_channel":
            view = SingleChannelPickerView(
                invoker_id=interaction.user.id,
                placeholder="Select thought/debug channel",
                apply_channel=lambda channel_id: self._set_thought_channel(
                    interaction.guild.id,
                    interaction.user.id,
                    channel_id,
                ),
            )
            await self._send_panel_response(
                interaction,
                content="Choose the dedicated AI thought/debug channel.",
                view=view,
            )
            return
        if value == "clear_channel":
            message = await self._set_thought_channel(interaction.guild.id, interaction.user.id, None)
            await interaction.response.send_message(message, ephemeral=True)
            return
        await interaction.response.send_message("Unknown thought log action.", ephemeral=True)

    async def _save_ai_thought_logs(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        level = (values.get("level") or "off").strip().lower()
        allow_mod_log = (values.get("allow_mod_log") or "off").strip().lower()
        if level not in {"off", "summary", "raw_debug"}:
            await interaction.response.send_message("Use one of: off, summary, raw_debug.", ephemeral=True)
            return
        if allow_mod_log not in {"on", "off", "enable", "disable", "true", "false"}:
            await interaction.response.send_message("Reuse mod-log must be `on` or `off`.", ephemeral=True)
            return
        updates = {
            "ai_thought_log_level": level,
            "ai_thought_log_allow_mod_log": int(allow_mod_log in {"on", "enable", "true"}),
        }
        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "ai_settings_save",
            summary="AI thought log settings updated",
            detail={"updates": updates},
        )
        await interaction.response.send_message("AI thought log settings updated.", ephemeral=True)

    async def _set_thought_channel(self, guild_id: int, user_id: int, channel_id: Optional[int]) -> str:
        await update_guild_config(guild_id, {"ai_thought_channel_id": channel_id})
        await add_guild_config_audit(
            guild_id,
            user_id,
            "ai_settings_save",
            summary="AI thought channel updated",
            target_type="channel",
            target_id=str(channel_id) if channel_id else None,
            detail={"channel_id": channel_id},
        )
        if channel_id:
            return f"AI thought/debug logs will use <#{channel_id}>."
        return "AI thought/debug channel cleared."

    def _build_provider_overview_embed(self, config: dict[str, Any]) -> discord.Embed:
        embed = discord.Embed(
            title="Provider and Model Overview",
            description="Secrets are masked here. Editing secrets and custom endpoints is auth-gated.",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Gemini key", value=self._format_key(config.get("gemini_api_key")), inline=False)
        embed.add_field(name="OpenRouter key", value=self._format_key(config.get("openrouter_api_key")), inline=False)
        embed.add_field(name="Brave key", value=self._format_key(config.get("brave_api_key")), inline=False)
        embed.add_field(
            name="Models",
            value=(
                f"General: {config.get('gemini_model') or 'Not set'}\n"
                f"Translate: {config.get('gemini_translate_model') or 'Not set'}\n"
                f"Summarize: {config.get('gemini_summarize_model') or 'Not set'}\n"
                f"OpenRouter: {config.get('openrouter_model') or 'Not set'}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Custom endpoint",
            value=(
                f"Enabled: {bool(config.get('custom_endpoint_enabled') or 0)}\n"
                f"URL: {config.get('custom_endpoint_url') or 'Not set'}\n"
                f"Model: {config.get('custom_model_name') or 'Not set'}"
            ),
            inline=False,
        )
        return embed

    async def _send_provider_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if password_configured and not authenticated:
            embed = discord.Embed(
                title="Provider and Model Overview",
                description="Authenticate to edit provider secrets, models, and the custom endpoint.",
                color=discord.Color.gold(),
            )
            view = AuthRequiredView(
                invoker_id=interaction.user.id,
                title="Authenticate to edit providers",
                service=InlineAuthService(),
                launch_label="Continue to provider editor",
                modal_factory=lambda: self._build_provider_secret_modal(),
            )
            await self._send_panel_response(interaction, embed=embed, view=view)
            return

        config = await get_guild_config(interaction.guild.id)
        embed = self._build_provider_overview_embed(config)
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Edit Secrets", "edit_secrets", "Gemini, OpenRouter, Brave, Replicate, and Tenor"),
                ActionOption("Edit Models", "edit_models", "General, translate, summarize, and uncensored models"),
                ActionOption("Edit Media Provider", "edit_media", "Image provider and model"),
                ActionOption("Edit Custom Endpoint", "edit_custom_endpoint", "URL, model, capabilities, enabled, API key"),
            ],
            on_action=lambda panel_interaction, value: self._handle_provider_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_provider_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "edit_secrets":
            if not await self._ensure_action_auth(interaction, action=ConfigAction.SET_SECRET):
                return
            await interaction.response.send_modal(self._build_provider_secret_modal())
            return
        if value == "edit_models":
            await interaction.response.send_modal(self._build_provider_model_modal())
            return
        if value == "edit_media":
            await interaction.response.send_modal(self._build_media_provider_modal())
            return
        if value == "edit_custom_endpoint":
            if not await self._ensure_action_auth(interaction, action=ConfigAction.SET_SECRET):
                return
            await interaction.response.send_modal(self._build_custom_endpoint_modal())
            return
        await interaction.response.send_message("Unknown provider action.", ephemeral=True)

    def _build_provider_secret_modal(self) -> CallbackFormModal:
        return CallbackFormModal(
            title="Provider Secrets",
            fields=[
                {"key": "gemini_api_key", "label": "Gemini key", "required": False, "placeholder": "Leave blank to keep; type clear to remove"},
                {"key": "openrouter_api_key", "label": "OpenRouter key", "required": False, "placeholder": "Leave blank to keep; type clear to remove"},
                {"key": "brave_api_key", "label": "Brave key", "required": False, "placeholder": "Leave blank to keep; type clear to remove"},
                {"key": "replicate_api_key", "label": "Replicate key", "required": False, "placeholder": "Leave blank to keep; type clear to remove"},
                {"key": "tenor_api_key", "label": "Tenor key", "required": False, "placeholder": "Leave blank to keep; type clear to remove"},
            ],
            on_submit_callback=lambda interaction, values: self._save_provider_secrets(interaction, values),
        )

    def _parse_secret_modal_updates(self, values: dict[str, str]) -> dict[str, Optional[str]]:
        updates: dict[str, Optional[str]] = {}
        for field, value in values.items():
            cleaned = (value or "").strip()
            if not cleaned:
                continue
            if cleaned.lower() == "clear":
                updates[field] = None
                continue
            updates[field] = self.encryption.encrypt(cleaned)
        return updates

    async def _save_provider_secrets(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        if not await self._ensure_action_auth(interaction, action=ConfigAction.SET_SECRET):
            return
        updates = self._parse_secret_modal_updates(values)
        if not updates:
            await interaction.response.send_message("No provider secret changes submitted.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            ConfigAction.SET_SECRET.value,
            summary="Provider secrets updated",
            detail={"fields": sorted(updates.keys())},
        )
        await interaction.response.send_message("Provider secrets updated.", ephemeral=True)

    def _build_provider_model_modal(self) -> CallbackFormModal:
        return CallbackFormModal(
            title="Provider Models",
            fields=[
                {"key": "general", "label": "General Gemini model", "required": False},
                {"key": "translate", "label": "Translate Gemini model", "required": False},
                {"key": "summarize", "label": "Summarize Gemini model", "required": False},
                {"key": "uncensored", "label": "OpenRouter model", "required": False},
                {"key": "openrouter_fallback_models", "label": "Fallback models (comma-separated)", "required": False},
            ],
            on_submit_callback=lambda interaction, values: self._save_provider_models(interaction, values),
        )

    async def _save_provider_models(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        updates: dict[str, Optional[str]] = {}
        if values.get("general"):
            updates["gemini_model"] = normalize_gemini_model(values["general"].strip()) or values["general"].strip()
        if values.get("translate"):
            updates["gemini_translate_model"] = normalize_gemini_model(values["translate"].strip()) or values["translate"].strip()
        if values.get("summarize"):
            updates["gemini_summarize_model"] = normalize_gemini_model(values["summarize"].strip()) or values["summarize"].strip()
        if values.get("uncensored"):
            updates["openrouter_model"] = normalize_openrouter_model(values["uncensored"].strip()) or values["uncensored"].strip()
        if values.get("openrouter_fallback_models"):
            updates["openrouter_fallback_models"] = values["openrouter_fallback_models"].strip()
        if not updates:
            await interaction.response.send_message("No model changes submitted.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "model_change",
            summary="Provider models updated",
            detail={"updates": updates},
        )
        await interaction.response.send_message("Provider models updated.", ephemeral=True)

    def _build_media_provider_modal(self) -> CallbackFormModal:
        return CallbackFormModal(
            title="Media Provider",
            fields=[
                {"key": "image_provider", "label": "Image provider", "required": False},
                {"key": "image_model", "label": "Image model", "required": False},
                {"key": "tenor_client_key", "label": "Tenor client key", "required": False, "placeholder": "Leave blank to keep; type clear to remove"},
            ],
            on_submit_callback=lambda interaction, values: self._save_media_provider_settings(interaction, values),
        )

    async def _save_media_provider_settings(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        updates: dict[str, Optional[str]] = {}
        if values.get("image_provider"):
            updates["image_provider"] = values["image_provider"].strip()
        if values.get("image_model"):
            updates["image_model"] = values["image_model"].strip()
        if values.get("tenor_client_key"):
            cleaned = values["tenor_client_key"].strip()
            updates["tenor_client_key"] = None if cleaned.lower() == "clear" else cleaned
        if not updates:
            await interaction.response.send_message("No media-provider changes submitted.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "model_change",
            summary="Media provider settings updated",
            detail={"updates": updates},
        )
        await interaction.response.send_message("Media provider settings updated.", ephemeral=True)

    def _build_custom_endpoint_modal(self) -> CallbackFormModal:
        return CallbackFormModal(
            title="Custom Endpoint",
            fields=[
                {"key": "custom_endpoint_url", "label": "Endpoint URL", "required": False},
                {"key": "custom_model_name", "label": "Model name", "required": False},
                {"key": "custom_model_capabilities", "label": "Capabilities", "required": False},
                {"key": "custom_endpoint_enabled", "label": "Enabled (on/off)", "required": False},
                {"key": "custom_endpoint_api_key", "label": "API key", "required": False, "placeholder": "Leave blank to keep; type clear to remove"},
            ],
            on_submit_callback=lambda interaction, values: self._save_custom_endpoint(interaction, values),
        )

    async def _save_custom_endpoint(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        if not await self._ensure_action_auth(interaction, action=ConfigAction.SET_SECRET):
            return
        updates: dict[str, Optional[str]] = {}
        for field in ("custom_endpoint_url", "custom_model_name", "custom_model_capabilities"):
            cleaned = (values.get(field) or "").strip()
            if cleaned:
                updates[field] = cleaned
        enabled_value = (values.get("custom_endpoint_enabled") or "").strip().lower()
        if enabled_value in {"on", "enable", "true", "yes"}:
            updates["custom_endpoint_enabled"] = 1
        elif enabled_value in {"off", "disable", "false", "no"}:
            updates["custom_endpoint_enabled"] = 0
        api_key = (values.get("custom_endpoint_api_key") or "").strip()
        if api_key:
            updates["custom_endpoint_api_key"] = None if api_key.lower() == "clear" else self.encryption.encrypt(api_key)
        if not updates:
            await interaction.response.send_message("No custom endpoint changes submitted.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "provider_endpoint_update",
            summary="Custom endpoint updated",
            detail={"updates": {key: ("***" if "key" in key else value) for key, value in updates.items()}},
        )
        await interaction.response.send_message("Custom endpoint updated.", ephemeral=True)

    async def _send_autorole_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_autorole_config(interaction.guild.id)
        role_id = config.get("autorole_id")
        embed = discord.Embed(
            title="Autorole",
            description="Set or clear the join role from the panel instead of separate slash commands.",
            color=discord.Color.dark_teal(),
        )
        embed.add_field(name="Role", value=f"<@&{role_id}>" if role_id else "None", inline=False)
        embed.add_field(name="Enabled", value=str(bool(config.get("autorole_enabled"))), inline=False)
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Set Role", "set_role", "Choose the role granted on join"),
                ActionOption("Disable Autorole", "disable", "Clear the role and disable autorole"),
            ],
            on_action=lambda panel_interaction, value: self._handle_autorole_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_autorole_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "set_role":
            view = SingleRolePickerView(
                invoker_id=interaction.user.id,
                placeholder="Select autorole",
                apply_role=lambda role_id: self._set_autorole(interaction.guild.id, interaction.user.id, role_id),
            )
            await self._send_panel_response(interaction, content="Choose the autorole to grant on join.", view=view)
            return
        if value == "disable":
            await set_autorole_id(interaction.guild.id, None)
            await set_autorole_enabled(interaction.guild.id, False)
            await add_guild_config_audit(
                interaction.guild.id,
                interaction.user.id,
                "autorole_settings_save",
                summary="Autorole disabled",
            )
            await interaction.response.send_message("Autorole disabled.", ephemeral=True)
            return
        await interaction.response.send_message("Unknown autorole action.", ephemeral=True)

    async def _set_autorole(self, guild_id: int, user_id: int, role_id: int) -> str:
        await set_autorole_id(guild_id, role_id)
        await set_autorole_enabled(guild_id, True)
        await add_guild_config_audit(
            guild_id,
            user_id,
            "autorole_settings_save",
            target_type="role",
            target_id=str(role_id),
            summary="Autorole updated",
        )
        return f"Autorole set to <@&{role_id}>."

    async def _send_welcome_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_welcome_config(interaction.guild.id)
        embed = discord.Embed(
            title="Welcome",
            description="Manage channel welcome flow, templates, DM onboarding, and test sends from one panel.",
            color=discord.Color.orange(),
        )
        channel_id = config.get("welcome_channel_id")
        embed.add_field(name="Channel", value=f"<#{channel_id}>" if channel_id else "None", inline=False)
        embed.add_field(name="Enabled", value="Yes" if config.get("welcome_enabled") else "No", inline=True)
        embed.add_field(name="DM welcome", value="Yes" if config.get("dm_welcome_enabled") else "No", inline=True)
        embed.add_field(
            name="Welcome message",
            value=self._summarize_welcome_text(
                config.get("welcome_message_template"),
                empty="Default AI-generated welcome",
            ),
            inline=False,
        )
        embed.add_field(
            name="DM message",
            value=self._summarize_welcome_text(
                config.get("dm_welcome_message"),
                empty="Not set",
            ),
            inline=False,
        )
        embed.set_footer(text="Standalone welcome commands were folded into `/welcome manage`.")
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Set Channel", "set_channel", "Choose the welcome channel"),
                ActionOption("Toggle Welcome", "toggle_enabled", "Enable or disable welcome messages without clearing the channel"),
                ActionOption("Disable Welcome", "disable", "Clear the welcome channel"),
                ActionOption("Edit Welcome Message", "edit_welcome_message", "Set the public welcome message template"),
                ActionOption("Clear Welcome Message", "clear_welcome_message", "Return to the default welcome message"),
                ActionOption("Edit DM Message", "edit_dm_message", "Set the DM onboarding message"),
                ActionOption("Clear DM Message", "clear_dm_message", "Remove the DM onboarding message"),
                ActionOption("Toggle DM Welcome", "toggle_dm", "Enable or disable DM welcome messages"),
                ActionOption("Send Test Message", "test_message", "Send a welcome preview to the configured channel"),
            ],
            on_action=lambda panel_interaction, value: self._handle_welcome_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_welcome_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "set_channel":
            if not await self._ensure_welcome_auth(interaction):
                return
            view = SingleChannelPickerView(
                invoker_id=interaction.user.id,
                placeholder="Select welcome channel",
                apply_channel=lambda channel_id: self._set_welcome_channel(interaction.guild.id, interaction.user.id, channel_id),
            )
            await self._send_panel_response(interaction, content="Choose the welcome channel.", view=view)
            return
        if value == "toggle_enabled":
            if not await self._ensure_welcome_auth(interaction):
                return
            await self._toggle_welcome_enabled(interaction)
            return
        if value == "disable":
            if not await self._ensure_welcome_auth(interaction):
                return
            await set_welcome_channel_id(interaction.guild.id, None)
            await set_welcome_enabled(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "welcome_settings_save", summary="Welcome disabled")
            await interaction.response.send_message("Welcome messages disabled.", ephemeral=True)
            return
        if value == "edit_welcome_message":
            if not await self._ensure_welcome_auth(interaction):
                return
            config = await get_welcome_config(interaction.guild.id)
            modal = CallbackFormModal(
                title="Welcome Template",
                fields=[
                    {
                        "key": "template",
                        "label": "Welcome template",
                        "default": config.get("welcome_message_template"),
                        "required": False,
                        "style": discord.TextStyle.paragraph,
                        "placeholder": "Use {member}, {member_name}, {member_count}, {member_ordinal}, {guild}.",
                        "max_length": 3500,
                    },
                ],
                on_submit_callback=lambda modal_interaction, values: self._save_welcome_template(modal_interaction, values),
            )
            await interaction.response.send_modal(modal)
            return
        if value == "clear_welcome_message":
            if not await self._ensure_welcome_auth(interaction):
                return
            await self._clear_welcome_template(interaction)
            return
        if value == "edit_dm_message":
            if not await self._ensure_welcome_auth(interaction):
                return
            config = await get_welcome_config(interaction.guild.id)
            modal = CallbackFormModal(
                title="DM Welcome Message",
                fields=[
                    {
                        "key": "message",
                        "label": "DM welcome message",
                        "default": config.get("dm_welcome_message"),
                        "required": False,
                        "style": discord.TextStyle.paragraph,
                        "placeholder": "Use \\n for line breaks if you want to type escapes.",
                        "max_length": 3500,
                    },
                ],
                on_submit_callback=lambda modal_interaction, values: self._save_dm_welcome_message(modal_interaction, values),
            )
            await interaction.response.send_modal(modal)
            return
        if value == "clear_dm_message":
            if not await self._ensure_welcome_auth(interaction):
                return
            await self._clear_dm_welcome_message(interaction)
            return
        if value == "toggle_dm":
            if not await self._ensure_welcome_auth(interaction):
                return
            await self._toggle_dm_welcome(interaction)
            return
        if value == "test_message":
            await self._send_welcome_test(interaction)
            return
        await interaction.response.send_message("Unknown welcome action.", ephemeral=True)

    async def _ensure_welcome_auth(self, interaction: discord.Interaction) -> bool:
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if not password_configured:
            await interaction.response.send_message(
                "This change requires a config password first. Use `/config password set`, then reopen `/welcome manage`.",
                ephemeral=True,
            )
            return False
        if not authenticated:
            await interaction.response.send_message(
                "Authentication required. Use `/config auth` and then reopen `/welcome manage`.",
                ephemeral=True,
            )
            return False
        return True

    @staticmethod
    def _summarize_welcome_text(value: Optional[str], *, empty: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            return empty
        collapsed = " ".join(cleaned.split())
        if len(collapsed) <= 140:
            return collapsed
        return f"{collapsed[:137]}..."

    @staticmethod
    def _normalize_welcome_text(value: Optional[str]) -> str:
        return (value or "").strip().replace("\\n", "\n")

    async def _toggle_welcome_enabled(self, interaction: discord.Interaction) -> None:
        config = await get_welcome_config(interaction.guild.id)
        currently_enabled = bool(config.get("welcome_enabled"))
        channel_id = config.get("welcome_channel_id")
        if not currently_enabled and not channel_id:
            await interaction.response.send_message(
                "Set a welcome channel before enabling welcome messages.",
                ephemeral=True,
            )
            return
        enabled = not currently_enabled
        await set_welcome_enabled(interaction.guild.id, enabled)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "welcome_settings_save",
            summary=f"Welcome {'enabled' if enabled else 'disabled'}",
            detail={"welcome_enabled": enabled},
        )
        await interaction.response.send_message(
            f"Welcome messages {'enabled' if enabled else 'disabled'}.",
            ephemeral=True,
        )

    async def _save_welcome_template(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        cleaned = self._normalize_welcome_text(values.get("template"))
        if not cleaned:
            await interaction.response.send_message("Template cannot be empty.", ephemeral=True)
            return
        if len(cleaned) > 3500:
            await interaction.response.send_message(
                "Template is too long. Please keep it under 3500 characters.",
                ephemeral=True,
            )
            return
        await set_welcome_message_template(interaction.guild.id, cleaned)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "welcome_template_set",
        )
        await interaction.response.send_message("Welcome template updated.", ephemeral=True)

    async def _clear_welcome_template(self, interaction: discord.Interaction) -> None:
        await set_welcome_message_template(interaction.guild.id, None)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "welcome_template_clear",
        )
        await interaction.response.send_message("Welcome template cleared.", ephemeral=True)

    async def _save_dm_welcome_message(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        cleaned = self._normalize_welcome_text(values.get("message"))
        if not cleaned:
            await interaction.response.send_message("Message cannot be empty.", ephemeral=True)
            return
        if len(cleaned) > 3500:
            await interaction.response.send_message(
                "Message is too long. Please keep it under 3500 characters.",
                ephemeral=True,
            )
            return
        await set_dm_welcome_message(interaction.guild.id, cleaned)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "dm_welcome_set",
        )
        await interaction.response.send_message("DM welcome message updated.", ephemeral=True)

    async def _clear_dm_welcome_message(self, interaction: discord.Interaction) -> None:
        await set_dm_welcome_message(interaction.guild.id, None)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "dm_welcome_clear",
        )
        await interaction.response.send_message("DM welcome message cleared.", ephemeral=True)

    async def _toggle_dm_welcome(self, interaction: discord.Interaction) -> None:
        enabled = not await get_dm_welcome_enabled(interaction.guild.id)
        await set_dm_welcome_enabled(interaction.guild.id, enabled)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "welcome_settings_save",
            summary="DM welcome toggle updated",
            detail={"enabled": enabled},
        )
        await interaction.response.send_message(
            f"DM welcome {'enabled' if enabled else 'disabled'}.",
            ephemeral=True,
        )

    async def _send_welcome_test(self, interaction: discord.Interaction) -> None:
        config = await get_welcome_config(interaction.guild.id)
        channel_id = config.get("welcome_channel_id")
        if not channel_id:
            await interaction.response.send_message("No welcome channel set.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Welcome channel not found.", ephemeral=True)
            return
        template = config.get("welcome_message_template")
        if template:
            member_count = int(getattr(interaction.guild, "member_count", 0) or 0)
            ordinal = self._format_ordinal(member_count)
            welcome_text = (
                template
                .replace("@user", interaction.user.mention)
                .replace("{member}", interaction.user.mention)
                .replace("{member_name}", interaction.user.display_name)
                .replace("{member_count}", str(member_count))
                .replace("{member_ordinal}", ordinal)
                .replace("{guild}", interaction.guild.name)
            )
        else:
            welcome_text = f"Test welcome message for {interaction.user.mention}!"
        await channel.send(
            welcome_text,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
        await interaction.response.send_message("Sent a test welcome message.", ephemeral=True)

    @staticmethod
    def _format_ordinal(number: int) -> str:
        if number <= 0:
            return str(number)
        if 10 <= (number % 100) <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
        return f"{number}{suffix}"

    async def _set_welcome_channel(self, guild_id: int, user_id: int, channel_id: int) -> str:
        await set_welcome_channel_id(guild_id, channel_id)
        await set_welcome_enabled(guild_id, True)
        await add_guild_config_audit(
            guild_id,
            user_id,
            "welcome_settings_save",
            target_type="channel",
            target_id=str(channel_id),
            summary="Welcome channel updated",
        )
        return f"Welcome messages will use <#{channel_id}>."

    async def _send_url_safety_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        config = await get_url_safety_config(interaction.guild.id)
        embed = discord.Embed(
            title="URL Safety",
            description="Review URL safety behavior and edit moderation patterns from the panel.",
            color=discord.Color.dark_teal(),
        )
        embed.add_field(
            name="Enabled",
            value="Yes" if config.get("url_safety_enabled") else "No",
            inline=False,
        )
        embed.add_field(
            name="Action",
            value=config.get("url_safety_action") or "warn",
            inline=False,
        )
        embed.add_field(
            name="Allowlist",
            value=self._format_pattern_summary(config.get("url_allowlist")),
            inline=False,
        )
        embed.add_field(
            name="Blocklist",
            value=self._format_pattern_summary(config.get("url_blocklist")),
            inline=False,
        )
        embed.set_footer(text="Toggle URL safety on/off from Capabilities > Conversation.")
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Set Action", "set_action", "Choose warn or delete for flagged links"),
                ActionOption("Edit Allowlist", "edit_allowlist", "Replace allowlist regex patterns"),
                ActionOption("Edit Blocklist", "edit_blocklist", "Replace blocklist regex patterns"),
                ActionOption("Clear Allowlist", "clear_allowlist", "Remove all allowlist patterns"),
                ActionOption("Clear Blocklist", "clear_blocklist", "Remove all blocklist patterns"),
            ],
            on_action=lambda panel_interaction, value: self._handle_url_safety_panel_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_url_safety_panel_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "set_action":
            modal = CallbackFormModal(
                title="URL Safety Action",
                fields=[
                    {
                        "key": "action",
                        "label": "Action (warn/delete)",
                        "default": "warn",
                        "required": True,
                    }
                ],
                on_submit_callback=lambda modal_interaction, values: self._save_url_safety_action(modal_interaction, values),
            )
            await interaction.response.send_modal(modal)
            return
        if value in {"edit_allowlist", "edit_blocklist"}:
            target = "allowlist" if value == "edit_allowlist" else "blocklist"
            modal = CallbackFormModal(
                title=f"URL Safety {target.title()}",
                fields=[
                    {
                        "key": "patterns",
                        "label": f"{target.title()} patterns",
                        "required": False,
                        "style": discord.TextStyle.paragraph,
                        "placeholder": "One pattern per line or comma-separated",
                    }
                ],
                on_submit_callback=lambda modal_interaction, values, target=target: self._save_url_safety_patterns(
                    modal_interaction,
                    target,
                    values,
                ),
            )
            await interaction.response.send_modal(modal)
            return
        if value in {"clear_allowlist", "clear_blocklist"}:
            target = "allowlist" if value == "clear_allowlist" else "blocklist"
            await self._clear_url_safety_patterns(interaction, target)
            return
        await interaction.response.send_message("Unknown URL safety action.", ephemeral=True)

    async def _save_url_safety_action(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if not password_configured:
            await interaction.response.send_message(
                "This change requires a config password first. Use `/config password set`, then reopen `/config panel`.",
                ephemeral=True,
            )
            return
        if not authenticated:
            await interaction.response.send_message(
                "Authentication required. Use `/config auth` and then reopen `/config panel`.",
                ephemeral=True,
            )
            return
        action_value = (values.get("action") or "").strip().lower()
        if action_value not in {"warn", "delete"}:
            await interaction.response.send_message("Action must be `warn` or `delete`.", ephemeral=True)
            return
        await set_url_safety_config(interaction.guild.id, {"url_safety_action": action_value})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "url_safety_action")
        await interaction.response.send_message(
            f"URL safety action set to **{action_value}**.{self._manage_panel_hint('/config panel')}",
            ephemeral=True,
        )

    async def _save_url_safety_patterns(
        self,
        interaction: discord.Interaction,
        target: str,
        values: dict[str, str],
    ) -> None:
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if not password_configured:
            await interaction.response.send_message(
                "This change requires a config password first. Use `/config password set`, then reopen `/config panel`.",
                ephemeral=True,
            )
            return
        if not authenticated:
            await interaction.response.send_message(
                "Authentication required. Use `/config auth` and then reopen `/config panel`.",
                ephemeral=True,
            )
            return
        patterns = (values.get("patterns") or "").strip()
        if not patterns:
            await interaction.response.send_message("No URL safety patterns submitted.", ephemeral=True)
            return
        field = "url_allowlist" if target == "allowlist" else "url_blocklist"
        await set_url_safety_config(interaction.guild.id, {field: patterns})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, f"url_safety_{target}")
        await interaction.response.send_message(
            f"URL {target} updated.{self._manage_panel_hint('/config panel')}",
            ephemeral=True,
        )

    async def _clear_url_safety_patterns(self, interaction: discord.Interaction, target: str) -> None:
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if not password_configured:
            await interaction.response.send_message(
                "This change requires a config password first. Use `/config password set`, then reopen `/config panel`.",
                ephemeral=True,
            )
            return
        if not authenticated:
            await interaction.response.send_message(
                "Authentication required. Use `/config auth` and then reopen `/config panel`.",
                ephemeral=True,
            )
            return
        field = "url_allowlist" if target == "allowlist" else "url_blocklist"
        await set_url_safety_config(interaction.guild.id, {field: None})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, f"url_safety_clear_{target}")
        await interaction.response.send_message(
            f"Cleared URL {target}.{self._manage_panel_hint('/config panel')}",
            ephemeral=True,
        )

    async def _send_modlog_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        channel_id = await get_mod_log_channel_id(interaction.guild.id)
        embed = discord.Embed(
            title="Mod Log",
            description="High-risk routing change. Auth is enforced when you submit changes.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Current channel", value=f"<#{channel_id}>" if channel_id else "None", inline=False)
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Set Channel", "set_channel", "Choose the moderation log channel"),
                ActionOption("Disable Mod Log", "disable", "Clear the moderation log channel"),
            ],
            on_action=lambda panel_interaction, value: self._handle_modlog_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_modlog_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "set_channel":
            view = SingleChannelPickerView(
                invoker_id=interaction.user.id,
                placeholder="Select moderation log channel",
                apply_channel=lambda channel_id: self._set_modlog_channel(interaction, channel_id),
            )
            await self._send_panel_response(interaction, content="Choose the moderation log channel.", view=view)
            return
        if value == "disable":
            if not await self._ensure_action_auth(interaction, action=ConfigAction.UPDATE_MODLOG):
                return
            await set_mod_log_channel_id(interaction.guild.id, None)
            await add_guild_config_audit(
                interaction.guild.id,
                interaction.user.id,
                ConfigAction.UPDATE_MODLOG.value,
                summary="Mod log channel cleared",
            )
            await interaction.response.send_message("Moderation logs disabled.", ephemeral=True)
            return
        await interaction.response.send_message("Unknown mod-log action.", ephemeral=True)

    async def _set_modlog_channel(self, interaction: discord.Interaction, channel_id: int) -> str:
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if not password_configured:
            return "Setting the mod-log channel requires a config password first."
        if not authenticated:
            return "Authentication required. Use `/config auth` and then reopen `/config panel`."
        await set_mod_log_channel_id(interaction.guild.id, channel_id)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            ConfigAction.UPDATE_MODLOG.value,
            target_type="channel",
            target_id=str(channel_id),
            summary="Mod log channel updated",
        )
        return f"Moderation logs will use <#{channel_id}>."

    async def _send_staff_panel(self, interaction: discord.Interaction) -> None:
        if not await self._require_guild(interaction):
            return
        entries = await get_staff_roles(interaction.guild.id)
        embed = discord.Embed(
            title="Staff",
            description="High-risk admin role routing. Auth is enforced when you submit changes.",
            color=discord.Color.dark_gold(),
        )
        if entries:
            lines = [f"Level {level}: <@&{role_id}>" for role_id, level in sorted(entries, key=lambda item: item[1], reverse=True)]
            embed.add_field(name="Configured roles", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Configured roles", value="None", inline=False)
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Add Mod Role", "add_mod", "Add a level-1 staff role"),
                ActionOption("Add Admin Role", "add_admin", "Add a level-2 staff role"),
                ActionOption("Remove Roles", "remove", "Bulk remove configured staff roles"),
            ],
            on_action=lambda panel_interaction, value: self._handle_staff_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_staff_action(self, interaction: discord.Interaction, value: str) -> None:
        if value in {"add_mod", "add_admin"}:
            level = 1 if value == "add_mod" else 2
            view = SingleRolePickerView(
                invoker_id=interaction.user.id,
                placeholder="Select staff role",
                apply_role=lambda role_id: self._add_staff_role_from_panel(interaction, role_id, level),
            )
            await self._send_panel_response(interaction, content="Choose the role to add.", view=view)
            return
        if value == "remove":
            entries = await get_staff_roles(interaction.guild.id)
            role_ids = [str(role_id) for role_id, _level in entries]
            view = PaginatedListEditorView(
                invoker_id=interaction.user.id,
                entries=role_ids,
                apply_remove=lambda selected: self._remove_staff_roles_from_panel(interaction, selected),
                apply_clear=lambda: self._clear_staff_roles_from_panel(interaction),
                requires_clear_auth=True,
                has_auth=lambda: is_authenticated(interaction.guild.id, interaction.user.id),
                request_auth=lambda panel_interaction: panel_interaction.response.send_message(
                    "Authentication required. Use `/config auth` and then reopen `/config panel`.",
                    ephemeral=True,
                ),
            )
            await self._send_panel_response(
                interaction,
                content="Select staff role IDs to remove. Use the summary above to match IDs to levels.",
                view=view,
            )
            return
        await interaction.response.send_message("Unknown staff action.", ephemeral=True)

    async def _add_staff_role_from_panel(self, interaction: discord.Interaction, role_id: int, level: int) -> str:
        password_configured, authenticated = await self._auth_status(interaction.guild.id, interaction.user.id)
        if not password_configured:
            return "Adding staff roles requires a config password first."
        if not authenticated:
            return "Authentication required. Use `/config auth` and then reopen `/config panel`."
        await add_staff_role(interaction.guild.id, role_id, level)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            ConfigAction.UPDATE_STAFF_ROLE.value,
            target_type="role",
            target_id=str(role_id),
            summary=f"Staff role added at level {level}",
            detail={"level": level},
        )
        return f"Added <@&{role_id}> as bot staff (level {level})."

    async def _remove_staff_roles_from_panel(self, interaction: discord.Interaction, selected: list[str]) -> str:
        if not await self._ensure_action_auth(interaction, action=ConfigAction.UPDATE_STAFF_ROLE):
            return "Authentication required. Use `/config auth` and then reopen `/config panel`."
        removed: list[int] = []
        for value in selected:
            try:
                role_id = int(value)
            except ValueError:
                continue
            if await remove_staff_role(interaction.guild.id, role_id):
                removed.append(role_id)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            ConfigAction.UPDATE_STAFF_ROLE.value,
            summary="Staff roles removed",
            detail={"removed": removed},
        )
        return f"Removed {len(removed)} staff role(s)."

    async def _clear_staff_roles_from_panel(self, interaction: discord.Interaction) -> str:
        if not await self._ensure_action_auth(interaction, action=ConfigAction.UPDATE_STAFF_ROLE):
            return "Authentication required. Use `/config auth` and then reopen `/config panel`."
        entries = await get_staff_roles(interaction.guild.id)
        removed: list[int] = []
        for role_id, _level in entries:
            if await remove_staff_role(interaction.guild.id, role_id):
                removed.append(role_id)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            ConfigAction.UPDATE_STAFF_ROLE.value,
            summary="All staff roles cleared",
            detail={"removed": removed},
        )
        return "Cleared all configured staff roles."

    # =========================
    # Password + Auth
    # =========================

    @config.command(name="auth", description="Authenticate for sensitive config operations.")
    @app_commands.checks.has_permissions(administrator=True)
    async def auth(self, interaction: discord.Interaction, password: str):
        if not await self._require_guild(interaction):
            return
        if not await has_password(interaction.guild.id):
            await interaction.response.send_message(
                "No password set yet. Use `/config password set` first.",
                ephemeral=True,
            )
            return
        if not await self._rate_limit(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message(
                "Too many attempts. Try again in 1 minute.",
                ephemeral=True,
            )
            return
        await cleanup_expired_sessions(interaction.guild.id)
        ok = await verify_and_create_session(interaction.guild.id, interaction.user.id, password)
        if not ok:
            await add_guild_config_audit(
                interaction.guild.id,
                interaction.user.id,
                "auth_failure",
            )
            await interaction.response.send_message("Invalid password.", ephemeral=True)
            return
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "auth_success",
        )
        await interaction.response.send_message(
            "Authenticated! Session valid for 15 minutes.",
            ephemeral=True,
        )


    @password_group.command(name="set", description="Set the config password (first time only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def password_set(self, interaction: discord.Interaction, password: str):
        if not await self._require_guild(interaction):
            return
        if await has_password(interaction.guild.id):
            await interaction.response.send_message(
                "Password already set. Use `/config password change`.",
                ephemeral=True,
            )
            return
        if not await self._rate_limit(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message(
                "Too many attempts. Try again in 1 minute.",
                ephemeral=True,
            )
            return
        await set_password(interaction.guild.id, password, interaction.user.id)
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "password_set")
        await interaction.response.send_message("Password set.", ephemeral=True)

    @password_group.command(name="change", description="Change the config password.")
    @app_commands.checks.has_permissions(administrator=True)
    async def password_change(self, interaction: discord.Interaction, old_password: str, new_password: str):
        if not await self._require_guild(interaction):
            return
        if not await self._rate_limit(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message(
                "Too many attempts. Try again in 1 minute.",
                ephemeral=True,
            )
            return
        if not await verify_and_create_session(interaction.guild.id, interaction.user.id, old_password):
            await interaction.response.send_message("Invalid password.", ephemeral=True)
            return
        await set_password(interaction.guild.id, new_password, interaction.user.id)
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "password_change")
        await interaction.response.send_message(
            "Password changed. Please re-authenticate.",
            ephemeral=True,
        )

    @password_group.command(name="reset", description="Reset the config password (owner only).")
    async def password_reset(self, interaction: discord.Interaction, new_password: str):
        if not await self._require_guild(interaction):
            return
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "Only the bot owner can reset passwords.",
                ephemeral=True,
            )
            return
        await set_password(interaction.guild.id, new_password, interaction.user.id)
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "password_reset")
        await interaction.response.send_message("Password reset.", ephemeral=True)

    # =========================
    # Keys
    # =========================

    @keys_group.command(name="manage", description="Open provider, key, and model configuration in the config panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def keys_manage(self, interaction: discord.Interaction):
        await self._send_provider_panel(interaction)

    # =========================
    # Models
    # =========================

    @model_group.command(name="manage", description="Open provider and model configuration in the config panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def model_manage(self, interaction: discord.Interaction):
        await self._send_provider_panel(interaction)

    # =========================
    # Env
    # =========================


    @env_group.command(name="example", description="Send the guild .env.example template.")
    @app_commands.checks.has_permissions(administrator=True)
    async def env_example(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        template_path = Path(__file__).resolve().parent.parent / "guild.env.example"
        if not template_path.exists():
            await interaction.response.send_message(
                "Template file not found on server.",
                ephemeral=True,
            )
            return
        template_text = template_path.read_text(encoding="utf-8")
        message = (
            "Heads up: OpenRouter free keys are often rate-limited or unavailable unless you have very high "
            "priority from OpenRouter. If you want reliable uncensored mode, use premium OpenRouter keys. "
            "For normal mode you can safely use Gemini free keys (add as many free keys as you can from "
            "different accounts for smooth sailing, as long as there is not much image analysis (do vids "
            "if you are really rich lol)). And set an OpenRouter credit limit to $1 in your OpenRouter "
            "settings. About $0.70 can yield ~1500-2500 uncensored messages (varies by model and prompt size).\n"
            "Security note: API keys are stored encrypted and only admins can view them. "
            "The bot creator does not access or use your keys.\n\n"
            "How to upload: 1) Copy the template below into a file named `guild.env` (or any .env name). "
            "2) Fill in your keys and models. 3) Upload it with `/config env upload`.\n"
            "Change \"GEMINI_KEY_TYPE\" to paid if you are using paid keys. It's more reliable."
        )

        await interaction.response.send_message(message, ephemeral=True)

        lines = template_text.strip().splitlines()
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        max_chunk_len = 1800
        for line in lines:
            line_len = len(line) + 1
            if current and current_len + line_len > max_chunk_len:
                chunks.append("\n".join(current))
                current = [line]
                current_len = line_len
            else:
                current.append(line)
                current_len += line_len
        if current:
            chunks.append("\n".join(current))

        total = len(chunks)
        for idx, chunk in enumerate(chunks, start=1):
            label = f"Guild env template (part {idx}/{total}):"
            block = f"{label}\n```\n{chunk}\n```"
            await interaction.followup.send(block, ephemeral=True)

    @env_group.command(name="upload", description="Upload a .env file for this guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def env_upload(self, interaction: discord.Interaction, file: discord.Attachment):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return

        if file.size > 16 * 1024:
            await interaction.response.send_message("File too large (max 16 KB).", ephemeral=True)
            return
        if not file.filename.endswith(".env"):
            await interaction.response.send_message("File must be a .env file.", ephemeral=True)
            return

        raw = await file.read()
        content = raw.decode("utf-8-sig")

        parsed, duplicates, unknown, errors = self._parse_env(content)
        if errors:
            await interaction.response.send_message(
                "Failed to parse .env file:\n" + "\n".join(errors),
                ephemeral=True,
            )
            return
        if duplicates:
            await interaction.response.send_message(
                f"Duplicate keys detected: {', '.join(duplicates)}",
                ephemeral=True,
            )
            return
        if unknown:
            await interaction.response.send_message(
                f"Unknown keys rejected: {', '.join(unknown)}",
                ephemeral=True,
            )
            return

        updates: Dict[str, Optional[str]] = {}
        warnings: List[str] = []
        summary: List[str] = []

        # Normalize and validate
        if "GEMINI_MODEL" in parsed:
            model = parsed["GEMINI_MODEL"] or ""
            normalized = normalize_gemini_model(model) or model
            if normalized and normalized not in RECOMMENDED_GEMINI_MODELS:
                warnings.append("GEMINI_MODEL is not in the recommended list.")
            updates["gemini_model"] = normalized or None
            summary.append(f"GEMINI_MODEL={updates['gemini_model'] or 'CLEARED'}")

        if "GEMINI_KEY_TYPE" in parsed:
            key_type = (parsed["GEMINI_KEY_TYPE"] or "").strip().lower()
            if key_type not in {"free", "paid", ""}:
                warnings.append("GEMINI_KEY_TYPE should be 'free' or 'paid'.")
            updates["gemini_key_type"] = key_type or None
            summary.append(f"GEMINI_KEY_TYPE={updates['gemini_key_type'] or 'CLEARED'}")

        if "OPENROUTER_MODEL" in parsed:
            model = parsed["OPENROUTER_MODEL"] or ""
            normalized = normalize_openrouter_model(model) or model
            if normalized and normalized not in RECOMMENDED_OPENROUTER_MODELS:
                warnings.append("OPENROUTER_MODEL is not in the recommended list.")
            updates["openrouter_model"] = normalized or None
            summary.append(f"OPENROUTER_MODEL={updates['openrouter_model'] or 'CLEARED'}")

        if "OPENROUTER_FALLBACK_MODELS" in parsed:
            raw_models = parsed["OPENROUTER_FALLBACK_MODELS"] or ""
            models = [m.strip() for m in raw_models.split(",") if m.strip()]
            normalized_models: List[str] = []
            unknown_models: List[str] = []
            for item in models:
                normalized = normalize_openrouter_model(item)
                if normalized:
                    normalized_models.append(normalized)
                else:
                    unknown_models.append(item)
            if unknown_models:
                warnings.append(
                    "Unknown OpenRouter fallback models ignored: " + ", ".join(unknown_models)
                )
            updates["openrouter_fallback_models"] = ",".join(normalized_models) if normalized_models else None
            summary.append(
                f"OPENROUTER_FALLBACK_MODELS={updates['openrouter_fallback_models'] or 'CLEARED'}"
            )

        if "IMAGE_PROVIDER" in parsed:
            provider = (parsed["IMAGE_PROVIDER"] or "").strip().lower()
            updates["image_provider"] = provider or None
            summary.append(f"IMAGE_PROVIDER={updates['image_provider'] or 'CLEARED'}")

        if "IMAGE_MODEL" in parsed:
            model = (parsed["IMAGE_MODEL"] or "").strip()
            updates["image_model"] = model or None
            summary.append(f"IMAGE_MODEL={updates['image_model'] or 'CLEARED'}")

        if "CUSTOM_ENDPOINT_URL" in parsed:
            url = (parsed["CUSTOM_ENDPOINT_URL"] or "").strip()
            updates["custom_endpoint_url"] = url or None
            summary.append(f"CUSTOM_ENDPOINT_URL={updates['custom_endpoint_url'] or 'CLEARED'}")

        if "CUSTOM_MODEL_NAME" in parsed:
            model = (parsed["CUSTOM_MODEL_NAME"] or "").strip()
            updates["custom_model_name"] = model or None
            summary.append(f"CUSTOM_MODEL_NAME={updates['custom_model_name'] or 'CLEARED'}")

        if "CUSTOM_MODEL_CAPABILITIES" in parsed:
            caps = (parsed["CUSTOM_MODEL_CAPABILITIES"] or "").strip()
            updates["custom_model_capabilities"] = caps or None
            summary.append(f"CUSTOM_MODEL_CAPABILITIES={updates['custom_model_capabilities'] or 'CLEARED'}")

        if "CUSTOM_ENDPOINT_ENABLED" in parsed:
            enabled_raw = (parsed["CUSTOM_ENDPOINT_ENABLED"] or "").strip().lower()
            if not enabled_raw:
                updates["custom_endpoint_enabled"] = None
            elif enabled_raw in {"1", "true", "yes", "on", "enable"}:
                updates["custom_endpoint_enabled"] = 1
            elif enabled_raw in {"0", "false", "no", "off", "disable"}:
                updates["custom_endpoint_enabled"] = 0
            else:
                warnings.append("CUSTOM_ENDPOINT_ENABLED should be true/false.")
            summary.append(
                f"CUSTOM_ENDPOINT_ENABLED={updates.get('custom_endpoint_enabled', 'CLEARED')}"
            )

        # API keys
        for key, value in parsed.items():
            if key not in KEY_ENV_KEYS:
                continue
            db_field = ENV_TO_DB[key]
            if not value:
                updates[db_field] = None
                summary.append(f"{key}=CLEARED")
                continue
            encrypted = self.encryption.encrypt(value)
            updates[db_field] = encrypted
            summary.append(f"{key}={self.encryption.mask_key(value)}")

        if updates:
            await update_guild_config(interaction.guild.id, updates)
            await add_guild_config_audit(
                interaction.guild.id,
                interaction.user.id,
                "env_upload",
                field="count",
                new_value=str(len(parsed)),
            )

        message = "**Env uploaded successfully.**\n" + "\n".join(summary)
        if warnings:
            message += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)
        await interaction.response.send_message(message, ephemeral=True)

        # Opportunistic cleanup
        await cleanup_guild_audit(interaction.guild.id)

    # =========================
    # Toggle
    # =========================

    @toggle_group.command(name="manage", description="Open capability toggles in the config panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_manage(self, interaction: discord.Interaction):
        await self._send_capabilities_panel(interaction)

    # =========================
    # AI Reply Behavior
    # =========================

    @ai_group.command(name="manage", description="Open AI settings in the config panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_manage(self, interaction: discord.Interaction):
        await self._send_ai_panel(interaction)

    async def _open_config_panel(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=self._config_panel_options(),
            on_action=lambda panel_interaction, value: self._handle_config_panel_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=self._build_config_panel_embed(config), view=view)

    @config.command(name="panel", description="Open the primary Discord-native config panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_panel(self, interaction: discord.Interaction):
        await self._open_config_panel(interaction)

    # =========================
    # URL Safety
    # =========================

    @url_safety_group.command(name="manage", description="Open URL safety settings in the config panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def url_safety_manage(self, interaction: discord.Interaction):
        await self._send_url_safety_panel(interaction)

    def _parse_env(self, content: str) -> Tuple[Dict[str, str], List[str], List[str], List[str]]:
        parsed: Dict[str, str] = {}
        duplicates: List[str] = []
        unknown: List[str] = []
        errors: List[str] = []
        seen: set[str] = set()

        for binding in parse_stream(io.StringIO(content)):
            if binding.error:
                errors.append(f"Parse error on line {binding.original.line}")
                continue
            key = binding.key
            if not key:
                continue
            if key in seen:
                duplicates.append(key)
                continue
            seen.add(key)
            if key not in ALLOWED_ENV_KEYS:
                unknown.append(key)
                continue
            value = binding.value if binding.value is not None else ""
            parsed[key] = value.strip()

        return parsed, duplicates, unknown, errors

    # =========================
    # Custom Endpoint
    # =========================

    @custom_endpoint_group.command(name="manage", description="Open provider and custom endpoint settings in the config panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def custom_endpoint_manage(self, interaction: discord.Interaction):
        await self._send_provider_panel(interaction)

    # =========================
    # Auto-role
    # =========================

    @autorole_group.command(name="manage", description="Open the autorole section inside the config panel UX.")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_manage(self, interaction: discord.Interaction):
        await self._send_autorole_panel(interaction)

    # =========================
    # Welcome
    # =========================

    @welcome_group.command(name="manage", description="Open the welcome section inside the config panel UX.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_manage(self, interaction: discord.Interaction):
        await self._send_welcome_panel(interaction)

    # =========================
    # Staff Roles
    # =========================

    @staff_group.command(name="manage", description="Open the staff section inside the config panel UX.")
    @app_commands.checks.has_permissions(administrator=True)
    async def staff_manage(self, interaction: discord.Interaction):
        await self._send_staff_panel(interaction)

    @staff_group.command(name="add", description="Add a role as bot staff.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role to grant staff access", level="1=Mod, 2=Admin")
    @app_commands.choices(level=[
        app_commands.Choice(name="1 (Mod)", value=1),
        app_commands.Choice(name="2 (Admin)", value=2),
    ])
    async def staff_add(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        level: app_commands.Choice[int],
    ):
        if not await self._require_guild(interaction):
            return
        await add_staff_role(interaction.guild.id, role.id, level.value)
        await interaction.response.send_message(
            f"Added {role.mention} as bot staff (level {level.value}). Use `/config panel` or `/staff manage` for future edits.",
            ephemeral=True,
        )

    @staff_group.command(name="remove", description="Remove a role from bot staff.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role to remove from staff")
    async def staff_remove(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ):
        if not await self._require_guild(interaction):
            return
        removed = await remove_staff_role(interaction.guild.id, role.id)
        if removed:
            await interaction.response.send_message(
                f"Removed {role.mention} from bot staff. Use `/config panel` or `/staff manage` for future edits.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{role.mention} was not configured as bot staff.",
                ephemeral=True,
            )

    @staff_group.command(name="list", description="List configured bot staff roles.")
    @app_commands.checks.has_permissions(administrator=True)
    async def staff_list(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        entries = await get_staff_roles(interaction.guild.id)
        if not entries:
            await interaction.response.send_message("No staff roles configured.", ephemeral=True)
            return
        lines = []
        for role_id, level in sorted(entries, key=lambda item: item[1], reverse=True):
            role = interaction.guild.get_role(role_id)
            role_name = role.mention if role else f"(deleted role {role_id})"
            lines.append(f"Level {level}: {role_name}")
        lines.append(self._manage_panel_hint("/config panel", "/staff manage").strip())
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    # =========================
    # Mod Log
    # =========================

    @modlog_group.command(name="manage", description="Open the mod-log section inside the config panel UX.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modlog_manage(self, interaction: discord.Interaction):
        await self._send_modlog_panel(interaction)

    @modlog_group.command(name="set", description="Set the moderation log channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Channel to receive mod logs")
    async def modlog_set(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        if not await self._require_guild(interaction):
            return
        await set_mod_log_channel_id(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            f"Moderation logs will be sent to {channel.mention}. Use `/config panel` or `/modlog manage` for future edits.",
            ephemeral=True,
        )

    @modlog_group.command(name="clear", description="Disable moderation logs.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modlog_clear(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await set_mod_log_channel_id(interaction.guild.id, None)
        await interaction.response.send_message(
            "Moderation logs disabled. Use `/config panel` or `/modlog manage` for future edits.",
            ephemeral=True,
        )

    @modlog_group.command(name="view", description="View the current mod log channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modlog_view(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        channel_id = await get_mod_log_channel_id(interaction.guild.id)
        if not channel_id:
            await interaction.response.send_message("No mod log channel set.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            await interaction.response.send_message(
                f"Mod logs are posted in {channel.mention}.{self._manage_panel_hint('/config panel', '/modlog manage')}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                (
                    f"Mod log channel set to ID {channel_id}, but I can't access it."
                    f"{self._manage_panel_hint('/config panel', '/modlog manage')}"
                ),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Config(bot))
