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
from discord.ext import commands

from utils.db_handler import get_server_mode, get_stats, increment_stat
from utils.api_manager import get_gemini_manager
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
        "commands": ["remember", "forget", "myinfo", "set_timezone", "birthday"]
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
        self.portfolio_url = os.getenv("PORTFOLIO_URL", "")
        self.start_time = datetime.now()
    
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
        
        embed = discord.Embed(
            title="📚 Femmy's Commands",
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
                translation, _ = await self.gemini.generate(prompt)
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
        embed = discord.Embed(
            title="🤖 About Femmy",
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


async def setup(bot: commands.Bot):
    """Load the Utilities cog."""
    await bot.add_cog(Utilities(bot))
