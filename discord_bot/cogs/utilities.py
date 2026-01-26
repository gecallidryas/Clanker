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
    !portfolio       - Check portfolio website status
    !ping            - Check bot latency
    !about           - Display bot information
"""

import os
import asyncio
import psutil
from datetime import datetime
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import get_server_mode, get_stats, increment_stat
from utils.api_manager import get_gemini_manager, get_gemini_translate_manager
from utils.rate_limiter import ai_limiter, get_rate_limit_message
from utils.logger import get_logger


# ============================================
# Command Categories for Help
# ============================================

COMMAND_CATEGORIES = {
    "🧠 AI & Chat": {
        "description": "Talk to me by mentioning me!",
        "commands": ["describe", "tldr"]
    },
    "💭 Memory": {
        "description": "I can remember things about you~",
        "commands": ["remember", "forget", "myinfo", "set_timezone", "birthday", "aboutuser", "aka", "aliases", "whois"]
    },
    "💕 Affection": {
        "description": "Build our relationship!",
        "commands": ["affection", "mood", "headpat", "hug"]
    },
    "🎭 Personality": {
        "description": "Change my personality mode~",
        "commands": ["mode", "modes", "currentmode"]
    },
    "🛠️ Utility": {
        "description": "Helpful tools and features",
        "commands": ["help", "ping", "stats", "about", "portfolio", "translate", "remind", "reminders"]
    },
    "🔧 Admin": {
        "description": "Server management (requires permissions)",
        "commands": ["reload", "setbump", "clearbump"]
    }
}

HELP_INTROS = {
    "mode_femboy": "Here's everything I can do for you, Nii-chan~ ♡",
    "mode_tsundere": "Fine, I'll tell you what I can do. It's not like I want to show off or anything!",
    "mode_oneesan": "Ara ara~ Let me show you what I can help you with, dear~"
}

logger = get_logger(__name__)


class Utilities(commands.Cog):
    """
    Utilities Cog - General purpose commands.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gemini = get_gemini_manager()
        try:
            self.translate_client = get_gemini_translate_manager()
        except ValueError:
            self.translate_client = None
        self.portfolio_url = os.getenv("PORTFOLIO_URL", "")
        self.start_time = datetime.now()

    def _get_bot_name(self, mode: str) -> str:
        if mode == "mode_oneesan":
            return "Yumi"
        if self.bot.user:
            return self.bot.user.display_name
        return "Femmy"
    
    # ============================================
    # Help Command
    # ============================================
    
    @commands.command(name="help")
    async def custom_help(self, ctx: commands.Context, *, command_name: str = None):
        """
        Show help for all commands or a specific command.
        """
        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_femboy"
        
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
        intro = HELP_INTROS.get(mode, HELP_INTROS["mode_femboy"])
        
        bot_name = self._get_bot_name(mode)
        embed = discord.Embed(
            title=f"📚 {bot_name}'s Commands",
            description=intro,
            color=discord.Color.pink()
        )
        
        for category_name, category_data in COMMAND_CATEGORIES.items():
            # Get commands that exist
            valid_commands = []
            for cmd_name in category_data["commands"]:
                cmd = self.bot.get_command(cmd_name)
                if cmd and not cmd.hidden:
                    valid_commands.append(f"`!{cmd_name}`")
            
            if valid_commands:
                embed.add_field(
                    name=f"{category_name}",
                    value=" ".join(valid_commands),
                    inline=False
                )
        
        embed.set_footer(text="Use !help <command> for more details on a specific command")
        
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

        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_femboy"
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
                client = self.translate_client or self.gemini
                translation, _ = await client.generate(prompt)
                translation = translation.strip()
            except RuntimeError:
                await ctx.send("❌ Translation service busy, try again later!")
                return
            except Exception as e:
                await ctx.send(f"❌ Translation failed: {e}")
                return
        
        embed = discord.Embed(
            title="🌐 Translation",
            color=discord.Color.blue()
        )
        embed.add_field(name="Original", value=text[:1024], inline=False)
        embed.add_field(name=f"→ {target_lang.title()}", value=translation[:1024], inline=False)
        
        await ctx.send(embed=embed)

        try:
            await increment_stat("messages_processed")
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)
    
    # ============================================
    # Existing Commands (tldr, portfolio, ping, about)
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

        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_femboy"
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
                summary, _ = await self.gemini.generate(prompt)
            except RuntimeError:
                await ctx.send("❌ Summary service busy, try again later!")
                return
            except Exception as e:
                await ctx.send(f"❌ Error generating summary: {e}")
                return
        
        embed = discord.Embed(
            title=f"📋 TL;DR - Last {len(messages)} messages",
            description=summary,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

        try:
            await increment_stat("messages_processed")
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)
    
    @commands.command(name="portfolio", aliases=["site", "website"])
    async def check_portfolio(self, ctx: commands.Context, url: str = None):
        """Check if a website is up and responding."""
        target_url = url or self.portfolio_url
        
        if not target_url:
            await ctx.send(
                "❌ No URL configured!\n"
                "Use `!portfolio <url>` or set `PORTFOLIO_URL` in `.env`"
            )
            return
        
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url
        
        async with ctx.typing():
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(target_url) as response:
                        status = response.status
                        
                        if 200 <= status < 300:
                            status_emoji, status_text, color = "✅", "Online", discord.Color.green()
                        elif 300 <= status < 400:
                            status_emoji, status_text, color = "↪️", "Redirect", discord.Color.yellow()
                        elif status == 503:
                            status_emoji, status_text, color = "🔧", "Maintenance", discord.Color.orange()
                        else:
                            status_emoji, status_text, color = "❌", "Error", discord.Color.red()
                        
            except aiohttp.ClientConnectorError:
                status_emoji, status_text, status, color = "🔌", "Connection Failed", "N/A", discord.Color.red()
            except asyncio.TimeoutError:
                status_emoji, status_text, status, color = "⏰", "Timeout", "N/A", discord.Color.orange()
            except Exception as e:
                status_emoji, status_text, status, color = "❓", f"Error: {str(e)[:50]}", "N/A", discord.Color.red()
        
        embed = discord.Embed(title=f"{status_emoji} Portfolio Status", color=color)
        embed.add_field(name="URL", value=target_url, inline=False)
        embed.add_field(name="Status", value=f"{status_text} ({status})", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)
        emoji = "🟢" if latency < 100 else "🟡" if latency < 200 else "🔴"
        await ctx.send(f"{emoji} Pong! Latency: **{latency}ms**")
    
    @commands.command(name="about", aliases=["info", "botinfo"])
    async def about(self, ctx: commands.Context):
        """Display information about the bot."""
        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_femboy"
        bot_name = self._get_bot_name(mode)
        embed = discord.Embed(
            title=f"🤖 About {bot_name}",
            description="An advanced AI Discord bot with multiple personalities!",
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
        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_femboy"

        if command_name:
            cmd = self.bot.get_command(command_name)
            if not cmd:
                await interaction.response.send_message(
                    f"âŒ Command `{command_name}` not found!",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title=f"ðŸ“– Help: !{cmd.name}",
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

        intro = HELP_INTROS.get(mode, HELP_INTROS["mode_femboy"])
        bot_name = self._get_bot_name(mode)
        embed = discord.Embed(
            title=f"ðŸ“š {bot_name}'s Commands",
            description=intro,
            color=discord.Color.pink(),
        )

        for category_name, category_data in COMMAND_CATEGORIES.items():
            valid_commands = []
            for cmd_name in category_data["commands"]:
                cmd = self.bot.get_command(cmd_name)
                if cmd and not cmd.hidden:
                    valid_commands.append(f"`!{cmd_name}`")

            if valid_commands:
                embed.add_field(
                    name=f"{category_name}",
                    value=" ".join(valid_commands),
                    inline=False,
                )

        embed.set_footer(text="Use !help <command> for more details on a specific command")
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
            title="ðŸ“Š Bot Statistics",
            color=discord.Color.blue(),
        )

        embed.add_field(name="â±ï¸ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="ðŸ  Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="ðŸ‘¥ Users", value=f"{total_users:,}", inline=True)

        embed.add_field(
            name="ðŸ’¬ Messages Processed",
            value=f"{stats.get('messages_processed', 0):,}",
            inline=True,
        )
        embed.add_field(
            name="ðŸ–¼ï¸ Images Analyzed",
            value=f"{stats.get('images_analyzed', 0):,}",
            inline=True,
        )
        embed.add_field(
            name="ðŸ’¾ Memory",
            value=f"{memory_mb:.1f} MB",
            inline=True,
        )

        if interaction.guild:
            mode = await get_server_mode(interaction.guild.id)
            mode_display = {
                "mode_femboy": "ðŸŽ€ Femboy",
                "mode_tsundere": "ðŸ˜¤ Tsundere",
                "mode_oneesan": "ðŸ’• Onee-san",
            }
            embed.add_field(
                name="ðŸŽ­ Current Mode",
                value=mode_display.get(mode, mode),
                inline=True,
            )

        embed.set_footer(text="Powered by Gemini AI â™¡")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reload", description="Reload a cog or all cogs (owner only).")
    @app_commands.describe(cog_name="Cog name or 'all'")
    @app_commands.checks.is_owner()
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

            result = f"âœ… Reloaded: {', '.join(success)}"
            if failed:
                result += f"\nâŒ Failed: {', '.join(failed)}"
            await interaction.followup.send(result)
            return

        cog_name = cog_name.lower()
        if cog_name not in available_cogs:
            await interaction.followup.send(f"âŒ Cog `{cog_name}` not found!")
            return

        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await interaction.followup.send(f"âœ… Reloaded `{cog_name}`!")
        except Exception as e:
            await interaction.followup.send(f"âŒ Failed to reload `{cog_name}`: {e}")

    @app_commands.command(name="translate", description="Translate text to another language.")
    @app_commands.describe(query="Text and target language, e.g. 'hello to japanese'")
    async def translate_slash(self, interaction: discord.Interaction, query: str):
        if " to " not in query.lower():
            await interaction.response.send_message(
                "**Usage:** `!translate <text> to <language>`\n"
                "**Example:** `!translate hello world to japanese`",
                ephemeral=True,
            )
            return

        parts = query.lower().rsplit(" to ", 1)
        text = query[:query.lower().rfind(" to ")]
        target_lang = parts[1].strip()

        if not text or not target_lang:
            await interaction.response.send_message(
                "âŒ Please provide both text and target language!",
                ephemeral=True,
            )
            return

        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_femboy"
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
            client = self.translate_client or self.gemini
            translation, _ = await client.generate(prompt)
            translation = translation.strip()
        except RuntimeError:
            await interaction.followup.send(
                "âŒ Translation service busy, try again later!",
                ephemeral=True,
            )
            return
        except Exception as e:
            await interaction.followup.send(
                f"âŒ Translation failed: {e}",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="ðŸŒ Translation",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Original", value=text[:1024], inline=False)
        embed.add_field(name=f"â†’ {target_lang.title()}", value=translation[:1024], inline=False)

        await interaction.followup.send(embed=embed)

        try:
            await increment_stat("messages_processed")
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

        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_femboy"
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
            summary, _ = await self.gemini.generate(prompt)
        except RuntimeError:
            await interaction.followup.send("Summary service busy, try again later!")
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
            await increment_stat("messages_processed")
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)

    @app_commands.command(name="portfolio", description="Check if a website is up.")
    @app_commands.describe(url="URL to check (optional)")
    async def check_portfolio_slash(self, interaction: discord.Interaction, url: str = None):
        target_url = url or self.portfolio_url

        if not target_url:
            await interaction.response.send_message(
                "âŒ No URL configured!\n"
                "Use `!portfolio <url>` or set `PORTFOLIO_URL` in `.env`",
                ephemeral=True,
            )
            return

        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        await interaction.response.defer(thinking=True)

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(target_url) as response:
                    status = response.status

                    if 200 <= status < 300:
                        status_emoji, status_text, color = "âœ…", "Online", discord.Color.green()
                    elif 300 <= status < 400:
                        status_emoji, status_text, color = "â†ªï¸", "Redirect", discord.Color.yellow()
                    elif status == 503:
                        status_emoji, status_text, color = "ðŸ”§", "Maintenance", discord.Color.orange()
                    else:
                        status_emoji, status_text, color = "âŒ", "Error", discord.Color.red()

        except aiohttp.ClientConnectorError:
            status_emoji, status_text, status, color = "ðŸ”Œ", "Connection Failed", "N/A", discord.Color.red()
        except asyncio.TimeoutError:
            status_emoji, status_text, status, color = "â°", "Timeout", "N/A", discord.Color.orange()
        except Exception as e:
            status_emoji, status_text, status, color = "â“", f"Error: {str(e)[:50]}", "N/A", discord.Color.red()

        embed = discord.Embed(title=f"{status_emoji} Portfolio Status", color=color)
        embed.add_field(name="URL", value=target_url, inline=False)
        embed.add_field(name="Status", value=f"{status_text} ({status})", inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        emoji = "ðŸŸ¢" if latency < 100 else "ðŸŸ¡" if latency < 200 else "ðŸ”´"
        await interaction.response.send_message(f"{emoji} Pong! Latency: **{latency}ms**")

    @app_commands.command(name="about", description="Display information about the bot.")
    async def about_slash(self, interaction: discord.Interaction):
        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_femboy"
        bot_name = self._get_bot_name(mode)
        embed = discord.Embed(
            title=f"ðŸ¤– About {bot_name}",
            description="An advanced AI Discord bot with multiple personalities!",
            color=discord.Color.pink(),
        )

        embed.add_field(
            name="âœ¨ Features",
            value=(
                "â€¢ Three personality modes\n"
                "â€¢ AI-powered conversations\n"
                "â€¢ Image analysis\n"
                "â€¢ Affection & Mood system\n"
                "â€¢ Reminders & Translation"
            ),
            inline=False,
        )

        embed.add_field(name="ðŸ“Š Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="ðŸ”— Commands", value="Use `!help`", inline=True)
        embed.set_footer(text="Powered by Gemini AI â™¡")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Load the Utilities cog."""
    await bot.add_cog(Utilities(bot))
