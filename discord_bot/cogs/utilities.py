"""
Utilities Cog for Femmy Discord Bot
====================================
General utility commands including help, stats, translation, and more.

Commands:
    !help [command]  - Show help for all or specific commands
    !stats           - Display bot statistics
    !reload [cog]    - Reload cogs (owner only)
    !translate       - Translate text using Gemini
    !tldr [count]    - Summarize the last N messages
    !ping            - Check bot latency
    !about           - Display bot information
"""

import os
import asyncio
import json
import psutil
import re
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import get_server_mode, get_stats, increment_stat
from modes import get_mode_profile
from utils.guild_ai import (
    generate_guild_gemini_text,
    generate_guild_gemini_translate_text,
    generate_guild_gemini_summary_text,
    GuildConfigError,
)
from utils.rate_limiter import ai_limiter, get_rate_limit_message
from utils.logger import get_logger


# ============================================
# Command Inventory for Help
# ============================================

HELP_COMMANDS = {
    "ai": {
        "visibility": "public",
        "prefix": ["!describe", "!tldr"],
        "slash": ["/describe", "/tldr", "/generate image"],
    },
    "memory": {
        "visibility": "public",
        "prefix": ["!remember", "!forget", "!myinfo", "!set_timezone", "!birthday", "!aboutuser", "!aka", "!aliases", "!whois"],
        "slash": [
            "/remember",
            "/forget",
            "/myinfo",
            "/timezone",
            "/birthday",
            "/aboutuser",
            "/aka",
            "/aliases",
            "/whois",
            "/analyze",
            "/teach memory personal",
            "/teach memory server",
            "/teach attribute",
            "/teach sampledialogue",
            "/teach document",
            "/personal privacy",
        ],
    },
    "affection": {
        "visibility": "public",
        "prefix": ["!affection", "!mood", "!headpat", "!hug"],
        "slash": ["/affection", "/mood", "/headpat", "/hug"],
    },
    "personality": {
        "visibility": "public",
        "prefix": ["!modes", "!currentmode"],
        "slash": ["/modes", "/currentmode"],
    },
    "personality_admin": {
        "visibility": "admin",
        "prefix": ["!mode", "!evil"],
        "slash": ["/mode", "/evil"],
    },
    "utility": {
        "visibility": "public",
        "prefix": ["!help", "!ping", "!stats", "!usage", "!about", "!translate", "!remind", "!reminders"],
        "slash": ["/help", "/ping", "/stats", "/about", "/translate", "/tldr", "/generate_embed", "/remind", "/reminders", "/remindcancel", "/usage"],
    },
    "moderation": {
        "visibility": "admin",
        "prefix": ["!setbump", "!clearbump", "!sync"],
        "slash": ["/bumpchannel", "/bumpstart", "/bumpstop", "/automod add", "/automod remove", "/automod list", "/automod spam", "/starboard setup", "/starboard toggle", "/starboard ignore", "/starboard unignore", "/starboard ignored"],
    },
    "config": {
        "visibility": "admin",
        "prefix": ["!admin", "!reload"],
        "slash": [
            "/config auth",
            "/config password",
            "/config keys",
            "/config model",
            "/config env",
            "/config toggle",
            "/config url_safety",
            "/config ui",
            "/config custom_endpoint",
            "/admin reset",
            "/admin view",
            "/admin setfact",
            "/admin delfact",
            "/admin affection",
            "/admin model",
            "/admin clearglobal",
            "/admin clearguild",
            "/setgenderrole",
            "/avatar reset",
        ],
    },
    "tools": {
        "visibility": "admin",
        "prefix": [],
        "slash": ["/tools status"],
    },
    "staff": {
        "visibility": "admin",
        "prefix": [],
        "slash": ["/staff add", "/staff remove", "/staff list"],
    },
    "modlog": {
        "visibility": "admin",
        "prefix": [],
        "slash": ["/modlog set", "/modlog clear", "/modlog view"],
    },
    "autorole": {
        "visibility": "admin",
        "prefix": [],
        "slash": ["/autorole set", "/autorole clear", "/autorole view"],
    },
    "welcome": {
        "visibility": "admin",
        "prefix": [],
        "slash": [
            "/welcome channel",
            "/welcome clear",
            "/welcome test",
            "/welcome set_message",
            "/welcome view_message",
            "/welcome clear_message",
            "/welcome set_dm_message",
            "/welcome clear_dm_message",
            "/welcome toggle_dm",
        ],
    },
    "persona": {
        "visibility": "admin",
        "prefix": [],
        "slash": ["/persona create", "/persona list", "/persona preview", "/persona edit", "/persona delete"],
    },
}

HELP_INTROS = {
    "mode_default": "Here are my available commands:",
    "mode_femboy": "Here is everything I can do for you, Nii-chan~",
    "mode_tsundere": "Fine, here is what I can do, baka.",
    "mode_oneesan": "Let me show you what I can help you with, my dear.",
}


def build_help_lines(is_admin: bool) -> list[str]:
    lines = []
    for section, cmds in HELP_COMMANDS.items():
        visibility = cmds.get("visibility", "public")
        if visibility == "admin" and not is_admin:
            continue
        title = section.replace("_", " ").title()
        prefix_cmds = " ".join(cmds.get("prefix", []))
        slash_cmds = " ".join(cmds.get("slash", []))
        if prefix_cmds:
            lines.append(f"{title} (Prefix): {prefix_cmds}")
        if slash_cmds:
            lines.append(f"{title} (Slash): {slash_cmds}")
    return lines


logger = get_logger(__name__)

EMBED_JSON_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
EMBED_COLOR_MAP = {
    "red": "ff4d4d",
    "dark red": "8b0000",
    "maroon": "800000",
    "pink": "ff69b4",
    "hot pink": "ff1493",
    "purple": "9b59b6",
    "blue": "3498db",
    "cyan": "00bcd4",
    "teal": "1abc9c",
    "green": "2ecc71",
    "lime": "7fff00",
    "yellow": "f1c40f",
    "orange": "e67e22",
    "gold": "f4d03f",
    "black": "000000",
    "white": "ffffff",
    "gray": "7f8c8d",
    "grey": "7f8c8d",
}


def _extract_embed_json(text: str) -> dict | None:
    if not text:
        return None
    match = EMBED_JSON_PATTERN.search(text)
    payload = match.group(1) if match else None
    if payload:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None
    return None


def _parse_embed_color(value) -> discord.Color:
    if value is None:
        return discord.Color.default()
    if isinstance(value, int):
        return discord.Color(value)
    if not isinstance(value, str):
        return discord.Color.default()
    raw = value.strip().lower()
    if not raw:
        return discord.Color.default()
    if raw in EMBED_COLOR_MAP:
        raw = EMBED_COLOR_MAP[raw]
    if raw.startswith("#"):
        raw = raw[1:]
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) == 3 and all(c in "0123456789abcdef" for c in raw):
        raw = "".join(c * 2 for c in raw)
    if len(raw) == 6 and all(c in "0123456789abcdef" for c in raw):
        return discord.Color(int(raw, 16))
    return discord.Color.default()


async def _is_owner_check(interaction: discord.Interaction) -> bool:
    return await interaction.client.is_owner(interaction.user)


class Utilities(commands.Cog):
    """
    Utilities Cog - General purpose commands.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now()

    def _get_bot_name(self, mode: str) -> str:
        if mode == "mode_oneesan":
            return "Yumi"
        if mode == "mode_default":
            return "Clanker"
        return "Femmy"
    
    # ============================================
    # Help Command
    # ============================================
    
    @commands.command(name="help")
    async def custom_help(self, ctx: commands.Context, *, command_name: str = None):
        """
        Show help for all commands or a specific command.
        """
        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_default"
        
        if command_name:
            # Show help for specific command
            cmd = self.bot.get_command(command_name)
            if not cmd:
                await ctx.send(f"❌ Command `{command_name}` not found!")
                return
            
            embed = discord.Embed(
                title=f"📖 Help: !{cmd.name}",
                description=cmd.help or "No description available.",
                color=discord.Color.blue()
            )
            
            if cmd.aliases:
                embed.add_field(
                    name="Aliases",
                    value=", ".join(f"`!{a}`" for a in cmd.aliases),
                    inline=False
                )
            
            # Usage based on signature
            usage = f"!{cmd.name}"
            if cmd.signature:
                usage += f" {cmd.signature}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
            
            await ctx.send(embed=embed)
            return
        
        # Show all commands
        is_admin = bool(
            ctx.guild
            and (ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.administrator)
        )
        intro = HELP_INTROS.get(mode, HELP_INTROS["mode_default"])
        lines = build_help_lines(is_admin)

        bot_name = self._get_bot_name(mode)
        description = "\n".join([
            intro,
            *lines,
            "Use !help <command> for more details on a specific command",
        ])
        embed = discord.Embed(
            title=f"???? {bot_name}'s Commands",
            description=description,
            color=discord.Color.pink()
        )

        await ctx.send(embed=embed)
    
    # ============================================
    # Stats Command
    # ============================================
    
    @commands.command(name="stats", aliases=["status", "botstats"])
    async def show_stats(self, ctx: commands.Context):
        """Display bot statistics and uptime."""
        stats = await get_stats()
        
        # Calculate uptime
        now = datetime.now()
        uptime = now - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            uptime_str = f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            uptime_str = f"{hours}h {minutes}m {seconds}s"
        else:
            uptime_str = f"{minutes}m {seconds}s"
        
        # Memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Count users
        total_users = sum(g.member_count or 0 for g in self.bot.guilds)
        
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="🏠 Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Users", value=f"{total_users:,}", inline=True)
        
        embed.add_field(
            name="💬 Messages Processed",
            value=f"{stats.get('messages_processed', 0):,}",
            inline=True
        )
        embed.add_field(
            name="🖼️ Images Analyzed",
            value=f"{stats.get('images_analyzed', 0):,}",
            inline=True
        )
        embed.add_field(
            name="💾 Memory",
            value=f"{memory_mb:.1f} MB",
            inline=True
        )
        
        # Get current mode
        if ctx.guild:
            mode = await get_server_mode(ctx.guild.id)
            mode_display = {
                "mode_femboy": "🎀 Femboy",
                "mode_tsundere": "😤 Tsundere",
                "mode_oneesan": "💕 Onee-san"
            }
            embed.add_field(
                name="🎭 Current Mode",
                value=mode_display.get(mode, mode),
                inline=True
            )
        
        embed.set_footer(text="Powered by Gemini AI ♡")
        
        await ctx.send(embed=embed)
    
    # ============================================
    # Reload Command
    # ============================================
    
    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx: commands.Context, cog_name: str = None):
        """
        Reload a cog or all cogs. (Owner only)
        
        Usage:
            !reload ai_brain - Reload specific cog
            !reload all      - Reload all cogs
            !reload          - List available cogs
        """
        cogs_dir = Path(__file__).parent
        available_cogs = [
            p.stem for p in cogs_dir.glob("*.py")
            if p.stem != "__init__" and not p.stem.startswith("_")
        ]
        
        if cog_name is None:
            # List available cogs
            cog_list = ", ".join(f"`{c}`" for c in sorted(available_cogs))
            await ctx.send(
                f"**Available cogs:**\n{cog_list}\n\n"
                f"Use `!reload <cog>` or `!reload all`"
            )
            return
        
        if cog_name.lower() == "all":
            # Reload all cogs
            success = []
            failed = []
            
            for cog in available_cogs:
                try:
                    await self.bot.reload_extension(f"cogs.{cog}")
                    success.append(cog)
                except Exception as e:
                    failed.append(f"{cog}: {str(e)[:50]}")
            
            result = f"✅ Reloaded: {', '.join(success)}"
            if failed:
                result += f"\n❌ Failed: {', '.join(failed)}"
            
            await ctx.send(result)
            return
        
        # Reload specific cog
        cog_name = cog_name.lower()
        if cog_name not in available_cogs:
            await ctx.send(f"❌ Cog `{cog_name}` not found!")
            return
        
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Reloaded `{cog_name}`!")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload `{cog_name}`: {e}")
    
    # ============================================
    # Translate Command
    # ============================================
    
    @commands.command(name="translate", aliases=["tr"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def translate(self, ctx: commands.Context, *, query: str):
        """
        Translate text to another language.
        
        Usage:
            !translate hello world to japanese
            !translate こんにちは to english
            !translate Bonjour to spanish
        """
        # Parse "to <language>" pattern
        if " to " not in query.lower():
            await ctx.send(
                "**Usage:** `!translate <text> to <language>`\n"
                "**Example:** `!translate hello world to japanese`"
            )
            return
        
        # Split on last "to"
        parts = query.lower().rsplit(" to ", 1)
        text = query[:query.lower().rfind(" to ")]
        target_lang = parts[1].strip()
        
        if not text or not target_lang:
            await ctx.send("❌ Please provide both text and target language!")
            return

        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_default"
        if not await ai_limiter.acquire(ctx.author.id):
            retry_after = ai_limiter.get_retry_after(ctx.author.id)
            await ctx.send(get_rate_limit_message(mode, retry_after))
            return
        
        async with ctx.typing():
            prompt = f"""
Translate the following text to {target_lang}.
Only output the translation, nothing else.
If you cannot translate, say "Translation not possible."

Text to translate:
{text}
"""
            
            try:
                translation, _ = await generate_guild_gemini_translate_text(ctx.guild.id, prompt)
                translation = translation.strip()
            except RuntimeError:
                await ctx.send("? Translation service busy, try again later!")
                return
            except GuildConfigError:
                await ctx.send(
                    "? This server hasn't configured Gemini keys yet. "
                    "Ask an admin to upload keys with /config env upload."
                )
                return
            except Exception as e:
                await ctx.send(f"? Translation failed: {e}")
                return
        
        embed = discord.Embed(
            title="🌐 Translation",
            color=discord.Color.blue()
        )
        embed.add_field(name="Original", value=text[:1024], inline=False)
        embed.add_field(name=f"→ {target_lang.title()}", value=translation[:1024], inline=False)
        
        await ctx.send(embed=embed)

        try:
            await increment_stat("messages_processed", guild_id=ctx.guild.id if ctx.guild else None)
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)
    
    # ============================================
    # Existing Commands (tldr, ping, about)
    # ============================================
    
    @commands.command(name="tldr", aliases=["summarize", "summary"])
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def summarize_messages(self, ctx: commands.Context, count: int = 50):
        """Summarize the last N messages in the channel."""
        if count < 5:
            await ctx.send("❌ Need at least 5 messages to summarize!")
            return
        
        if count > 100:
            count = 100

        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_default"
        if not await ai_limiter.acquire(ctx.author.id):
            retry_after = ai_limiter.get_retry_after(ctx.author.id)
            await ctx.send(get_rate_limit_message(mode, retry_after))
            return
        
        async with ctx.typing():
            messages = []
            async for message in ctx.channel.history(limit=count, before=ctx.message):
                if not message.author.bot:
                    messages.append(f"{message.author.display_name}: {message.content}")
            
            if len(messages) < 5:
                await ctx.send("❌ Not enough non-bot messages to summarize!")
                return
            
            conversation_text = "\n".join(reversed(messages))
            prompt = f"""
Summarize the following Discord conversation in a concise, easy-to-read format.
Highlight key topics, decisions, and any action items.
Keep the summary under 300 words.

Conversation:
{conversation_text}

Provide a clear, bulleted summary:
"""
            
            try:
                summary, _ = await generate_guild_gemini_summary_text(ctx.guild.id, prompt)
            except RuntimeError:
                await ctx.send("? Summary service busy, try again later!")
                return
            except GuildConfigError:
                await ctx.send(
                    "? This server hasn't configured Gemini keys yet. "
                    "Ask an admin to upload keys with /config env upload."
                )
                return
            except Exception as e:
                await ctx.send(f"? Error generating summary: {e}")
                return
        
        embed = discord.Embed(
            title=f"📋 TL;DR - Last {len(messages)} messages",
            description=summary,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

        try:
            await increment_stat("messages_processed", guild_id=ctx.guild.id if ctx.guild else None)
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)
    
    
    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)
        emoji = "🟢" if latency < 100 else "🟡" if latency < 200 else "🔴"
        await ctx.send(f"{emoji} Pong! Latency: **{latency}ms**")
    
    @commands.command(name="about", aliases=["info", "botinfo"])
    async def about(self, ctx: commands.Context):
        """Display information about the bot."""
        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_default"
        bot_name = self._get_bot_name(mode)
        bio = None
        if ctx.guild:
            bios = getattr(self.bot, "mode_bio_by_guild", None) or {}
            bio = bios.get(ctx.guild.id)
        if not bio:
            bio = get_mode_profile(mode).bio
        embed = discord.Embed(
            title=f"🤖 About {bot_name}",
            description=f"{bio}\n\nAn advanced AI Discord bot with multiple personalities!",
            color=discord.Color.pink()
        )
        
        embed.add_field(
            name="✨ Features",
            value=(
                "• Three personality modes\n"
                "• AI-powered conversations\n"
                "• Image analysis\n"
                "• Affection & Mood system\n"
                "• Reminders & Translation"
            ),
            inline=False
        )
        
        embed.add_field(name="📊 Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="🔗 Commands", value="Use `!help`", inline=True)
        embed.set_footer(text="Powered by Gemini AI ♡")
        
        await ctx.send(embed=embed)

    @app_commands.command(name="help", description="Show help for commands.")
    @app_commands.describe(command_name="Specific command to show help for")
    async def custom_help_slash(self, interaction: discord.Interaction, command_name: str = None):
        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_default"

        if command_name:
            cmd = self.bot.get_command(command_name)
            if not cmd:
                await interaction.response.send_message(
                    f"❌ Command `{command_name}` not found!",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title=f"📖 Help: !{cmd.name}",
                description=cmd.help or "No description available.",
                color=discord.Color.blue(),
            )

            if cmd.aliases:
                embed.add_field(
                    name="Aliases",
                    value=", ".join(f"`!{a}`" for a in cmd.aliases),
                    inline=False,
                )

            usage = f"!{cmd.name}"
            if cmd.signature:
                usage += f" {cmd.signature}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)

            await interaction.response.send_message(embed=embed)
            return

        is_admin = bool(
            interaction.guild
            and (interaction.user.guild_permissions.manage_guild or interaction.user.guild_permissions.administrator)
        )
        intro = HELP_INTROS.get(mode, HELP_INTROS["mode_default"])
        lines = build_help_lines(is_admin)
        bot_name = self._get_bot_name(mode)
        description = "\n".join([
            intro,
            *lines,
            "Use !help <command> for more details on a specific command",
        ])
        embed = discord.Embed(
            title=f"???? {bot_name}'s Commands",
            description=description,
            color=discord.Color.pink(),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="Display bot statistics.")
    async def show_stats_slash(self, interaction: discord.Interaction):
        stats = await get_stats()

        now = datetime.now()
        uptime = now - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            uptime_str = f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            uptime_str = f"{hours}h {minutes}m {seconds}s"
        else:
            uptime_str = f"{minutes}m {seconds}s"

        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        total_users = sum(g.member_count or 0 for g in self.bot.guilds)

        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=discord.Color.blue(),
        )

        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="🏠 Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Users", value=f"{total_users:,}", inline=True)

        embed.add_field(
            name="💬 Messages Processed",
            value=f"{stats.get('messages_processed', 0):,}",
            inline=True,
        )
        embed.add_field(
            name="🖼️ Images Analyzed",
            value=f"{stats.get('images_analyzed', 0):,}",
            inline=True,
        )
        embed.add_field(
            name="💾 Memory",
            value=f"{memory_mb:.1f} MB",
            inline=True,
        )

        if interaction.guild:
            mode = await get_server_mode(interaction.guild.id)
            mode_display = {
                "mode_femboy": "🎀 Femboy",
                "mode_tsundere": "😤 Tsundere",
                "mode_oneesan": "💖 Onee-san",
            }
            embed.add_field(
                name="🎭 Current Mode",
                value=mode_display.get(mode, mode),
                inline=True,
            )

        embed.set_footer(text="Powered by Gemini AI ♡")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reload", description="Reload a cog or all cogs (owner only).")
    @app_commands.describe(cog_name="Cog name or 'all'")
    @app_commands.check(_is_owner_check)
    async def reload_cog_slash(self, interaction: discord.Interaction, cog_name: str = None):
        await interaction.response.defer(thinking=True)

        cogs_dir = Path(__file__).parent
        available_cogs = [
            p.stem for p in cogs_dir.glob("*.py")
            if p.stem != "__init__" and not p.stem.startswith("_")
        ]

        if cog_name is None:
            cog_list = ", ".join(f"`{c}`" for c in sorted(available_cogs))
            await interaction.followup.send(
                f"**Available cogs:**\n{cog_list}\n\n"
                f"Use `!reload <cog>` or `!reload all`"
            )
            return

        if cog_name.lower() == "all":
            success = []
            failed = []

            for cog in available_cogs:
                try:
                    await self.bot.reload_extension(f"cogs.{cog}")
                    success.append(cog)
                except Exception as e:
                    failed.append(f"{cog}: {str(e)[:50]}")

            result = f"✅ Reloaded: {', '.join(success)}"
            if failed:
                result += f"\n❌ Failed: {', '.join(failed)}"
            await interaction.followup.send(result)
            return

        cog_name = cog_name.lower()
        if cog_name not in available_cogs:
            await interaction.followup.send(f"❌ Cog `{cog_name}` not found!")
            return

        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await interaction.followup.send(f"✅ Reloaded `{cog_name}`!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to reload `{cog_name}`: {e}")

    @app_commands.command(name="translate", description="Translate text to another language.")
    @app_commands.describe(query="Text and target language, e.g. 'hello to japanese'")
    async def translate_slash(self, interaction: discord.Interaction, query: str):
        if " to " not in query.lower():
            await interaction.response.send_message(
                "**Usage:** `!translate <text> to <language>`\n"
                "**Example:** `!translate hello to japanese`",
                ephemeral=True,
            )
            return

        parts = query.lower().rsplit(" to ", 1)
        text = query[:query.lower().rfind(" to ")]
        target_lang = parts[1].strip()

        if not text or not target_lang:
            await interaction.response.send_message(
                "? Please provide both text and target language!",
                ephemeral=True,
            )
            return

        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_default"
        if not await ai_limiter.acquire(interaction.user.id):
            retry_after = ai_limiter.get_retry_after(interaction.user.id)
            await interaction.response.send_message(
                get_rate_limit_message(mode, retry_after),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        prompt = f"""
Translate the following text to {target_lang}.
Only output the translation, nothing else.
If you cannot translate, say "Translation not possible."

Text to translate:
{text}
"""

        try:
            translation, _ = await generate_guild_gemini_translate_text(interaction.guild.id, prompt)
            translation = translation.strip()
        except RuntimeError:
            await interaction.followup.send(
                "? Translation service busy, try again later!",
                ephemeral=True,
            )
            return
        except GuildConfigError:
            await interaction.followup.send(
                "? This server hasn't configured Gemini keys yet. "
                "Ask an admin to upload keys with /config env upload.",
                ephemeral=True,
            )
            return
        except Exception as e:
            await interaction.followup.send(
                f"? Translation failed: {e}",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="?? Translation",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Original", value=text[:1024], inline=False)
        embed.add_field(name=f"? {target_lang.title()}", value=translation[:1024], inline=False)

        await interaction.followup.send(embed=embed)

        try:
            await increment_stat(
                "messages_processed",
                guild_id=interaction.guild.id if interaction.guild else None,
            )
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)

    @app_commands.command(name="generate_embed", description="Describe an embed and I'll build it.")
    @app_commands.describe(prompt="Describe the embed (title, color, fields, footer, etc.)")
    async def generate_embed_slash(self, interaction: discord.Interaction, prompt: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "Missing permissions: Manage Messages.",
                ephemeral=True,
            )
            return

        mode = await get_server_mode(interaction.guild.id)
        if not await ai_limiter.acquire(interaction.user.id):
            retry_after = ai_limiter.get_retry_after(interaction.user.id)
            await interaction.response.send_message(
                get_rate_limit_message(mode, retry_after),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        ai_prompt = f"""
You are a JSON generator for Discord embeds.
Return a single JSON object with this schema:
{{
  "title": "string",
  "description": "string",
  "color": "hex string like #FF00FF or 0xFF00FF (convert color names to hex)",
  "fields": [{{"name": "string", "value": "string", "inline": false}}],
  "footer": "string"
}}

Rules:
- Output ONLY valid JSON. No markdown, no commentary.
- Omit fields that are not requested (use empty strings or empty list).
- Max 25 fields.
- Keep field values concise.

User request:
{prompt}
"""

        try:
            response_text, _ = await generate_guild_gemini_text(interaction.guild.id, ai_prompt)
        except RuntimeError:
            await interaction.followup.send(
                "Embed generator busy, try again later.",
                ephemeral=True,
            )
            return
        except GuildConfigError:
            await interaction.followup.send(
                "This server hasn't configured Gemini keys yet. "
                "Ask an admin to upload keys with /config env upload.",
                ephemeral=True,
            )
            return
        except Exception as e:
            await interaction.followup.send(f"Embed generation failed: {e}", ephemeral=True)
            return

        data = _extract_embed_json(response_text)
        if not data:
            await interaction.followup.send(
                "AI didn't return valid embed JSON. Try rephrasing.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=(data.get("title") or None),
            description=(data.get("description") or None),
            color=_parse_embed_color(data.get("color")),
        )

        fields = data.get("fields") or []
        if isinstance(fields, list):
            for field in fields[:25]:
                if not isinstance(field, dict):
                    continue
                name = str(field.get("name") or "").strip()
                value = str(field.get("value") or "").strip()
                if not name or not value:
                    continue
                inline = bool(field.get("inline")) if "inline" in field else False
                embed.add_field(name=name[:256], value=value[:1024], inline=inline)

        footer = data.get("footer")
        if footer:
            embed.set_footer(text=str(footer)[:2048])

        await interaction.followup.send(embed=embed)

        try:
            await increment_stat(
                "messages_processed",
                guild_id=interaction.guild.id if interaction.guild else None,
            )
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)
    @app_commands.command(name="tldr", description="Summarize the last N messages.")
    @app_commands.describe(count="Number of messages to summarize (5-100)")
    async def summarize_messages_slash(self, interaction: discord.Interaction, count: int = 50):
        if count < 5:
            await interaction.response.send_message("Need at least 5 messages to summarize!", ephemeral=True)
            return
        if count > 100:
            count = 100

        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_default"
        if not await ai_limiter.acquire(interaction.user.id):
            retry_after = ai_limiter.get_retry_after(interaction.user.id)
            await interaction.response.send_message(get_rate_limit_message(mode, retry_after), ephemeral=True)
            return

        await interaction.response.defer()
        messages = []
        channel = interaction.channel
        if channel is None:
            await interaction.followup.send("Can't access channel history.")
            return

        async for message in channel.history(limit=count, before=interaction.created_at):
            if not message.author.bot:
                messages.append(f"{message.author.display_name}: {message.content}")

        if len(messages) < 5:
            await interaction.followup.send("Not enough non-bot messages to summarize!")
            return

        conversation_text = "\n".join(reversed(messages))
        prompt = f"""
Summarize the following Discord conversation in a concise, easy-to-read format.
Highlight key topics, decisions, and any action items.
Keep the summary under 300 words.

Conversation:
{conversation_text}

Provide a clear, bulleted summary:
"""

        try:
            summary, _ = await generate_guild_gemini_summary_text(interaction.guild.id, prompt)
        except RuntimeError:
            await interaction.followup.send("Summary service busy, try again later!")
            return
        except GuildConfigError:
            await interaction.followup.send(
                "This server hasn't configured Gemini keys yet. "
                "Ask an admin to upload keys with /config env upload.",
                ephemeral=True,
            )
            return
        except Exception as e:
            await interaction.followup.send(f"Error generating summary: {e}")
            return

        embed = discord.Embed(
            title=f"TL;DR - Last {len(messages)} messages",
            description=summary,
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

        try:
            await increment_stat(
                "messages_processed",
                guild_id=interaction.guild.id if interaction.guild else None,
            )
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)
    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        emoji = "🟢" if latency < 100 else "🟡" if latency < 200 else "🔴"
        await interaction.response.send_message(f"{emoji} Pong! Latency: **{latency}ms**")

    @app_commands.command(name="about", description="Display information about the bot.")
    async def about_slash(self, interaction: discord.Interaction):
        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_default"
        bot_name = self._get_bot_name(mode)
        bio = None
        if interaction.guild:
            bios = getattr(self.bot, "mode_bio_by_guild", None) or {}
            bio = bios.get(interaction.guild.id)
        if not bio:
            bio = get_mode_profile(mode).bio
        embed = discord.Embed(
            title=f"🤖 About {bot_name}",
            description=f"{bio}\n\nAn advanced AI Discord bot with multiple personalities!",
            color=discord.Color.pink(),
        )

        embed.add_field(
            name="✨ Features",
            value=(
                "• Three personality modes\n"
                "• AI-powered conversations\n"
                "• Image analysis\n"
                "• Affection & Mood system\n"
                "• Reminders & Translation"
            ),
            inline=False,
        )

        embed.add_field(name="📊 Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="🔗 Commands", value="Use `!help`", inline=True)
        embed.set_footer(text="Powered by Gemini AI ♡")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Load the Utilities cog."""
    await bot.add_cog(Utilities(bot))
