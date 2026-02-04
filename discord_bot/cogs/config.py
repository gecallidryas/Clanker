"""
Guild configuration commands for API keys and models.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


class Config(commands.Cog):
    # Main config group
    config = app_commands.Group(name="config", description="Guild configuration")
    
    # Subgroups under /config
    password_group = app_commands.Group(name="password", description="Manage guild config password", parent=config)
    keys_group = app_commands.Group(name="keys", description="View or manage stored API keys", parent=config)
    model_group = app_commands.Group(name="model", description="View or set models", parent=config)
    env_group = app_commands.Group(name="env", description="Upload or retrieve guild env template", parent=config)
    toggle_group = app_commands.Group(name="toggle", description="Toggle guild features", parent=config)
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
                f"Auto-role is currently **{status}**.",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_autorole_enabled(interaction.guild.id, True)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "autorole_on")
            await interaction.response.send_message("Auto-role enabled.", ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await set_autorole_enabled(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "autorole_off")
            await interaction.response.send_message("Auto-role disabled.", ephemeral=True)
        else:
            await interaction.response.send_message("Usage: `/config toggle autorole on|off`", ephemeral=True)

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
                f"Welcome messages are currently **{status}**.",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_welcome_enabled(interaction.guild.id, True)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "welcome_on")
            await interaction.response.send_message("Welcome messages enabled.", ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await set_welcome_enabled(interaction.guild.id, False)
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, "welcome_off")
            await interaction.response.send_message("Welcome messages disabled.", ephemeral=True)
        else:
            await interaction.response.send_message("Usage: `/config toggle welcome on|off`", ephemeral=True)

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
                f"{label} is currently **{status}**.",
                ephemeral=True,
            )
            return
        if not await self._require_auth(interaction):
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await update_guild_config(interaction.guild.id, {flag_name: 1})
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, f"{flag_name}_on")
            await interaction.response.send_message(f"{label} enabled.", ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await update_guild_config(interaction.guild.id, {flag_name: 0})
            await add_guild_config_audit(interaction.guild.id, interaction.user.id, f"{flag_name}_off")
            await interaction.response.send_message(f"{label} disabled.", ephemeral=True)
        else:
            await interaction.response.send_message("Usage: `on` or `off`.", ephemeral=True)

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

    @config.command(name="ui", description="Open a quick toggle UI panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_ui(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not await self._require_auth(interaction):
            return
        view = ConfigToggleView(interaction.guild.id, interaction.user.id)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
        capabilities="Comma-separated capabilities (tools, vision, video)",
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
            f"Auto-role set to {role.mention}.",
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
        await interaction.response.send_message("Auto-role disabled.", ephemeral=True)

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
                f"Auto-role is {'enabled' if enabled else 'disabled'}, but no role is set.",
                ephemeral=True,
            )
            return
        role = interaction.guild.get_role(role_id)
        role_display = role.mention if role else f"(deleted role {role_id})"
        await interaction.response.send_message(
            f"Auto-role: {role_display} (enabled: {enabled}).",
            ephemeral=True,
        )

    # =========================
    # Welcome
    # =========================

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
            f"Welcome messages will be sent to {channel.mention}.",
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
        await interaction.response.send_message("Welcome messages disabled.", ephemeral=True)

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
        await interaction.response.send_message(f"Current template:\n{template}", ephemeral=True)

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
            f"Added {role.mention} as bot staff (level {level.value}).",
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
                f"Removed {role.mention} from bot staff.",
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
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    # =========================
    # Mod Log
    # =========================

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
            f"Moderation logs will be sent to {channel.mention}.",
            ephemeral=True,
        )

    @modlog_group.command(name="clear", description="Disable moderation logs.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modlog_clear(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await set_mod_log_channel_id(interaction.guild.id, None)
        await interaction.response.send_message("Moderation logs disabled.", ephemeral=True)

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
                f"Mod logs are posted in {channel.mention}.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Mod log channel set to ID {channel_id}, but I can't access it.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Config(bot))
