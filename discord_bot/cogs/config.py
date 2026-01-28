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
)
from utils.encryption import get_encryption
from utils.guild_ai import (
    RECOMMENDED_GEMINI_MODELS,
    RECOMMENDED_OPENROUTER_MODELS,
)
from utils.api_manager import normalize_openrouter_model, normalize_gemini_model, OPENROUTER_MODELS
from utils.rate_limiter import RateLimiter
from utils.logger import get_logger

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
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "OPENROUTER_API_KEY_2": "openrouter_api_key_2",
    "OPENROUTER_API_KEY_3": "openrouter_api_key_3",
    "OPENROUTER_API_KEY_4": "openrouter_api_key_4",
    "OPENROUTER_API_KEY_5": "openrouter_api_key_5",
    "GEMINI_MODEL": "gemini_model",
    "OPENROUTER_MODEL": "openrouter_model",
    "OPENROUTER_FALLBACK_MODELS": "openrouter_fallback_models",
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
    "uncensored": [
        "openrouter_api_key",
        "openrouter_api_key_2",
        "openrouter_api_key_3",
        "openrouter_api_key_4",
        "openrouter_api_key_5",
    ],
}


class Config(commands.Cog):
    config = app_commands.Group(name="config", description="Guild configuration")

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
                "Use this command in a server.",
                ephemeral=True,
            )
            return False
        return True

    async def _require_auth(self, interaction: discord.Interaction) -> bool:
        if not await is_authenticated(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message(
                "Please authenticate first with `/config auth`.",
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

    @config.group(name="password", description="Manage guild config password.")
    @app_commands.checks.has_permissions(administrator=True)
    async def password_group(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await interaction.response.send_message(
            "Use a subcommand: set, change, or reset.",
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

    @config.group(name="keys", description="View or clear stored API keys.")
    @app_commands.checks.has_permissions(administrator=True)
    async def keys_group(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await interaction.response.send_message(
            "Use a subcommand: view or clear.",
            ephemeral=True,
        )

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
            name="OpenRouter (Uncensored)",
            value=format_group(CATEGORY_FIELDS["uncensored"]),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @keys_group.command(name="clear", description="Clear all stored API keys.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(category="general, translate, summarize, uncensored", slot="Key slot (1-5)")
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
                "Invalid category or slot. Categories: general, translate, summarize, uncensored.",
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
                "Invalid category or slot. Categories: general, translate, summarize, uncensored.",
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
        options = ["general", "translate", "summarize", "uncensored"]
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
    # Models
    # =========================

    @config.group(name="model", description="View or set models.")
    @app_commands.checks.has_permissions(administrator=True)
    async def model_group(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await interaction.response.send_message(
            "Use a subcommand: view or set.",
            ephemeral=True,
        )

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

    # =========================
    # Env
    # =========================

    @config.group(name="env", description="Upload or retrieve guild env template.")
    @app_commands.checks.has_permissions(administrator=True)
    async def env_group(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await interaction.response.send_message(
            "Use a subcommand: upload or example.",
            ephemeral=True,
        )

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
        await interaction.response.send_message(
            "Here is the guild .env.example template.",
            file=discord.File(template_path),
            ephemeral=True,
        )

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

    @config.group(name="toggle", description="Toggle guild features.")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_group(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await interaction.response.send_message(
            "Use a subcommand: evil.",
            ephemeral=True,
        )

    @toggle_group.command(name="evil", description="Enable or disable evil mode.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def toggle_evil(self, interaction: discord.Interaction, state: Optional[str] = None):
        if not await self._require_guild(interaction):
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Config(bot))
