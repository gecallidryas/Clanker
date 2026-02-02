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
import discord
from discord import app_commands
from discord.ext import commands

from utils.app_emojis import (
    filter_emojis_by_prefix,
    format_custom_emoji,
    get_application_emojis,
)
from utils.db_handler import (
    get_server_mode,
    set_server_mode,
    get_evil_mode,
    set_evil_mode,
    get_autorole_config,
    get_welcome_config,
    get_dm_welcome_message,
    get_dm_welcome_enabled,
)
from utils.guild_ai import generate_guild_gemini_text, GuildConfigError
from utils.logger import get_logger
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

    async def _set_presence_for_mode(self, mode_key: str) -> None:
        activity = discord.Game(name="Clanking with humans")
        await self.bot.change_presence(activity=activity)

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
            await ctx.send("Evil Mode is disabled in default mode.")
            return

        if not state:
            current = await get_evil_mode(ctx.guild.id)
            status = "ENABLED" if current else "DISABLED"
            await ctx.send(f"😈 Evil Mode is currently **{status}**.")
            return

        state = state.lower()
        if state in ["on", "enable", "true", "yes"]:
            await set_evil_mode(ctx.guild.id, True)
            await ctx.send("😈 Evil Mode ENABLED. Responses will now use uncensored models (Venice/Hermes).")
        elif state in ["off", "disable", "false", "no"]:
            await set_evil_mode(ctx.guild.id, False)
            await ctx.send("😇 Evil Mode DISABLED. Returning to standard safety protocols.")
        else:
            await ctx.send("Usage: `!evil on` or `!evil off`")

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
            await interaction.response.send_message("Evil Mode is disabled in default mode.", ephemeral=True)
            return

        if not state:
            current = await get_evil_mode(interaction.guild.id)
            status = "ENABLED" if current else "DISABLED"
            await interaction.response.send_message(f"😈 Evil Mode is currently **{status}**.")
            return

        state = state.lower()
        if state in ["on", "enable", "true", "yes"]:
            await set_evil_mode(interaction.guild.id, True)
            await interaction.response.send_message(
                "😈 Evil Mode ENABLED. Responses will now use uncensored models (Venice/Hermes)."
            )
        elif state in ["off", "disable", "false", "no"]:
            await set_evil_mode(interaction.guild.id, False)
            await interaction.response.send_message(
                "😇 Evil Mode DISABLED. Returning to standard safety protocols."
            )
        else:
            await interaction.response.send_message("Usage: `/evil on` or `/evil off`", ephemeral=True)

    @commands.command(name="mode")
    @commands.has_permissions(manage_guild=True)
    async def switch_mode(self, ctx: commands.Context, mode_name: str = None):
        """
        Switch the bot's personality mode.

        Args:
            mode_name: Personality mode (femboy, tsundere, oneesan)
        """
        # Check if mode is locked via environment
        locked_mode = os.getenv("BOT_MODE", "").lower()
        if locked_mode in ("femboy", "tsundere", "oneesan"):
            await ctx.send(
                "Mode switching is disabled for this bot instance.\n"
                f"This bot is locked to **{locked_mode}** mode."
            )
            return

        if not mode_name:
            await self.show_modes(ctx)
            return

        # Normalize mode name
        mode_name = mode_name.lower().strip()
        target_mode = resolve_mode_key(mode_name)

        if not target_mode:
            await ctx.send(
                f"Unknown mode: `{mode_name}`\n"
                "Use `!modes` to see available options!"
            )
            return

        # Check if already in this mode
        current_mode = await get_server_mode(ctx.guild.id)
        if current_mode == target_mode:
            profile = get_mode_profile(target_mode)
            mode_icon = await self._get_mode_icon(target_mode)
            prefix = f"{mode_icon} " if mode_icon else ""
            await ctx.send(f"{prefix}Already in **{profile.display_name}** mode!")
            return

        # Switch mode
        await set_server_mode(ctx.guild.id, target_mode)
        if target_mode == "mode_default":
            await set_evil_mode(ctx.guild.id, False)

        profile = get_mode_profile(target_mode)
        mode_icon = await self._get_mode_icon(target_mode)
        prefix = f"{mode_icon} " if mode_icon else ""
        await ctx.send(f"{prefix}{profile.switch_message}")
        try:
            await self._set_presence_for_mode(target_mode)
        except Exception as exc:
            logger.warning("Failed to update presence for %s: %s", target_mode, exc)
        try:
            from utils.server_avatar import set_mode_avatar
            evil_mode_enabled = await get_evil_mode(ctx.guild.id)
            success, reason = await set_mode_avatar(
                self.bot,
                ctx.guild.id,
                target_mode,
                evil_mode=evil_mode_enabled,
            )
            if not success and reason != "custom":
                logger.warning("Failed to update server avatar for %s: %s", target_mode, reason)
        except Exception as exc:
            logger.warning("Failed to update server avatar for %s: %s", target_mode, exc)

    @app_commands.command(name="mode", description="Switch the bot's personality mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(mode="Personality mode")
    @app_commands.choices(mode=[
        app_commands.Choice(name="default", value="default"),
        app_commands.Choice(name="femboy", value="femboy"),
        app_commands.Choice(name="tsundere", value="tsundere"),
        app_commands.Choice(name="oneesan", value="oneesan"),
    ])
    async def switch_mode_slash(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        locked_mode = os.getenv("BOT_MODE", "").lower()
        if locked_mode in ("femboy", "tsundere", "oneesan"):
            await interaction.response.send_message(
                "Mode switching is disabled for this bot instance.\n"
                f"This bot is locked to **{locked_mode}** mode.",
                ephemeral=True,
            )
            return

        mode_name = mode.value
        target_mode = resolve_mode_key(mode_name)

        if not target_mode:
            await interaction.response.send_message(
                f"Unknown mode: `{mode_name}`\n"
                "Use `/modes` to see available options!",
                ephemeral=True,
            )
            return

        current_mode = await get_server_mode(interaction.guild.id)
        if current_mode == target_mode:
            profile = get_mode_profile(target_mode)
            mode_icon = await self._get_mode_icon(target_mode)
            prefix = f"{mode_icon} " if mode_icon else ""
            await interaction.response.send_message(
                f"{prefix}Already in **{profile.display_name}** mode!"
            )
            return

        await set_server_mode(interaction.guild.id, target_mode)
        if target_mode == "mode_default":
            await set_evil_mode(interaction.guild.id, False)
        profile = get_mode_profile(target_mode)
        mode_icon = await self._get_mode_icon(target_mode)
        prefix = f"{mode_icon} " if mode_icon else ""
        await interaction.response.send_message(f"{prefix}{profile.switch_message}")
        try:
            await self._set_presence_for_mode(target_mode)
        except Exception as exc:
            logger.warning("Failed to update presence for %s: %s", target_mode, exc)
        try:
            from utils.server_avatar import set_mode_avatar
            evil_mode_enabled = await get_evil_mode(interaction.guild.id)
            success, reason = await set_mode_avatar(
                self.bot,
                interaction.guild.id,
                target_mode,
                evil_mode=evil_mode_enabled,
            )
            if not success and reason != "custom":
                logger.warning("Failed to update server avatar for %s: %s", target_mode, reason)
        except Exception as exc:
            logger.warning("Failed to update server avatar for %s: %s", target_mode, exc)

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

        embed.set_footer(text="Manage Guild permission required to change modes")
        await interaction.response.send_message(embed=embed)

    @commands.command(name="currentmode", aliases=["whatmode"])
    async def show_current_mode(self, ctx: commands.Context):
        """Display the current personality mode."""
        current_mode = await get_server_mode(ctx.guild.id)
        current_evil = await get_evil_mode(ctx.guild.id)
        profile = get_mode_profile(current_mode)
        mode_icon = await self._get_mode_icon(current_mode)
        prefix = f"{mode_icon} " if mode_icon else ""
        evil_text = " 😈 (Evil Mode Active)" if current_evil else ""

        await ctx.send(
            f"{prefix}Currently in **{profile.display_name}** mode!{evil_text}\n"
            f"*{profile.description}*"
        )

    @app_commands.command(name="currentmode", description="Show the current personality mode.")
    async def show_current_mode_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        current_mode = await get_server_mode(interaction.guild.id)
        current_evil = await get_evil_mode(interaction.guild.id)
        profile = get_mode_profile(current_mode)
        mode_icon = await self._get_mode_icon(current_mode)
        prefix = f"{mode_icon} " if mode_icon else ""
        evil_text = " 😈 (Evil Mode Active)" if current_evil else ""

        await interaction.response.send_message(
            f"{prefix}Currently in **{profile.display_name}** mode!{evil_text}\n"
            f"*{profile.description}*"
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
                    welcome_text = fallback_messages.get(mode, fallback_messages["mode_femboy"])
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
