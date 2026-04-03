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
    manage_group = app_commands.Group(name="manage", description="Manage channels, categories, and roles")
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
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption(group["title"], group_key, group["description"])
                for group_key, group in FEATURE_GROUPS.items()
            ],
            on_action=lambda panel_interaction, value: self._send_feature_group_panel(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

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
            description="Channel and message controls for welcome and DM onboarding.",
            color=discord.Color.orange(),
        )
        channel_id = config.get("welcome_channel_id")
        embed.add_field(name="Channel", value=f"<#{channel_id}>" if channel_id else "None", inline=False)
        embed.add_field(name="Enabled", value=str(bool(config.get("welcome_enabled"))), inline=True)
        embed.add_field(name="DM welcome", value=str(bool(config.get("dm_welcome_enabled"))), inline=True)
        embed.add_field(
            name="Custom message",
            value="Set" if config.get("welcome_message_template") else "Default",
            inline=True,
        )
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=[
                ActionOption("Set Channel", "set_channel", "Choose the welcome channel"),
                ActionOption("Disable Welcome", "disable", "Clear the welcome channel"),
                ActionOption("Edit Messages", "edit_messages", "Welcome template and DM welcome message"),
                ActionOption("Toggle DM Welcome", "toggle_dm", "Enable or disable DM welcome messages"),
            ],
            on_action=lambda panel_interaction, value: self._handle_welcome_action(panel_interaction, value),
        )
        await self._send_panel_response(interaction, embed=embed, view=view)

    async def _handle_welcome_action(self, interaction: discord.Interaction, value: str) -> None:
        if value == "set_channel":
            view = SingleChannelPickerView(
                invoker_id=interaction.user.id,
                placeholder="Select welcome channel",
                apply_channel=lambda channel_id: self._set_welcome_channel(interaction.guild.id, interaction.user.id, channel_id),
            )
            await self._send_panel_response(interaction, content="Choose the welcome channel.", view=view)
            return
        if value == "disable":
            await set_welcome_channel_id(interaction.guild.id, None)
            await set_welcome_enabled(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "welcome_settings_save", summary="Welcome disabled")
            await interaction.response.send_message("Welcome messages disabled.", ephemeral=True)
            return
        if value == "edit_messages":
            modal = CallbackFormModal(
                title="Welcome Messages",
                fields=[
                    {
                        "key": "welcome_message_template",
                        "label": "Welcome template",
                        "required": False,
                        "style": discord.TextStyle.paragraph,
                    },
                    {
                        "key": "dm_welcome_message",
                        "label": "DM welcome message",
                        "required": False,
                        "style": discord.TextStyle.paragraph,
                    },
                ],
                on_submit_callback=lambda modal_interaction, values: self._save_welcome_messages(modal_interaction, values),
            )
            await interaction.response.send_modal(modal)
            return
        if value == "toggle_dm":
            modal = CallbackFormModal(
                title="DM Welcome Toggle",
                fields=[{"key": "enabled", "label": "Enabled (on/off)", "default": "on", "required": True}],
                on_submit_callback=lambda modal_interaction, values: self._save_dm_welcome_toggle(modal_interaction, values),
            )
            await interaction.response.send_modal(modal)
            return
        await interaction.response.send_message("Unknown welcome action.", ephemeral=True)

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

    async def _save_welcome_messages(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        template = (values.get("welcome_message_template") or "").strip()
        dm_message = (values.get("dm_welcome_message") or "").strip()
        if template:
            await set_welcome_message_template(interaction.guild.id, template.replace("\\n", "\n"))
        if dm_message:
            await set_dm_welcome_message(interaction.guild.id, dm_message.replace("\\n", "\n"))
        if not template and not dm_message:
            await interaction.response.send_message("No welcome-message changes submitted.", ephemeral=True)
            return
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "welcome_settings_save",
            summary="Welcome message settings updated",
            detail={"template_updated": bool(template), "dm_updated": bool(dm_message)},
        )
        await interaction.response.send_message("Welcome messages updated.", ephemeral=True)

    async def _save_dm_welcome_toggle(self, interaction: discord.Interaction, values: dict[str, str]) -> None:
        enabled_value = (values.get("enabled") or "").strip().lower()
        if enabled_value not in {"on", "off", "enable", "disable", "true", "false"}:
            await interaction.response.send_message("DM welcome must be `on` or `off`.", ephemeral=True)
            return
        enabled = enabled_value in {"on", "enable", "true"}
        await set_dm_welcome_enabled(interaction.guild.id, enabled)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "welcome_settings_save",
            summary="DM welcome toggle updated",
            detail={"enabled": enabled},
        )
        await interaction.response.send_message(f"DM welcome {'enabled' if enabled else 'disabled'}.", ephemeral=True)

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


    @keys_group.command(name="view", description="View masked API keys.")
    @app_commands.checks.has_permissions(administrator=True)
    async def keys_view(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        embed = discord.Embed(title="Guild API Keys", color=discord.Color.blue())

        def format_group(fields: List[str]) -> str:
            lines = []
            for idx, field in enumerate(fields, start=1):
                value = self._format_key(config.get(field))
                lines.append(f"{idx}. {value}")
            return "\n".join(lines) if lines else "Not set"

        embed.add_field(
            name="Gemini (General)",
            value=format_group(CATEGORY_FIELDS["general"]),
            inline=False,
        )
        embed.add_field(
            name="Gemini (Translate)",
            value=format_group(CATEGORY_FIELDS["translate"]),
            inline=False,
        )
        embed.add_field(
            name="Gemini (Summarize)",
            value=format_group(CATEGORY_FIELDS["summarize"]),
            inline=False,
        )
        embed.add_field(
            name="Gemini (Profile)",
            value=format_group(CATEGORY_FIELDS["profile"]),
            inline=False,
        )
        embed.add_field(
            name="OpenRouter (Uncensored)",
            value=format_group(CATEGORY_FIELDS["uncensored"]),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @keys_group.command(name="clear", description="Clear all stored API keys.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(category="general, translate, summarize, profile, uncensored", slot="Key slot (1-5)")
    async def keys_clear(self, interaction: discord.Interaction, category: Optional[str] = None, slot: Optional[int] = None):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        if not category:
            await clear_guild_keys(interaction.guild.id)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "key_clear", field="all")
            await interaction.response.send_message("All keys cleared.", ephemeral=True)
            return

        if slot is None:
            await interaction.response.send_message("Specify a slot (1-5).", ephemeral=True)
            return

        field = self._resolve_category_field(category, slot)
        if not field:
            await interaction.response.send_message(
                "Invalid category or slot. Categories: general, translate, summarize, profile, uncensored.",
                ephemeral=True,
            )
            return

        await update_guild_config(interaction.guild.id, {field: None})
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "key_clear",
            field=field,
        )
        await interaction.response.send_message(
            f"Cleared key slot {slot} for {category}.",
            ephemeral=True,
        )

    @keys_group.command(name="set", description="Set an API key for a task.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        category="general, translate, summarize, or uncensored",
        slot="Key slot (1-5)",
        key="API key value",
    )
    async def keys_set(self, interaction: discord.Interaction, category: str, slot: int, key: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        field = self._resolve_category_field(category, slot)
        if not field:
            await interaction.response.send_message(
                "Invalid category or slot. Categories: general, translate, summarize, profile, uncensored.",
                ephemeral=True,
            )
            return
        encrypted = self.encryption.encrypt(key)
        await update_guild_config(interaction.guild.id, {field: encrypted})
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "key_set",
            field=field,
            new_value=self.encryption.mask_key(key),
        )
        await interaction.response.send_message(
            f"Key set for {category} slot {slot}: {self.encryption.mask_key(key)}",
            ephemeral=True,
        )

    @keys_set.autocomplete("category")
    async def keys_set_category_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        options = ["general", "translate", "summarize", "profile", "uncensored"]
        current_lower = current.lower().strip()
        matches = [opt for opt in options if current_lower in opt]
        return [app_commands.Choice(name=opt, value=opt) for opt in matches[:25]]

    @keys_set.autocomplete("slot")
    async def keys_set_slot_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[int]]:
        return [app_commands.Choice(name=str(i), value=i) for i in range(1, 6)]

    # =========================
    # Models
    # =========================


    @model_group.command(name="view", description="View current model settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def model_view(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        embed = discord.Embed(
            title="Guild Model Settings",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="GEMINI_MODEL (General)",
            value=config.get("gemini_model") or "Not set",
            inline=False,
        )
        embed.add_field(
            name="GEMINI_MODEL (Translate)",
            value=config.get("gemini_translate_model") or "Not set",
            inline=False,
        )
        embed.add_field(
            name="GEMINI_MODEL (Summarize)",
            value=config.get("gemini_summarize_model") or "Not set",
            inline=False,
        )
        embed.add_field(
            name="OPENROUTER_MODEL (Uncensored)",
            value=config.get("openrouter_model") or "Not set",
            inline=False,
        )
        embed.add_field(
            name="OPENROUTER_FALLBACK_MODELS",
            value=config.get("openrouter_fallback_models") or "Not set",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @model_group.command(name="set", description="Set a model for a provider.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(category="general, translate, summarize, or uncensored", model="Model key or full ID")
    async def model_set(self, interaction: discord.Interaction, category: str, model: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        category = category.lower().strip()
        model = model.strip()

        config = await get_guild_config(interaction.guild.id)
        updates: Dict[str, Optional[str]] = {}
        warnings: List[str] = []

        if category in ("general",):
            normalized = normalize_gemini_model(model) or model
            if normalized not in RECOMMENDED_GEMINI_MODELS:
                warnings.append("GEMINI_MODEL is not in the recommended list.")
            updates["gemini_model"] = normalized
            old_value = config.get("gemini_model")
        elif category in ("translate",):
            normalized = normalize_gemini_model(model) or model
            if normalized not in RECOMMENDED_GEMINI_MODELS:
                warnings.append("GEMINI_TRANSLATE_MODEL is not in the recommended list.")
            updates["gemini_translate_model"] = normalized
            old_value = config.get("gemini_translate_model")
        elif category in ("summarize", "summary", "summarisation", "summarise"):
            normalized = normalize_gemini_model(model) or model
            if normalized not in RECOMMENDED_GEMINI_MODELS:
                warnings.append("GEMINI_SUMMARIZE_MODEL is not in the recommended list.")
            updates["gemini_summarize_model"] = normalized
            old_value = config.get("gemini_summarize_model")
        elif category in ("uncensored", "openrouter"):
            normalized = normalize_openrouter_model(model) or model
            if normalized not in RECOMMENDED_OPENROUTER_MODELS:
                warnings.append("OPENROUTER_MODEL is not in the recommended list.")
            updates["openrouter_model"] = normalized
            old_value = config.get("openrouter_model")
        else:
            await interaction.response.send_message(
                "Unknown category. Use `general`, `translate`, `summarize`, or `uncensored`.",
                ephemeral=True,
            )
            return

        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "model_change",
            field=category,
            old_value=old_value,
            new_value=(
                updates.get("gemini_model")
                or updates.get("gemini_translate_model")
                or updates.get("gemini_summarize_model")
                or updates.get("openrouter_model")
            ),
        )

        message = f"Model updated for {category}."
        if warnings:
            message += "\n" + "\n".join(f"Warning: {w}" for w in warnings)
        await interaction.response.send_message(message, ephemeral=True)

    @model_set.autocomplete("category")
    async def model_set_category_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        options = ["general", "translate", "summarize", "uncensored"]
        current_lower = current.lower().strip()
        matches = [opt for opt in options if current_lower in opt]
        return [app_commands.Choice(name=opt, value=opt) for opt in matches[:25]]

    @model_set.autocomplete("model")
    async def model_set_model_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        category = None
        try:
            category = str(interaction.namespace.category).lower()
        except Exception:
            category = ""
        current_lower = (current or "").lower().strip()

        if category in ("uncensored", "openrouter"):
            options = list(dict.fromkeys(list(OPENROUTER_MODELS.keys()) + RECOMMENDED_OPENROUTER_MODELS))
        else:
            options = RECOMMENDED_GEMINI_MODELS
        matches = [opt for opt in options if current_lower in opt.lower()]
        return [app_commands.Choice(name=opt, value=opt) for opt in matches[:25]]

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


    @toggle_group.command(name="evil", description="Enable or disable evil mode.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_evil(self, interaction: discord.Interaction, state: Optional[str] = None):
        if not await self._require_guild(interaction):
            return
        current_mode = await get_server_mode(interaction.guild.id)
        if current_mode == "mode_default":
            await set_evil_mode(interaction.guild.id, False)
            await interaction.response.send_message(
                "Evil Mode is disabled in default mode.",
                ephemeral=True,
            )
            return
        if not state:
            current = await get_evil_mode(interaction.guild.id)
            status = "ENABLED" if current else "DISABLED"
            await interaction.response.send_message(
                f"Evil Mode is currently **{status}**.",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_evil_mode(interaction.guild.id, True)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "evil_mode_on")
            await interaction.response.send_message("Evil Mode enabled.", ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await set_evil_mode(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "evil_mode_off")
            await interaction.response.send_message("Evil Mode disabled.", ephemeral=True)
        else:
            await interaction.response.send_message("Usage: `/config toggle evil on|off`", ephemeral=True)

    @toggle_group.command(name="autorole", description="Enable or disable auto-role.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_autorole(self, interaction: discord.Interaction, state: Optional[str] = None):
        if not await self._require_guild(interaction):
            return
        if not state:
            config = await get_autorole_config(interaction.guild.id)
            status = "ENABLED" if config.get("autorole_enabled") else "DISABLED"
            await interaction.response.send_message(
                f"Auto-role is currently **{status}**.{self._manage_panel_hint('/config panel', '/autorole manage')}",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_autorole_enabled(interaction.guild.id, True)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "autorole_on")
            await interaction.response.send_message(
                f"Auto-role enabled.{self._manage_panel_hint('/config panel', '/autorole manage')}",
                ephemeral=True,
            )
        elif state_value in {"off", "disable", "false", "no"}:
            await set_autorole_enabled(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "autorole_off")
            await interaction.response.send_message(
                f"Auto-role disabled.{self._manage_panel_hint('/config panel', '/autorole manage')}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Usage: `/config toggle autorole on|off`.{self._manage_panel_hint('/config panel', '/autorole manage')}",
                ephemeral=True,
            )

    @toggle_group.command(name="welcome", description="Enable or disable welcome messages.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_welcome(self, interaction: discord.Interaction, state: Optional[str] = None):
        if not await self._require_guild(interaction):
            return
        if not state:
            config = await get_welcome_config(interaction.guild.id)
            status = "ENABLED" if config.get("welcome_enabled") else "DISABLED"
            await interaction.response.send_message(
                f"Welcome messages are currently **{status}**.{self._manage_panel_hint('/config panel', '/welcome manage')}",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_welcome_enabled(interaction.guild.id, True)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "welcome_on")
            await interaction.response.send_message(
                f"Welcome messages enabled.{self._manage_panel_hint('/config panel', '/welcome manage')}",
                ephemeral=True,
            )
        elif state_value in {"off", "disable", "false", "no"}:
            await set_welcome_enabled(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "welcome_off")
            await interaction.response.send_message(
                f"Welcome messages disabled.{self._manage_panel_hint('/config panel', '/welcome manage')}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Usage: `/config toggle welcome on|off`.{self._manage_panel_hint('/config panel', '/welcome manage')}",
                ephemeral=True,
            )

    async def _toggle_feature_flag(
        self,
        interaction: discord.Interaction,
        flag_name: str,
        label: str,
        state: Optional[str],
    ) -> None:
        if not await self._require_guild(interaction):
            return
        if not state:
            config = await get_guild_config(interaction.guild.id)
            enabled = bool(config.get(flag_name) or 0)
            status = "ENABLED" if enabled else "DISABLED"
            await interaction.response.send_message(
                f"{label} is currently **{status}**.{self._tools_panel_hint()}",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await update_guild_config(interaction.guild.id, {flag_name: 1})
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, f"{flag_name}_on")
            await interaction.response.send_message(f"{label} enabled.{self._tools_panel_hint()}", ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await update_guild_config(interaction.guild.id, {flag_name: 0})
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, f"{flag_name}_off")
            await interaction.response.send_message(f"{label} disabled.{self._tools_panel_hint()}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Usage: `on` or `off`.{self._tools_panel_hint()}", ephemeral=True)

    @toggle_group.command(name="web_search", description="Enable or disable web search tools.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_web_search(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "web_search_enabled", "Web search", state)

    @toggle_group.command(name="image_gen", description="Enable or disable image generation.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_image_gen(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "image_gen_enabled", "Image generation", state)

    @toggle_group.command(name="stickers", description="Enable or disable sticker usage.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_stickers(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "sticker_usage_enabled", "Sticker usage", state)

    @toggle_group.command(name="emojis", description="Enable or disable emoji usage.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_emojis(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "emoji_usage_enabled", "Emoji usage", state)

    @toggle_group.command(name="pin_message", description="Enable or disable AI pinning.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_pin_message(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "pin_message_enabled", "Pin message", state)

    @toggle_group.command(name="self_teaching", description="Enable or disable self-teaching.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_self_teaching(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "self_teaching_enabled", "Self teaching", state)

    @toggle_group.command(name="youtube", description="Enable or disable YouTube processing.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_youtube(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "youtube_enabled", "YouTube processing", state)

    @toggle_group.command(name="profile_peek", description="Enable or disable profile picture analysis.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_profile_peek(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "profile_peek_enabled", "Profile peek", state)

    @toggle_group.command(name="rag", description="Enable or disable local RAG retrieval.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_rag(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "rag_enabled", "RAG retrieval", state)

    @toggle_group.command(name="gif_responses", description="Enable or disable GIF replies.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_gif_responses(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "gif_responses_enabled", "GIF responses", state)

    @toggle_group.command(name="url_safety", description="Enable or disable URL safety checks.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_url_safety(self, interaction: discord.Interaction, state: Optional[str] = None):
        await self._toggle_feature_flag(interaction, "url_safety_enabled", "URL safety", state)

    # =========================
    # AI Reply Behavior
    # =========================

    @ai_group.command(name="view", description="View AI reply gating settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_view(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return

        config = await get_guild_config(interaction.guild.id)
        whitelist_ids = self._parse_id_list_field(config.get("ai_channel_whitelist"))
        auto_ids = self._parse_id_list_field(config.get("ai_auto_channels"))
        cooldown = int(config.get("ai_reply_cooldown_seconds") or 0)
        cooldown_type = str(config.get("ai_reply_cooldown_type") or "per_user")
        self_reply_limit = int(config.get("ai_self_reply_limit") or 3)
        multi_persona_enabled = bool(config.get("ai_multi_persona_enabled") or 0)
        triggered_persona_limit = int(config.get("ai_triggered_persona_limit") or 1)
        persona_webhooks_enabled = bool(config.get("ai_persona_webhooks_enabled", 1))
        auto_threshold = int(config.get("ai_auto_threshold") or 0)
        streaming_enabled = bool(config.get("ai_streaming_enabled", 1))
        stream_min_flush_chars = int(config.get("ai_stream_min_flush_chars") or 120)
        stream_stall_seconds = float(config.get("ai_stream_stall_seconds") or 2.0)
        stream_min_interval_seconds = float(config.get("ai_stream_min_interval_seconds") or 1.0)
        stream_max_messages = int(config.get("ai_stream_max_messages") or 6)
        stream_max_total_chars = int(config.get("ai_stream_max_total_chars") or 6000)
        thought_channel_id = config.get("ai_thought_channel_id")
        thought_log_level = str(config.get("ai_thought_log_level") or "off")
        thought_log_allow_mod_log = bool(config.get("ai_thought_log_allow_mod_log") or 0)

        def _render_channels(ids: list[int]) -> str:
            if not ids:
                return "None"
            return ", ".join(f"<#{channel_id}>" for channel_id in ids)

        embed = discord.Embed(title="AI Reply Settings", color=discord.Color.blue())
        embed.add_field(name="Reply Cooldown (seconds)", value=str(cooldown), inline=False)
        embed.add_field(name="Reply Cooldown Scope", value=cooldown_type, inline=False)
        embed.add_field(name="Self-reply chain limit", value=str(self_reply_limit), inline=False)
        embed.add_field(
            name="Persona runtime",
            value=(
                f"multi_persona={multi_persona_enabled}, "
                f"triggered_limit={triggered_persona_limit}, "
                f"webhook_identity={persona_webhooks_enabled}"
            ),
            inline=False,
        )
        embed.add_field(name="Channel whitelist", value=_render_channels(whitelist_ids), inline=False)
        embed.add_field(name="Auto channels", value=_render_channels(auto_ids), inline=False)
        embed.add_field(name="Auto threshold", value=str(auto_threshold), inline=False)
        embed.add_field(name="Streaming enabled", value=str(streaming_enabled), inline=False)
        embed.add_field(
            name="Stream budget",
            value=(
                f"min_flush_chars={stream_min_flush_chars}, "
                f"stall={stream_stall_seconds:.1f}s, "
                f"min_interval={stream_min_interval_seconds:.1f}s, "
                f"max_messages={stream_max_messages}, "
                f"max_total_chars={stream_max_total_chars}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Thought log",
            value=(
                f"level={thought_log_level}, "
                f"channel={'<#{0}>'.format(thought_channel_id) if thought_channel_id else 'None'}, "
                f"allow_mod_log_reuse={thought_log_allow_mod_log}"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ai_group.command(name="cooldown", description="Set AI reply cooldown in seconds.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(seconds="0 disables cooldown")
    async def ai_set_cooldown(self, interaction: discord.Interaction, seconds: int):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        if seconds < 0 or seconds > 3600:
            await interaction.response.send_message("Use a value between 0 and 3600.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, {"ai_reply_cooldown_seconds": int(seconds)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_reply_cooldown_seconds_set")
        await interaction.response.send_message(f"AI reply cooldown set to {seconds}s.", ephemeral=True)

    @ai_group.command(name="cooldown_type", description="Set AI reply cooldown scope.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        scope="off, per_user, per_channel, server_wide, strict_server_wide",
    )
    async def ai_set_cooldown_type(self, interaction: discord.Interaction, scope: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        normalized = (scope or "").strip().lower()
        valid = {"off", "per_user", "per_channel", "server_wide", "strict_server_wide"}
        if normalized not in valid:
            await interaction.response.send_message(
                "Use one of: off, per_user, per_channel, server_wide, strict_server_wide.",
                ephemeral=True,
            )
            return
        await update_guild_config(interaction.guild.id, {"ai_reply_cooldown_type": normalized})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_reply_cooldown_type_set")
        await interaction.response.send_message(
            f"AI reply cooldown scope set to `{normalized}`.",
            ephemeral=True,
        )

    @ai_group.command(name="self_reply_limit", description="Set max self-reply chain depth.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(limit="Maximum consecutive reply chain depth (1-20)")
    async def ai_set_self_reply_limit(self, interaction: discord.Interaction, limit: int):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        if limit < 1 or limit > 20:
            await interaction.response.send_message("Use a value between 1 and 20.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, {"ai_self_reply_limit": int(limit)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_self_reply_limit_set")
        await interaction.response.send_message(f"AI self-reply chain limit set to {limit}.", ephemeral=True)

    @ai_group.command(name="auto_threshold", description="Set message count threshold for auto channels.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(threshold="0 disables auto-channel threshold behavior")
    async def ai_set_auto_threshold(self, interaction: discord.Interaction, threshold: int):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        if threshold < 0 or threshold > 20:
            await interaction.response.send_message("Use a value between 0 and 20.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, {"ai_auto_threshold": int(threshold)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_auto_threshold_set")
        await interaction.response.send_message(f"AI auto-channel threshold set to {threshold}.", ephemeral=True)

    @ai_group.command(name="whitelist_add", description="Add a channel to the AI reply whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_whitelist_add(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        current = self._parse_id_list_field(config.get("ai_channel_whitelist"))
        if channel.id not in current:
            current.append(channel.id)
        await update_guild_config(interaction.guild.id, {"ai_channel_whitelist": json.dumps(current)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_whitelist_add")
        await interaction.response.send_message(f"Added {channel.mention} to AI reply whitelist.", ephemeral=True)

    @ai_group.command(name="whitelist_remove", description="Remove a channel from the AI reply whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_whitelist_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        current = self._parse_id_list_field(config.get("ai_channel_whitelist"))
        current = [channel_id for channel_id in current if channel_id != channel.id]
        await update_guild_config(interaction.guild.id, {"ai_channel_whitelist": json.dumps(current)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_whitelist_remove")
        await interaction.response.send_message(f"Removed {channel.mention} from AI reply whitelist.", ephemeral=True)

    @ai_group.command(name="whitelist_clear", description="Clear the AI reply whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_whitelist_clear(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await update_guild_config(interaction.guild.id, {"ai_channel_whitelist": None})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_whitelist_clear")
        await interaction.response.send_message("AI reply whitelist cleared.", ephemeral=True)

    @ai_group.command(name="auto_channel_add", description="Add a channel to AI auto-response channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_auto_channel_add(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        current = self._parse_id_list_field(config.get("ai_auto_channels"))
        if channel.id not in current:
            current.append(channel.id)
        await update_guild_config(interaction.guild.id, {"ai_auto_channels": json.dumps(current)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_auto_channel_add")
        await interaction.response.send_message(f"Added {channel.mention} to AI auto channels.", ephemeral=True)

    @ai_group.command(name="auto_channel_remove", description="Remove a channel from AI auto-response channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_auto_channel_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        current = self._parse_id_list_field(config.get("ai_auto_channels"))
        current = [channel_id for channel_id in current if channel_id != channel.id]
        await update_guild_config(interaction.guild.id, {"ai_auto_channels": json.dumps(current)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_auto_channel_remove")
        await interaction.response.send_message(f"Removed {channel.mention} from AI auto channels.", ephemeral=True)

    @ai_group.command(name="streaming", description="Enable or disable streamed AI replies.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off")
    async def ai_set_streaming(self, interaction: discord.Interaction, state: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        normalized = (state or "").strip().lower()
        if normalized not in {"on", "off", "enable", "disable", "true", "false"}:
            await interaction.response.send_message("Use `on` or `off`.", ephemeral=True)
            return
        enabled = normalized in {"on", "enable", "true"}
        await update_guild_config(interaction.guild.id, {"ai_streaming_enabled": int(enabled)})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_streaming_enabled_set")
        await interaction.response.send_message(
            f"AI streaming {'enabled' if enabled else 'disabled'}.",
            ephemeral=True,
        )

    @ai_group.command(name="stream_budget", description="Set streaming flush and send-budget limits.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        min_flush_chars="Minimum buffered characters before soft flush (20-1000)",
        stall_seconds="Fallback stall flush timer in seconds (1-30)",
        min_interval_seconds="Minimum seconds between sends (0-10)",
        max_messages="Maximum streamed Discord messages per turn (1-20)",
        max_total_chars="Maximum total visible characters per turn (500-20000)",
    )
    async def ai_set_stream_budget(
        self,
        interaction: discord.Interaction,
        min_flush_chars: int,
        stall_seconds: float,
        min_interval_seconds: float,
        max_messages: int,
        max_total_chars: int,
    ):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        if not 20 <= min_flush_chars <= 1000:
            await interaction.response.send_message("min_flush_chars must be between 20 and 1000.", ephemeral=True)
            return
        if not 1 <= stall_seconds <= 30:
            await interaction.response.send_message("stall_seconds must be between 1 and 30.", ephemeral=True)
            return
        if not 0 <= min_interval_seconds <= 10:
            await interaction.response.send_message("min_interval_seconds must be between 0 and 10.", ephemeral=True)
            return
        if not 1 <= max_messages <= 20:
            await interaction.response.send_message("max_messages must be between 1 and 20.", ephemeral=True)
            return
        if not 500 <= max_total_chars <= 20000:
            await interaction.response.send_message("max_total_chars must be between 500 and 20000.", ephemeral=True)
            return
        await update_guild_config(
            interaction.guild.id,
            {
                "ai_stream_min_flush_chars": int(min_flush_chars),
                "ai_stream_stall_seconds": float(stall_seconds),
                "ai_stream_min_interval_seconds": float(min_interval_seconds),
                "ai_stream_max_messages": int(max_messages),
                "ai_stream_max_total_chars": int(max_total_chars),
            },
        )
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_stream_budget_set")
        await interaction.response.send_message("AI streaming budget updated.", ephemeral=True)

    @ai_group.command(name="thought_channel", description="Set or clear the dedicated AI thought/debug channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Leave empty to clear the dedicated thought channel")
    async def ai_set_thought_channel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await update_guild_config(
            interaction.guild.id,
            {"ai_thought_channel_id": channel.id if channel else None},
        )
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_thought_channel_set")
        if channel:
            await interaction.response.send_message(
                f"AI thought/debug logs will use {channel.mention}.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("AI thought/debug channel cleared.", ephemeral=True)

    @ai_group.command(name="thought_level", description="Set AI thought/debug logging level.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(level="off, summary, raw_debug")
    async def ai_set_thought_level(self, interaction: discord.Interaction, level: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        normalized = (level or "").strip().lower()
        if normalized not in {"off", "summary", "raw_debug"}:
            await interaction.response.send_message("Use one of: off, summary, raw_debug.", ephemeral=True)
            return
        await update_guild_config(interaction.guild.id, {"ai_thought_log_level": normalized})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "ai_thought_log_level_set")
        await interaction.response.send_message(f"AI thought log level set to `{normalized}`.", ephemeral=True)

    @ai_group.command(name="thought_modlog", description="Allow or deny fallback reuse of the mod-log for AI thought logs.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off")
    async def ai_set_thought_modlog(self, interaction: discord.Interaction, state: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        normalized = (state or "").strip().lower()
        if normalized not in {"on", "off", "enable", "disable", "true", "false"}:
            await interaction.response.send_message("Use `on` or `off`.", ephemeral=True)
            return
        enabled = normalized in {"on", "enable", "true"}
        await update_guild_config(interaction.guild.id, {"ai_thought_log_allow_mod_log": int(enabled)})
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "ai_thought_log_allow_mod_log_set",
        )
        await interaction.response.send_message(
            f"AI thought log mod-log reuse {'enabled' if enabled else 'disabled'}.",
            ephemeral=True,
        )

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

    @config.command(name="ui", description="Open a quick toggle UI panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_ui(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await interaction.response.send_message(
            "Use `/config panel` for the new admin UX. `/config ui` is now a legacy shortcut.",
            ephemeral=True,
        )

    # =========================
    # URL Safety
    # =========================

    @url_safety_group.command(name="view", description="View URL safety settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def url_safety_view(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        config = await get_url_safety_config(interaction.guild.id)

        def format_list(raw: Optional[str]) -> str:
            if not raw:
                return "Not set"
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            if len(lines) > 6:
                return "\n".join(lines[:6]) + "\n..."
            return "\n".join(lines)

        embed = discord.Embed(title="URL Safety Settings", color=discord.Color.blue())
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
            name="Allowlist (regex)",
            value=format_list(config.get("url_allowlist")),
            inline=False,
        )
        embed.add_field(
            name="Blocklist (regex)",
            value=format_list(config.get("url_blocklist")),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @url_safety_group.command(name="action", description="Set URL safety action (warn/delete).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(action="warn or delete")
    async def url_safety_action(self, interaction: discord.Interaction, action: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        action_value = (action or "").strip().lower()
        if action_value not in {"warn", "delete"}:
            await interaction.response.send_message("Action must be `warn` or `delete`.", ephemeral=True)
            return
        await set_url_safety_config(interaction.guild.id, {"url_safety_action": action_value})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "url_safety_action")
        await interaction.response.send_message(
            f"URL safety action set to **{action_value}**.",
            ephemeral=True,
        )

    @url_safety_group.command(name="allowlist", description="Set URL allowlist regex patterns.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(patterns="One pattern per line or comma-separated")
    async def url_safety_allowlist(self, interaction: discord.Interaction, patterns: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_url_safety_config(interaction.guild.id, {"url_allowlist": patterns.strip()})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "url_safety_allowlist")
        await interaction.response.send_message("URL allowlist updated.", ephemeral=True)

    @url_safety_group.command(name="blocklist", description="Set URL blocklist regex patterns.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(patterns="One pattern per line or comma-separated")
    async def url_safety_blocklist(self, interaction: discord.Interaction, patterns: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_url_safety_config(interaction.guild.id, {"url_blocklist": patterns.strip()})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "url_safety_blocklist")
        await interaction.response.send_message("URL blocklist updated.", ephemeral=True)

    @url_safety_group.command(name="clear", description="Clear URL allowlist or blocklist.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(target="allowlist or blocklist")
    async def url_safety_clear(self, interaction: discord.Interaction, target: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        target_value = (target or "").strip().lower()
        if target_value not in {"allowlist", "blocklist"}:
            await interaction.response.send_message("Target must be `allowlist` or `blocklist`.", ephemeral=True)
            return
        field = "url_allowlist" if target_value == "allowlist" else "url_blocklist"
        await set_url_safety_config(interaction.guild.id, {field: None})
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, f"url_safety_clear_{target_value}")
        await interaction.response.send_message(f"Cleared URL {target_value}.", ephemeral=True)

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

    @custom_endpoint_group.command(name="view", description="View custom endpoint settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def custom_endpoint_view(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        config = await get_guild_config(interaction.guild.id)
        enabled = bool(config.get("custom_endpoint_enabled") or 0)
        embed = discord.Embed(title="Custom Endpoint Settings", color=discord.Color.blue())
        embed.add_field(name="Enabled", value=str(enabled), inline=False)
        embed.add_field(name="Endpoint URL", value=config.get("custom_endpoint_url") or "Not set", inline=False)
        embed.add_field(name="Model", value=config.get("custom_model_name") or "Not set", inline=False)
        embed.add_field(
            name="Capabilities",
            value=config.get("custom_model_capabilities") or "Not set",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @custom_endpoint_group.command(name="set", description="Set custom endpoint values.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        url="Base URL for OpenAI-compatible endpoint",
        model="Model name",
        capabilities="Comma-separated capabilities (openai_compat, streaming, tools, vision, video)",
        enabled="on/off",
        api_key="API key (optional)",
    )
    async def custom_endpoint_set(
        self,
        interaction: discord.Interaction,
        url: Optional[str] = None,
        model: Optional[str] = None,
        capabilities: Optional[str] = None,
        enabled: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return

        updates: Dict[str, Optional[str]] = {}
        if url is not None:
            updates["custom_endpoint_url"] = url.strip() if url.strip() else None
        if model is not None:
            updates["custom_model_name"] = model.strip() if model.strip() else None
        if capabilities is not None:
            updates["custom_model_capabilities"] = capabilities.strip() if capabilities.strip() else None
        if enabled is not None:
            enabled_value = enabled.lower().strip()
            if enabled_value in {"on", "enable", "true", "yes"}:
                updates["custom_endpoint_enabled"] = 1
            elif enabled_value in {"off", "disable", "false", "no"}:
                updates["custom_endpoint_enabled"] = 0
        if api_key is not None:
            updates["custom_endpoint_api_key"] = self.encryption.encrypt(api_key.strip()) if api_key.strip() else None

        if not updates:
            await interaction.response.send_message("No changes provided.", ephemeral=True)
            return

        await update_guild_config(interaction.guild.id, updates)
        await add_guild_config_audit(interaction.guild.id, interaction.user.id, "custom_endpoint_set")
        await interaction.response.send_message("Custom endpoint updated.", ephemeral=True)

    # =========================
    # Auto-role
    # =========================

    @autorole_group.command(name="manage", description="Open the autorole section inside the config panel UX.")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_manage(self, interaction: discord.Interaction):
        await self._send_autorole_panel(interaction)

    @autorole_group.command(name="set", description="Set the auto-role for new members.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role to assign on join")
    async def autorole_set(self, interaction: discord.Interaction, role: discord.Role):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_autorole_id(interaction.guild.id, role.id)
        await set_autorole_enabled(interaction.guild.id, True)
        await interaction.response.send_message(
            f"Auto-role set to {role.mention}. Use `/config panel` or `/autorole manage` for future edits.",
            ephemeral=True,
        )

    @autorole_group.command(name="clear", description="Clear the auto-role.")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_clear(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_autorole_id(interaction.guild.id, None)
        await set_autorole_enabled(interaction.guild.id, False)
        await interaction.response.send_message(
            "Auto-role disabled. Use `/config panel` or `/autorole manage` for future edits.",
            ephemeral=True,
        )

    @autorole_group.command(name="view", description="View the current auto-role.")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_view(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        config = await get_autorole_config(interaction.guild.id)
        role_id = config.get("autorole_id")
        enabled = config.get("autorole_enabled")
        if not role_id:
            await interaction.response.send_message(
                (
                    f"Auto-role is {'enabled' if enabled else 'disabled'}, but no role is set."
                    f"{self._manage_panel_hint('/config panel', '/autorole manage')}"
                ),
                ephemeral=True,
            )
            return
        role = interaction.guild.get_role(role_id)
        role_display = role.mention if role else f"(deleted role {role_id})"
        await interaction.response.send_message(
            f"Auto-role: {role_display} (enabled: {enabled}).{self._manage_panel_hint('/config panel', '/autorole manage')}",
            ephemeral=True,
        )

    # =========================
    # Welcome
    # =========================

    @welcome_group.command(name="manage", description="Open the welcome section inside the config panel UX.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_manage(self, interaction: discord.Interaction):
        await self._send_welcome_panel(interaction)

    @welcome_group.command(name="channel", description="Set the welcome channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Channel for welcome messages")
    async def welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_welcome_channel_id(interaction.guild.id, channel.id)
        await set_welcome_enabled(interaction.guild.id, True)
        await interaction.response.send_message(
            f"Welcome messages will be sent to {channel.mention}. Use `/config panel` or `/welcome manage` for future edits.",
            ephemeral=True,
        )

    @welcome_group.command(name="clear", description="Disable welcome messages and clear the channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_clear(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_welcome_channel_id(interaction.guild.id, None)
        await set_welcome_enabled(interaction.guild.id, False)
        await interaction.response.send_message(
            "Welcome messages disabled. Use `/config panel` or `/welcome manage` for future edits.",
            ephemeral=True,
        )

    @welcome_group.command(name="test", description="Send a test welcome message.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_test(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        config = await get_welcome_config(interaction.guild.id)
        channel_id = config.get("welcome_channel_id")
        if not channel_id:
            await interaction.response.send_message("No welcome channel set.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Welcome channel not found.", ephemeral=True)
            return
        await channel.send(f"Test welcome message for {interaction.user.mention}!")
        await interaction.response.send_message("Sent a test welcome message.", ephemeral=True)

    @welcome_group.command(name="set_message", description="Set a custom welcome message template.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        template="Use {member}, {member_name}, {member_count}, {member_ordinal}, {guild}."
    )
    async def welcome_set_message(self, interaction: discord.Interaction, template: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        cleaned = (template or "").strip()
        cleaned = cleaned.replace("\\n", "\n")
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

    @welcome_group.command(name="view_message", description="View the welcome message template.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_view_message(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        config = await get_welcome_config(interaction.guild.id)
        template = config.get("welcome_message_template")
        if not template:
            await interaction.response.send_message("No custom welcome template set.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"Current template:\n{template}{self._manage_panel_hint('/config panel', '/welcome manage')}",
            ephemeral=True,
        )

    @welcome_group.command(name="clear_message", description="Clear the welcome message template.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_clear_message(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_welcome_message_template(interaction.guild.id, None)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "welcome_template_clear",
        )
        await interaction.response.send_message("Welcome template cleared.", ephemeral=True)

    @welcome_group.command(name="set_dm_message", description="Set the DM welcome message.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(message="Message sent to new members via DM (use \\n for line breaks)")
    async def welcome_set_dm_message(self, interaction: discord.Interaction, message: str):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        cleaned = (message or "").strip()
        cleaned = cleaned.replace("\\n", "\n")
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

    @welcome_group.command(name="clear_dm_message", description="Clear the DM welcome message.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_clear_dm_message(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        await set_dm_welcome_message(interaction.guild.id, None)
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "dm_welcome_clear",
        )
        await interaction.response.send_message("DM welcome message cleared.", ephemeral=True)

    @welcome_group.command(name="toggle_dm", description="Enable or disable DM welcome messages.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def welcome_toggle_dm(self, interaction: discord.Interaction, state: Optional[str] = None):
        if not await self._require_guild(interaction):
            return
        if not state:
            enabled = await get_dm_welcome_enabled(interaction.guild.id)
            await interaction.response.send_message(
                f"DM welcome messages are currently **{'ENABLED' if enabled else 'DISABLED'}**.",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_dm_welcome_enabled(interaction.guild.id, True)
            await add_guild_config_audit(
                interaction.guild.id,
                interaction.user.id,
                "dm_welcome_on",
            )
            await interaction.response.send_message("DM welcome messages enabled.", ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await set_dm_welcome_enabled(interaction.guild.id, False)
            await add_guild_config_audit(
                interaction.guild.id,
                interaction.user.id,
                "dm_welcome_off",
            )
            await interaction.response.send_message("DM welcome messages disabled.", ephemeral=True)
        else:
            await interaction.response.send_message("Usage: `/welcome toggle_dm on|off`", ephemeral=True)

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
    # Structure Management
    # =========================

    @manage_group.command(name="create_category", description="Create a category.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manage_create_category(self, interaction: discord.Interaction, name: str):
        if not await self._require_guild(interaction):
            return
        category = await interaction.guild.create_category(
            name=name.strip(),
            reason=f"Requested by {interaction.user}",
        )
        await self._send_manage_mod_log(
            interaction.guild,
            interaction.user,
            "create_category",
            f"{category.name} ({category.id})",
        )
        await interaction.response.send_message(
            f"Created category {category.name}.",
            ephemeral=True,
        )

    @manage_group.command(name="create_text_channel", description="Create a text channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(category="Optional parent category")
    async def manage_create_text_channel(
        self,
        interaction: discord.Interaction,
        name: str,
        category: Optional[discord.CategoryChannel] = None,
    ):
        if not await self._require_guild(interaction):
            return
        channel = await interaction.guild.create_text_channel(
            name=name.strip(),
            category=category,
            reason=f"Requested by {interaction.user}",
        )
        await self._send_manage_mod_log(
            interaction.guild,
            interaction.user,
            "create_text_channel",
            f"{channel.name} ({channel.id})",
        )
        await interaction.response.send_message(
            f"Created text channel {channel.mention}.",
            ephemeral=True,
        )

    @manage_group.command(name="create_voice_channel", description="Create a voice channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(category="Optional parent category")
    async def manage_create_voice_channel(
        self,
        interaction: discord.Interaction,
        name: str,
        category: Optional[discord.CategoryChannel] = None,
    ):
        if not await self._require_guild(interaction):
            return
        channel = await interaction.guild.create_voice_channel(
            name=name.strip(),
            category=category,
            reason=f"Requested by {interaction.user}",
        )
        await self._send_manage_mod_log(
            interaction.guild,
            interaction.user,
            "create_voice_channel",
            f"{channel.name} ({channel.id})",
        )
        await interaction.response.send_message(
            f"Created voice channel `{channel.name}`.",
            ephemeral=True,
        )

    @manage_group.command(name="create_role", description="Create a role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manage_create_role(self, interaction: discord.Interaction, name: str):
        if not await self._require_guild(interaction):
            return
        role = await interaction.guild.create_role(
            name=name.strip(),
            reason=f"Requested by {interaction.user}",
        )
        await self._send_manage_mod_log(
            interaction.guild,
            interaction.user,
            "create_role",
            f"{role.name} ({role.id})",
        )
        await interaction.response.send_message(
            f"Created role {role.mention}.",
            ephemeral=True,
        )

    @manage_group.command(name="delete_category", description="Delete a category (confirmation required).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manage_delete_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        if not await self._require_guild(interaction):
            return
        summary = f"delete category '{category.name}'"

        async def _confirm() -> str:
            existing = interaction.guild.get_channel(category.id)
            if not isinstance(existing, discord.CategoryChannel):
                return "Category no longer exists."
            name = existing.name
            await existing.delete(reason=f"Requested by {interaction.user}")
            await self._send_manage_mod_log(
                interaction.guild,
                interaction.user,
                "delete_category",
                f"{name} ({category.id})",
            )
            return f"Deleted category `{name}`."

        view = ManageConfirmView(interaction.user.id, summary, _confirm)
        await interaction.response.send_message(
            f"Confirm delete: `{category.name}`",
            view=view,
            ephemeral=True,
        )

    @manage_group.command(name="delete_channel", description="Delete a text/voice channel (confirmation required).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manage_delete_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | discord.VoiceChannel,
    ):
        if not await self._require_guild(interaction):
            return
        summary = f"delete channel '{channel.name}'"

        async def _confirm() -> str:
            existing = interaction.guild.get_channel(channel.id)
            if not isinstance(existing, (discord.TextChannel, discord.VoiceChannel)):
                return "Channel no longer exists."
            name = existing.name
            kind = "text" if isinstance(existing, discord.TextChannel) else "voice"
            await existing.delete(reason=f"Requested by {interaction.user}")
            await self._send_manage_mod_log(
                interaction.guild,
                interaction.user,
                "delete_channel",
                f"{name} ({channel.id}) [{kind}]",
            )
            return f"Deleted {kind} channel `{name}`."

        view = ManageConfirmView(interaction.user.id, summary, _confirm)
        await interaction.response.send_message(
            f"Confirm delete: `{channel.name}`",
            view=view,
            ephemeral=True,
        )

    @manage_group.command(name="delete_role", description="Delete a role (confirmation required).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manage_delete_role(self, interaction: discord.Interaction, role: discord.Role):
        if not await self._require_guild(interaction):
            return
        if role.is_default():
            await interaction.response.send_message("Cannot delete @everyone.", ephemeral=True)
            return
        summary = f"delete role '{role.name}'"

        async def _confirm() -> str:
            existing = interaction.guild.get_role(role.id)
            if not existing:
                return "Role no longer exists."
            name = existing.name
            await existing.delete(reason=f"Requested by {interaction.user}")
            await self._send_manage_mod_log(
                interaction.guild,
                interaction.user,
                "delete_role",
                f"{name} ({role.id})",
            )
            return f"Deleted role `{name}`."

        view = ManageConfirmView(interaction.user.id, summary, _confirm)
        await interaction.response.send_message(
            f"Confirm delete: `{role.name}`",
            view=view,
            ephemeral=True,
        )

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
