"""
Social Cog for Femmy Discord Bot
=================================
Handles bot personality mode switching and mention reactions.

Commands:
    !mode <persona>  - Switch between personality modes
    !modes           - List available personality modes

Personality Modes:
    - femboy: Obedient, cute younger brother
    - tsundere: Abrasive but caring younger sister
    - oneesan: Mature, caring older sister (Ara Ara~)
"""

import os
import random
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands

from utils.app_emojis import (
    filter_emojis_by_prefix,
    format_custom_emoji,
    get_application_emojis,
)
from utils.db_handler import (
    add_guild_config_audit,
    get_server_mode,
    set_server_mode,
    get_evil_mode,
    set_evil_mode,
    get_autorole_config,
    get_welcome_config,
    get_dm_welcome_message,
    get_dm_welcome_enabled,
    get_custom_persona_by_name,
    get_custom_persona_by_mode_key,
    get_guild_custom_personas,
    sanitize_persona_name,
    set_guild_avatar_path,
)
from utils.guild_ai import generate_guild_gemini_text, GuildConfigError
from utils.logger import get_logger
from utils.server_profile import set_custom_profile, set_mode_profile, set_member_nickname
from utils.persona_panel_ui import (
    MANAGE_GUIDANCE,
    activate_persona_mode,
    set_persona_evil_mode,
)
from modes import get_mode_profile, get_all_modes, resolve_mode_key

logger = get_logger(__name__)


# Mode profiles are defined in discord_bot/modes

class Social(commands.Cog):
    """
    Social Cog - Personality mode management and reactions.
    
    Features:
        - Mode switching between three personalities
        - Custom reactions when mentioned
        - Greeting system
        
    TODO:
        - [ ] Add per-user mode preferences
        - [ ] Implement reaction randomization
        - [ ] Add custom greeting messages
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _resolve_custom_persona(self, guild_id: int, mode_name: str) -> dict | None:
        if not mode_name:
            return None
        persona = await get_custom_persona_by_name(guild_id, mode_name)
        if persona:
            return persona

        slug = sanitize_persona_name(mode_name)
        if not slug:
            return None

        try:
            personas = await get_guild_custom_personas(guild_id)
        except Exception:
            return None

        for candidate in personas:
            name = candidate.get("name") or ""
            if sanitize_persona_name(name) == slug:
                return candidate
        return None

    async def _get_app_emojis_by_prefix(self, prefix: str) -> list:
        emojis = await get_application_emojis(self.bot)
        return filter_emojis_by_prefix(emojis, prefix)

    async def _get_mode_icon(self, mode_key: str) -> str:
        profile = get_mode_profile(mode_key)
        prefix = profile.emoji_prefix or ""

        if prefix:
            emojis = await self._get_app_emojis_by_prefix(prefix)
            for emoji in emojis:
                token = format_custom_emoji(emoji)
                if token:
                    return token

        return ""

    def _set_mode_bio(self, guild_id: int, mode_key: str, custom_persona: dict | None = None) -> None:
        if custom_persona:
            bio = (custom_persona.get("bio") or f"Custom persona: {custom_persona.get('name', 'Unknown')}.").strip()
        else:
            bio = get_mode_profile(mode_key).bio
        bios = getattr(self.bot, "mode_bio_by_guild", None)
        if bios is None:
            bios = {}
            setattr(self.bot, "mode_bio_by_guild", bios)
        bios[guild_id] = bio

    def _get_mode_nickname(self, mode_key: str, custom_persona: dict | None = None) -> str:
        if custom_persona and custom_persona.get("name"):
            return str(custom_persona.get("name")).strip()
        if mode_key == "mode_oneesan":
            return "Yumi"
        if mode_key == "mode_default":
            return "Clanker"
        return "Femmy"

    async def _apply_mode_profile_updates(
        self,
        guild_id: int,
        mode_key: str,
        custom_persona: dict | None = None,
    ) -> None:
        self._set_mode_bio(guild_id, mode_key, custom_persona=custom_persona)

        try:
            if custom_persona:
                custom_bio = (custom_persona.get("bio") or f"Custom persona: {custom_persona.get('name', 'custom')}.").strip()
                banner_path = custom_persona.get("banner_path")
                if banner_path:
                    banner_file = Path(banner_path)
                    if banner_file.exists():
                        banner_bytes = banner_file.read_bytes()
                        success, reason = await set_custom_profile(
                            self.bot,
                            guild_id,
                            banner_bytes=banner_bytes,
                            bio=custom_bio,
                        )
                    else:
                        banner_path = None
                if not banner_path:
                    default_profile = get_mode_profile("mode_default")
                    success, reason = await set_mode_profile(
                        self.bot,
                        guild_id,
                        "mode_default",
                        bio=custom_bio,
                        banner_file=default_profile.banner_file,
                    )
            else:
                profile = get_mode_profile(mode_key)
                success, reason = await set_mode_profile(
                    self.bot,
                    guild_id,
                    mode_key,
                    bio=profile.bio,
                    banner_file=profile.banner_file,
                )
            if not success:
                logger.warning("Failed to update guild profile for %s: %s", mode_key, reason)
        except Exception as exc:
            logger.warning("Failed to update guild profile for %s: %s", mode_key, exc)

        try:
            nickname = self._get_mode_nickname(mode_key, custom_persona=custom_persona)
            nickname = nickname[:32].strip() if nickname else None
            if nickname == "":
                nickname = None
            success, reason = await set_member_nickname(self.bot, guild_id, nickname)
            if not success and reason != "forbidden":
                logger.warning("Failed to update guild nickname for %s: %s", mode_key, reason)
        except Exception as exc:
            logger.warning("Failed to update guild nickname for %s: %s", mode_key, exc)

        try:
            if custom_persona and custom_persona.get("avatar_path"):
                avatar_path = custom_persona.get("avatar_path")
                avatar_bytes = Path(avatar_path).read_bytes()
                from utils.server_avatar import set_custom_avatar
                success, reason = await set_custom_avatar(self.bot, guild_id, avatar_bytes)
                if not success:
                    logger.warning("Failed to update server avatar for %s: %s", mode_key, reason)
            else:
                await set_guild_avatar_path(guild_id, None)
                from utils.server_avatar import set_mode_avatar
                evil_mode_enabled = await get_evil_mode(guild_id)
                target_avatar_mode = mode_key if not custom_persona else "mode_default"
                success, reason = await set_mode_avatar(
                    self.bot,
                    guild_id,
                    target_avatar_mode,
                    evil_mode=evil_mode_enabled,
                    force=True,
                )
                if not success and reason != "custom":
                    logger.warning("Failed to update server avatar for %s: %s", mode_key, reason)
        except Exception as exc:
            logger.warning("Failed to update server avatar for %s: %s", mode_key, exc)

    async def _log_persona_presentation_audit(
        self,
        guild_id: int,
        user_id: int,
        *,
        action: str,
        summary: str,
        detail: dict | None = None,
        target_id: str | None = None,
    ) -> None:
        await add_guild_config_audit(
            guild_id,
            user_id,
            action,
            category="persona_presentation",
            target_type="persona_mode",
            target_id=target_id,
            summary=summary,
            detail=detail,
        )

    async def apply_mode_selection(
        self,
        guild: discord.Guild,
        actor: discord.abc.User,
        mode_name: str | None,
    ) -> tuple[bool, str]:
        locked_mode = os.getenv("BOT_MODE", "").lower()
        if locked_mode in ("femboy", "tsundere", "oneesan"):
            return (
                False,
                "Mode switching is disabled for this bot instance.\n"
                f"This bot is locked to **{locked_mode}** mode.",
            )

        requested_name = (mode_name or "").strip().lower()
        if not requested_name:
            return False, "No mode provided."

        target_mode = resolve_mode_key(requested_name)
        custom_persona = None
        if not target_mode:
            custom_persona = await self._resolve_custom_persona(guild.id, requested_name)
            if custom_persona:
                target_mode = custom_persona.get("mode_key")

        if not target_mode:
            return False, f"Unknown mode: `{requested_name}`"

        current_mode = await get_server_mode(guild.id)
        if current_mode == target_mode:
            if custom_persona:
                return True, f"Already in **{custom_persona.get('name', 'custom')}** mode!"
            profile = get_mode_profile(target_mode)
            mode_icon = await self._get_mode_icon(target_mode)
            prefix = f"{mode_icon} " if mode_icon else ""
            return True, f"{prefix}Already in **{profile.display_name}** mode!"

        await activate_persona_mode(
            bot=self.bot,
            guild_id=guild.id,
            user_id=actor.id,
            mode_key=target_mode,
        )

        if custom_persona:
            target_name = custom_persona.get("name", "custom")
            message = f"Mode changed to **{target_name}**!"
        else:
            profile = get_mode_profile(target_mode)
            mode_icon = await self._get_mode_icon(target_mode)
            prefix = f"{mode_icon} " if mode_icon else ""
            target_name = profile.display_name
            message = f"{prefix}{profile.switch_message}"
        return True, message

    async def apply_evil_mode_change(
        self,
        guild: discord.Guild,
        actor: discord.abc.User,
        state: bool | None,
    ) -> tuple[bool, str]:
        current_mode = await get_server_mode(guild.id)
        if current_mode == "mode_default":
            await set_evil_mode(guild.id, False)
            return True, "Evil Mode is disabled in default mode."

        if state is None:
            current = await get_evil_mode(guild.id)
            status = "ENABLED" if current else "DISABLED"
            return True, f"Evil Mode is currently **{status}**."

        await set_persona_evil_mode(
            bot=self.bot,
            guild_id=guild.id,
            user_id=actor.id,
            enabled=state,
        )
        if state:
            return True, "Evil Mode ENABLED. Responses will now use uncensored models (Venice/Hermes)."
        return True, "Evil Mode DISABLED. Returning to standard safety protocols."

    def _is_mention_only(self, message: discord.Message) -> bool:
        """Return True when the message only mentions the bot."""
        content = message.content
        content = content.replace(f"<@{self.bot.user.id}>", "")
        content = content.replace(f"<@!{self.bot.user.id}>", "")
        return content.strip() == ""

    def _format_ordinal(self, number: int) -> str:
        if number <= 0:
            return str(number)
        if 10 <= (number % 100) <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
        return f"{number}{suffix}"

    def _apply_welcome_template(
        self,
        template: str,
        member: discord.Member,
        member_count: int,
    ) -> str:
        ordinal = self._format_ordinal(member_count)
        replacements = {
            "{member}": member.mention,
            "{member_name}": member.display_name,
            "{member_count}": str(member_count),
            "{member_ordinal}": ordinal,
            "{guild}": member.guild.name,
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def _ensure_join_count_sentence(self, text: str, member_count: int) -> str:
        ordinal = self._format_ordinal(member_count)
        if str(member_count) in text or ordinal in text:
            return text
        sentence = f"You are the {ordinal} member to join~"
        if text.endswith((".", "!", "?", "~")):
            return f"{text} {sentence}"
        return f"{text}. {sentence}"
    
    @commands.command(name="evil", aliases=["uncensored"])
    @commands.has_permissions(manage_guild=True)
    async def toggle_evil_mode(self, ctx: commands.Context, state: str = None):
        """
        Toggle 'Evil' (Uncensored) mode using OpenRouter models.
        
        Usage: !evil [on/off]
        """
        current_mode = await get_server_mode(ctx.guild.id)
        if current_mode == "mode_default":
            await set_evil_mode(ctx.guild.id, False)
            await ctx.send(f"Evil Mode is disabled in default mode. {MANAGE_GUIDANCE}")
            return

        if not state:
            current = await get_evil_mode(ctx.guild.id)
            status = "ENABLED" if current else "DISABLED"
            await ctx.send(f"😈 Evil Mode is currently **{status}**. {MANAGE_GUIDANCE}")
            return

        state = state.lower()
        if state in ["on", "enable", "true", "yes"]:
            await set_persona_evil_mode(
                bot=self.bot,
                guild_id=ctx.guild.id,
                user_id=ctx.author.id,
                enabled=True,
            )
            await ctx.send(f"😈 Evil Mode ENABLED. Responses will now use uncensored models (Venice/Hermes). {MANAGE_GUIDANCE}")
        elif state in ["off", "disable", "false", "no"]:
            await set_persona_evil_mode(
                bot=self.bot,
                guild_id=ctx.guild.id,
                user_id=ctx.author.id,
                enabled=False,
            )
            await ctx.send(f"😇 Evil Mode DISABLED. Returning to standard safety protocols. {MANAGE_GUIDANCE}")
        else:
            await ctx.send(f"Usage: `!evil on` or `!evil off` {MANAGE_GUIDANCE}")

    @app_commands.command(name="evil", description="Toggle uncensored (evil) mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(state="on/off")
    async def toggle_evil_mode_slash(self, interaction: discord.Interaction, state: str = None):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        current_mode = await get_server_mode(interaction.guild.id)
        if current_mode == "mode_default":
            await set_evil_mode(interaction.guild.id, False)
            await interaction.response.send_message(
                f"Evil Mode is disabled in default mode. {MANAGE_GUIDANCE}",
                ephemeral=True,
            )
            return

        if not state:
            current = await get_evil_mode(interaction.guild.id)
            status = "ENABLED" if current else "DISABLED"
            await interaction.response.send_message(f"😈 Evil Mode is currently **{status}**. {MANAGE_GUIDANCE}")
            return

        state = state.lower()
        if state in ["on", "enable", "true", "yes"]:
            await set_persona_evil_mode(
                bot=self.bot,
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                enabled=True,
            )
            await interaction.response.send_message(
                f"😈 Evil Mode ENABLED. Responses will now use uncensored models (Venice/Hermes). {MANAGE_GUIDANCE}"
            )
        elif state in ["off", "disable", "false", "no"]:
            await set_persona_evil_mode(
                bot=self.bot,
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                enabled=False,
            )
            await interaction.response.send_message(
                f"😇 Evil Mode DISABLED. Returning to standard safety protocols. {MANAGE_GUIDANCE}"
            )
        else:
            await interaction.response.send_message(
                f"Usage: `/evil on` or `/evil off` {MANAGE_GUIDANCE}",
                ephemeral=True,
            )

    @app_commands.command(name="evil", description="Toggle uncensored (evil) mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(state="on/off")
    async def toggle_evil_mode_slash(self, interaction: discord.Interaction, state: str = None):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        normalized_state = None
        if state:
            lowered = state.lower().strip()
            if lowered in ["on", "enable", "true", "yes"]:
                normalized_state = True
            elif lowered in ["off", "disable", "false", "no"]:
                normalized_state = False
            else:
                await interaction.response.send_message(
                    "Usage: `/evil on` or `/evil off`\nUse `/persona manage` for the primary persona and presentation panel.",
                    ephemeral=True,
                )
                return

        _, message = await self.apply_evil_mode_change(
            interaction.guild,
            interaction.user,
            normalized_state,
        )
        await interaction.response.send_message(
            f"{message}\nUse `/persona manage` for the primary persona and presentation panel.",
            ephemeral=True,
        )

    @commands.command(name="mode")
    @commands.has_permissions(manage_guild=True)
    async def switch_mode(self, ctx: commands.Context, mode_name: str = None):
        """
        Switch the bot's personality mode.

        Args:
            mode_name: Personality mode (femboy, tsundere, oneesan)
        """
        if not mode_name:
            await self.show_modes(ctx)
            return

        ok, message = await self.apply_mode_selection(ctx.guild, ctx.author, mode_name)
        if not ok:
            await ctx.send(f"{message}\nUse `!modes` to see available options.")
            return
        await ctx.send(f"{message}\nUse `/persona manage` for the primary persona and presentation panel.")

    @app_commands.command(name="mode", description="Switch the bot's personality mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(mode="Personality mode")
    async def switch_mode_slash(self, interaction: discord.Interaction, mode: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        _, message = await self.apply_mode_selection(interaction.guild, interaction.user, mode)
        await interaction.response.send_message(
            f"{message}\nUse `/persona manage` for the primary persona and presentation panel.",
            ephemeral=True,
        )

    @app_commands.command(name="mode", description="Switch the bot's personality mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(mode="Personality mode")
    async def switch_mode_slash(self, interaction: discord.Interaction, mode: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        ok, message = await self.apply_mode_selection(interaction.guild, interaction.user, mode)
        if not ok:
            await interaction.response.send_message(
                f"{message}\nUse `/modes` to see available options!",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"{message}\nUse `/persona manage` for the primary persona and presentation panel.",
            ephemeral=True,
        )

    @switch_mode_slash.autocomplete("mode")
    async def mode_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if not interaction.guild:
            return []

        current_lower = (current or "").lower()
        options = ["default", "femboy", "tsundere", "oneesan"]

        try:
            personas = await get_guild_custom_personas(interaction.guild.id)
        except Exception:
            personas = []

        for persona in personas:
            name = persona.get("name")
            if name:
                options.append(name)

        results = []
        for option in options:
            if current_lower and current_lower not in option.lower():
                continue
            results.append(app_commands.Choice(name=option, value=option))
            if len(results) >= 25:
                break

        return results

    @commands.command(name="modes", aliases=["personalities", "personas"])
    async def show_modes(self, ctx: commands.Context):
        """
        Display all available personality modes.
        """
        current_mode = await get_server_mode(ctx.guild.id)
        current_evil = await get_evil_mode(ctx.guild.id)

        embed = discord.Embed(
            title="Available Personality Modes",
            description="Switch Femmy's personality with `!mode <name>`",
            color=discord.Color.from_rgb(255, 182, 193),
        )

        evil_status = "😈 Evil Mode: ON" if current_evil else "😇 Evil Mode: OFF"
        embed.add_field(name="System Status", value=evil_status, inline=False)

        for profile in get_all_modes():
            mode_key = profile.key
            is_current = mode_key == current_mode
            marker = " <- Current" if is_current else ""
            mode_icon = await self._get_mode_icon(mode_key)
            prefix = f"{mode_icon} " if mode_icon else ""

            embed.add_field(
                name=f"{prefix}{profile.display_name}{marker}",
                value=f"{profile.description}\nAliases: {', '.join(profile.aliases)}",
                inline=False,
            )

        try:
            personas = await get_guild_custom_personas(ctx.guild.id)
        except Exception:
            personas = []

        if personas:
            lines = []
            for persona in personas:
                name = persona.get("name", "Custom Persona")
                mode_key = persona.get("mode_key", "")
                is_current = mode_key == current_mode
                marker = " <- Current" if is_current else ""
                bio = (persona.get("bio") or "Custom persona.").strip()
                if len(bio) > 80:
                    bio = bio[:77].rstrip() + "..."
                lines.append(f"- {name}{marker}: {bio}")
                if len(lines) >= 12:
                    break

            embed.add_field(
                name="Custom Personas",
                value="\n".join(lines),
                inline=False,
            )

        embed.set_footer(text="Manage Guild permission required to change modes")
        await ctx.send(embed=embed)

    @app_commands.command(name="modes", description="List all available personality modes.")
    async def show_modes_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        current_mode = await get_server_mode(interaction.guild.id)
        current_evil = await get_evil_mode(interaction.guild.id)

        embed = discord.Embed(
            title="Available Personality Modes",
            description="Switch Femmy's personality with `/mode`",
            color=discord.Color.from_rgb(255, 182, 193),
        )

        evil_status = "😈 Evil Mode: ON" if current_evil else "😇 Evil Mode: OFF"
        embed.add_field(name="System Status", value=evil_status, inline=False)

        for profile in get_all_modes():
            mode_key = profile.key
            is_current = mode_key == current_mode
            marker = " <- Current" if is_current else ""
            mode_icon = await self._get_mode_icon(mode_key)
            prefix = f"{mode_icon} " if mode_icon else ""

            embed.add_field(
                name=f"{prefix}{profile.display_name}{marker}",
                value=f"{profile.description}\nAliases: {', '.join(profile.aliases)}",
                inline=False,
            )

        try:
            personas = await get_guild_custom_personas(interaction.guild.id)
        except Exception:
            personas = []

        if personas:
            lines = []
            for persona in personas:
                name = persona.get("name", "Custom Persona")
                mode_key = persona.get("mode_key", "")
                is_current = mode_key == current_mode
                marker = " <- Current" if is_current else ""
                bio = (persona.get("bio") or "Custom persona.").strip()
                if len(bio) > 80:
                    bio = bio[:77].rstrip() + "..."
                lines.append(f"- {name}{marker}: {bio}")
                if len(lines) >= 12:
                    break

            embed.add_field(
                name="Custom Personas",
                value="\n".join(lines),
                inline=False,
            )

        embed.set_footer(text="Manage Guild permission required to change modes")
        await interaction.response.send_message(embed=embed)

    @commands.command(name="currentmode", aliases=["whatmode"])
    async def show_current_mode(self, ctx: commands.Context):
        """Display the current personality mode."""
        current_mode = await get_server_mode(ctx.guild.id)
        current_evil = await get_evil_mode(ctx.guild.id)
        custom_persona = None
        if current_mode.startswith("custom_"):
            custom_persona = await get_custom_persona_by_mode_key(ctx.guild.id, current_mode)

        evil_text = " 😈 (Evil Mode Active)" if current_evil else ""
        if custom_persona:
            description = custom_persona.get("bio") or "Custom persona."
            await ctx.send(
                f"Currently in **{custom_persona.get('name', 'custom')}** mode!{evil_text}\n"
                f"*{description}*"
            )
            return

        profile = get_mode_profile(current_mode)
        mode_icon = await self._get_mode_icon(current_mode)
        prefix = f"{mode_icon} " if mode_icon else ""

        await ctx.send(
            f"{prefix}Currently in **{profile.display_name}** mode!{evil_text}\n"
            f"*{profile.bio}*"
        )

    @app_commands.command(name="currentmode", description="Show the current personality mode.")
    async def show_current_mode_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        current_mode = await get_server_mode(interaction.guild.id)
        current_evil = await get_evil_mode(interaction.guild.id)
        custom_persona = None
        if current_mode.startswith("custom_"):
            custom_persona = await get_custom_persona_by_mode_key(interaction.guild.id, current_mode)

        evil_text = " 😈 (Evil Mode Active)" if current_evil else ""
        if custom_persona:
            description = custom_persona.get("bio") or "Custom persona."
            await interaction.response.send_message(
                f"Currently in **{custom_persona.get('name', 'custom')}** mode!{evil_text}\n"
                f"*{description}*"
            )
            return

        profile = get_mode_profile(current_mode)
        mode_icon = await self._get_mode_icon(current_mode)
        prefix = f"{mode_icon} " if mode_icon else ""

        await interaction.response.send_message(
            f"{prefix}Currently in **{profile.display_name}** mode!{evil_text}\n"
            f"*{profile.bio}*"
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Handle auto-role assignment and optional AI welcome message.
        """
        guild_id = member.guild.id
        mode = await get_server_mode(guild_id)

        # Auto-role
        try:
            autorole_config = await get_autorole_config(guild_id)
            if autorole_config.get("autorole_enabled") and autorole_config.get("autorole_id"):
                role = member.guild.get_role(autorole_config["autorole_id"])
                if role:
                    await member.add_roles(role, reason="Auto-role assignment")
        except discord.Forbidden:
            logger.warning("Missing permissions to assign autorole in %s", member.guild.name)
        except Exception as exc:
            logger.error("Auto-role assignment failed in %s: %s", member.guild.name, exc, exc_info=True)

        # AI Welcome
        welcome_config = await get_welcome_config(guild_id)
        welcome_enabled = welcome_config.get("welcome_enabled")
        channel_id = welcome_config.get("welcome_channel_id") if welcome_enabled else None
        channel = member.guild.get_channel(channel_id) if channel_id else None
        template = welcome_config.get("welcome_message_template") if welcome_enabled else None
        member_count = int(getattr(member.guild, "member_count", 0) or 0)

        if channel:
            if template:
                welcome_text = self._apply_welcome_template(template, member, member_count)
            else:
                prompt = (
                    "Write one short, cute, friendly welcome sentence for a new Discord member. "
                    f"Server: {member.guild.name}. User: {member.display_name}. "
                    f"Persona mode: {mode}. Keep it playful, SFW, and unique."
                )

                fallback_messages = {
                    "mode_default": f"Welcome to the server, {member.mention}.",
                    "mode_femboy": f"Welcome to the server, {member.mention}! I hope we can be great friends~",
                    "mode_tsundere": f"Oh, {member.mention} joined... I guess you can stay. ...Welcome.",
                    "mode_oneesan": f"Ara ara~ Welcome, {member.mention}! Make yourself at home, my dear~",
                }

                try:
                    welcome_text, _ = await generate_guild_gemini_text(guild_id, prompt)
                    welcome_text = welcome_text.strip()
                except GuildConfigError:
                    welcome_text = ""
                except Exception as exc:
                    logger.warning("AI welcome failed for %s: %s", member.guild.name, exc)
                    welcome_text = ""

                if not welcome_text:
                    welcome_text = fallback_messages.get(mode, fallback_messages["mode_default"])
                else:
                    if member.mention not in welcome_text:
                        welcome_text = f"{welcome_text} {member.mention}"

            if member_count > 0:
                welcome_text = self._ensure_join_count_sentence(welcome_text, member_count)

            try:
                await channel.send(
                    welcome_text,
                    allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                )
            except discord.Forbidden:
                logger.warning("Missing permissions to send welcome in %s", member.guild.name)

        # DM Welcome (Preset message from server staff)
        dm_enabled = await get_dm_welcome_enabled(guild_id)
        dm_text = await get_dm_welcome_message(guild_id)
        if dm_enabled and dm_text:
            try:
                embed = discord.Embed(
                    title=f"Welcome to {member.guild.name}!",
                    description=dm_text,
                    color=discord.Color.blue(),
                )
                embed.set_footer(text="This is an automated message from the server staff.")
                await member.send(embed=embed)
            except discord.Forbidden:
                logger.warning("Could not DM %s (DMs closed).", member)
            except Exception as exc:
                logger.warning("Failed to DM welcome message to %s: %s", member, exc)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Respond to mention-only messages with a quick reaction.
        """
        if message.author.bot:
            return
        if not message.guild:
            return
        if self.bot.user not in message.mentions:
            return
        if message.attachments:
            return
        if not self._is_mention_only(message):
            return

        mode = await get_server_mode(message.guild.id)
        profile = get_mode_profile(mode)
        responses = profile.mention_reactions or ()
        if not responses:
            return
        response_text = random.choice(responses)
        await message.reply(response_text, mention_author=False)


async def setup(bot: commands.Bot):
    """Load the Social cog."""
    await bot.add_cog(Social(bot))
