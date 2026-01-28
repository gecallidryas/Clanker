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
    FEMMY_EMOJI_PREFIX,
    YUMI_EMOJI_PREFIX,
)
from utils.db_handler import get_server_mode, set_server_mode, get_evil_mode, set_evil_mode


# Mode display information
MODE_INFO = {
    "mode_femboy": {
        "name": "Obedient Femboy Brother",
        "emoji": "🎀",
        "description": "Submissive, cute, energetic, and helpful. Calls you Nii-chan/Onee-chan~",
        "aliases": ["femboy", "bro", "brother"]
    },
    "mode_tsundere": {
        "name": "Tsundere Younger Sister",
        "emoji": "😤",
        "description": "It's not like I want to help you or anything! Baka!",
        "aliases": ["tsundere", "tsun", "sis"]
    },
    "mode_oneesan": {
        "name": "Caring Older Sister",
        "emoji": "💕",
        "description": "Ara ara~ Mature, soothing, and motherly. Makes sure you're eating well~",
        "aliases": ["oneesan", "onesan", "big sis", "ara"]
    }
}

# Mention reactions per mode (used when the bot is mentioned without a message)
MENTION_REACTIONS = {
    "mode_femboy": [
        "Hi hi! Need me, Nii-chan? I'm right here~",
        "Ehehe, you called? I'm ready to help!",
        "I'm here! Tell me what you need and I'll do my best~"
    ],
    "mode_tsundere": [
        "Hmph. What is it? It's not like I wanted to respond or anything.",
        "Baka... you called me for that? Fine, what do you want?",
        "Don't just ping me for no reason... say what you need."
    ],
    "mode_oneesan": [
        "Ara ara~ Yes, my dear? How can I help you?",
        "I'm here, little one. What do you need?",
        "Did you call for me? I'm listening, dear."
    ]
}


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
        if mode_key == "mode_femboy":
            prefix = FEMMY_EMOJI_PREFIX
        elif mode_key == "mode_oneesan":
            prefix = YUMI_EMOJI_PREFIX
        else:
            prefix = ""

        if prefix:
            emojis = await self._get_app_emojis_by_prefix(prefix)
            for emoji in emojis:
                token = format_custom_emoji(emoji)
                if token:
                    return token

        return MODE_INFO.get(mode_key, MODE_INFO["mode_femboy"])["emoji"]

    def _is_mention_only(self, message: discord.Message) -> bool:
        """Return True when the message only mentions the bot."""
        content = message.content
        content = content.replace(f"<@{self.bot.user.id}>", "")
        content = content.replace(f"<@!{self.bot.user.id}>", "")
        return content.strip() == ""
    
    @commands.command(name="evil", aliases=["uncensored"])
    @commands.has_permissions(manage_guild=True)
    async def toggle_evil_mode(self, ctx: commands.Context, state: str = None):
        """
        Toggle 'Evil' (Uncensored) mode using OpenRouter models.
        
        Usage: !evil [on/off]
        """
        if not state:
            current = await get_evil_mode(ctx.guild.id)
            status = "ENABLED" if current else "DISABLED"
            await ctx.send(f"😈 Evil Mode is currently **{status}**.")
            return

        state = state.lower()
        if state in ["on", "enable", "true", "yes"]:
            await set_evil_mode(ctx.guild.id, True)
            await ctx.send("😈 **Evil Mode ENABLED**. Responses will now use uncensored models (Venice/Hermes).")
        elif state in ["off", "disable", "false", "no"]:
            await set_evil_mode(ctx.guild.id, False)
            await ctx.send("😇 **Evil Mode DISABLED**. Returning to standard safety protocols.")
        else:
            await ctx.send("Usage: `!evil on` or `!evil off`")

    @app_commands.command(name="evil", description="Toggle uncensored (evil) mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(state="on/off")
    async def toggle_evil_mode_slash(self, interaction: discord.Interaction, state: str = None):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
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
                "😈 **Evil Mode ENABLED**. Responses will now use uncensored models (Venice/Hermes)."
            )
        elif state in ["off", "disable", "false", "no"]:
            await set_evil_mode(interaction.guild.id, False)
            await interaction.response.send_message(
                "😇 **Evil Mode DISABLED**. Returning to standard safety protocols."
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
                "🔒 Mode switching is disabled for this bot instance.\n"
                f"This bot is locked to **{locked_mode}** mode."
            )
            return
        
        if not mode_name:
            await self.show_modes(ctx)
            return
        
        # Normalize mode name
        mode_name = mode_name.lower().strip()
        
        # Find matching mode
        target_mode = None
        for mode_key, info in MODE_INFO.items():
            if mode_name in info["aliases"] or mode_name == mode_key:
                target_mode = mode_key
                break
        
        if not target_mode:
            await ctx.send(
                f"❌ Unknown mode: `{mode_name}`\n"
                f"Use `!modes` to see available options!"
            )
            return
        
        # Check if already in this mode
        current_mode = await get_server_mode(ctx.guild.id)
        if current_mode == target_mode:
            mode_info = MODE_INFO[target_mode]
            mode_icon = await self._get_mode_icon(target_mode)
            await ctx.send(
                f"{mode_icon} Already in **{mode_info['name']}** mode!"
            )
            return
        
        # Switch mode
        await set_server_mode(ctx.guild.id, target_mode)
        
        mode_info = MODE_INFO[target_mode]
        mode_icon = await self._get_mode_icon(target_mode)
        
        # Send personality-appropriate confirmation
        confirmations = {
            "mode_femboy": f"{mode_icon} Mode switched! Ehehe~ I'll be your cute little sibling now, Nii-chan! ♡",
            "mode_tsundere": f"{mode_icon} F-fine! I switched modes... It's not like I wanted to or anything! Hmph!",
            "mode_oneesan": f"{mode_icon} Ara ara~ Mode changed, my dear. Let me take care of you now~ 💕"
        }
        
        await ctx.send(confirmations.get(target_mode, f"{mode_icon} Mode switched!"))

    @app_commands.command(name="mode", description="Switch the bot's personality mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(mode="Personality mode")
    @app_commands.choices(mode=[
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
                "🔒 Mode switching is disabled for this bot instance.\n"
                f"This bot is locked to **{locked_mode}** mode.",
                ephemeral=True,
            )
            return

        mode_name = mode.value
        target_mode = None
        for mode_key, info in MODE_INFO.items():
            if mode_name in info["aliases"] or mode_name == mode_key:
                target_mode = mode_key
                break

        if not target_mode:
            await interaction.response.send_message(
                f"❌ Unknown mode: `{mode_name}`\nUse `/modes` to see available options!",
                ephemeral=True,
            )
            return

        current_mode = await get_server_mode(interaction.guild.id)
        if current_mode == target_mode:
            mode_info = MODE_INFO[target_mode]
            mode_icon = await self._get_mode_icon(target_mode)
            await interaction.response.send_message(
                f"{mode_icon} Already in **{mode_info['name']}** mode!"
            )
            return

        await set_server_mode(interaction.guild.id, target_mode)
        mode_info = MODE_INFO[target_mode]
        mode_icon = await self._get_mode_icon(target_mode)
        confirmations = {
            "mode_femboy": f"{mode_icon} Mode switched! Ehehe~ I'll be your cute little sibling now, Nii-chan! ♡",
            "mode_tsundere": f"{mode_icon} F-fine! I switched modes... It's not like I wanted to or anything! Hmph!",
            "mode_oneesan": f"{mode_icon} Ara ara~ Mode changed, my dear. Let me take care of you now~ 💕",
        }
        await interaction.response.send_message(confirmations.get(target_mode, f"{mode_icon} Mode switched!"))

    @commands.command(name="modes", aliases=["personalities", "personas"])
    async def show_modes(self, ctx: commands.Context):
        """
        Display all available personality modes.
        
        TODO:
            - [ ] Add mode preview
            - [ ] Show current mode
        """
        current_mode = await get_server_mode(ctx.guild.id)
        current_evil = await get_evil_mode(ctx.guild.id)
        
        embed = discord.Embed(
            title="🎭 Available Personality Modes",
            description="Switch Femmy's personality with `!mode <name>`",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        
        evil_status = "😈 **Evil Mode**: ON" if current_evil else "😇 **Evil Mode**: OFF"
        embed.add_field(name="System Status", value=evil_status, inline=False)
        
        for mode_key, info in MODE_INFO.items():
            is_current = mode_key == current_mode
            marker = " ← Current" if is_current else ""
            mode_icon = await self._get_mode_icon(mode_key)
            
            embed.add_field(
                name=f"{mode_icon} {info['name']}{marker}",
                value=f"{info['description']}\n*Aliases: {', '.join(info['aliases'])}*",
                inline=False
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
            title="🎭 Available Personality Modes",
            description="Switch Femmy's personality with `/mode`",
            color=discord.Color.from_rgb(255, 182, 193),
        )

        evil_status = "😈 **Evil Mode**: ON" if current_evil else "😇 **Evil Mode**: OFF"
        embed.add_field(name="System Status", value=evil_status, inline=False)

        for mode_key, info in MODE_INFO.items():
            is_current = mode_key == current_mode
            marker = " ← Current" if is_current else ""
            mode_icon = await self._get_mode_icon(mode_key)

            embed.add_field(
                name=f"{mode_icon} {info['name']}{marker}",
                value=f"{info['description']}\n*Aliases: {', '.join(info['aliases'])}*",
                inline=False,
            )

        embed.set_footer(text="Manage Guild permission required to change modes")
        await interaction.response.send_message(embed=embed)
    
    @commands.command(name="currentmode", aliases=["whatmode"])
    async def show_current_mode(self, ctx: commands.Context):
        """Display the current personality mode."""
        current_mode = await get_server_mode(ctx.guild.id)
        current_evil = await get_evil_mode(ctx.guild.id)
        info = MODE_INFO.get(current_mode, MODE_INFO["mode_femboy"])
        mode_icon = await self._get_mode_icon(current_mode)
        
        evil_text = "\n😈 (Evil Mode Active)" if current_evil else ""
        
        await ctx.send(
            f"{mode_icon} Currently in **{info['name']}** mode!{evil_text}\n"
            f"*{info['description']}*"
        )

    @app_commands.command(name="currentmode", description="Show the current personality mode.")
    async def show_current_mode_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        current_mode = await get_server_mode(interaction.guild.id)
        current_evil = await get_evil_mode(interaction.guild.id)
        info = MODE_INFO.get(current_mode, MODE_INFO["mode_femboy"])
        mode_icon = await self._get_mode_icon(current_mode)
        evil_text = "\n😈 (Evil Mode Active)" if current_evil else ""

        await interaction.response.send_message(
            f"{mode_icon} Currently in **{info['name']}** mode!{evil_text}\n"
            f"*{info['description']}*"
        )
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Send a welcome message when a new member joins.
        Message style based on current persona.
        
        TODO:
            - [ ] Make this configurable per server
            - [ ] Add welcome channel configuration
            - [ ] Implement welcome DMs
        """
        # Get current mode for this server
        mode = await get_server_mode(member.guild.id)
        
        # Personality-based welcome messages
        welcomes = {
            "mode_femboy": f"Welcome to the server, {member.mention}! I hope we can be great friends~ ♡ Let me know if you need any help, I'd love to assist you! ✨",
            "mode_tsundere": f"Oh, {member.mention} joined... I guess you can stay. It's not like we wanted more members or anything! ...Welcome.",
            "mode_oneesan": f"Ara ara~ Welcome, {member.mention}! Make yourself at home, my dear. If you need anything at all, don't hesitate to ask~ 💕"
        }
        
        # Find system channel
        if member.guild.system_channel:
            try:
                await member.guild.system_channel.send(welcomes.get(mode, welcomes["mode_femboy"]))
            except discord.Forbidden:
                pass

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
        responses = MENTION_REACTIONS.get(mode, MENTION_REACTIONS["mode_femboy"])
        await message.reply(random.choice(responses), mention_author=False)


async def setup(bot: commands.Bot):
    """Load the Social cog."""
    await bot.add_cog(Social(bot))
