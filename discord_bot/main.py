"""
Femmy Discord Bot - Main Entry Point
=====================================
A highly advanced Discord bot with Gemini AI integration,
featuring three personality modes and modular cog architecture.

Author: Your Name
Version: 1.0.0
"""

import os
import asyncio
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.logger import get_logger, log_startup, log_error, log_command
from utils.db_handler import increment_stat

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load environment variables
load_dotenv(ENV_PATH)

COG_PACKAGE = "cogs"

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(
        f"Missing required environment variable: {name}. "
        f"Set it in your environment or {ENV_PATH}"
    )


# Bot configuration
DISCORD_TOKEN = _require_env("DISCORD_TOKEN")
GEMINI_API_KEY = _require_env("GEMINI_API_KEY")

# Optional: Lock bot to a specific personality mode
# Set BOT_MODE=femboy, tsundere, or oneesan to lock the mode
BOT_MODE = os.getenv("BOT_MODE", "").lower()
VALID_MODES = {"femboy": "mode_femboy", "tsundere": "mode_tsundere", "oneesan": "mode_oneesan"}
LOCKED_MODE = VALID_MODES.get(BOT_MODE)

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True

logger = get_logger(__name__)


def discover_cogs() -> list[str]:
    """Discover all cogs in the cogs directory."""
    cogs_dir = Path(__file__).parent / COG_PACKAGE
    return sorted(
        f"{COG_PACKAGE}.{path.stem}"
        for path in cogs_dir.glob("*.py")
        if path.stem != "__init__" and not path.stem.startswith("_")
    )


class Femmy(commands.Bot):
    """
    Main bot class for Femmy.
    
    TODO:
        - [ ] Initialize database on startup
        - [ ] Load all cogs from cogs/ directory
        - [ ] Set up error handling
        - [ ] Configure logging
    """
    
    def __init__(self):
        super().__init__(
            command_prefix=os.getenv("COMMAND_PREFIX", "!"),
            intents=intents,
            description="Femmy - Your AI companion with personality!",
            help_command=None  # Use custom help in utilities.py
        )
    
    async def setup_hook(self):
        """
        Called when the bot is starting up.
        Load cogs and initialize database here.
        
        TODO:
            - [ ] Call database initialization
            - [ ] Load all cogs dynamically
            - [ ] Set up Gemini client
        """
        # Initialize database
        from utils.db_handler import init_db
        await init_db()
        
        # Load cogs dynamically
        cog_list = discover_cogs()
        
        for cog in cog_list:
            try:
                await self.load_extension(cog)
                logger.info("Loaded cog: %s", cog)
            except Exception as e:
                logger.error("Failed to load cog %s: %s", cog, e, exc_info=True)

        try:
            await self.tree.sync()
            logger.info("Slash commands synced.")
        except Exception as e:
            logger.error("Failed to sync slash commands: %s", e, exc_info=True)
    
    async def on_ready(self):
        """Called when the bot is connected and ready."""
        logger.info("=" * 50)
        logger.info("%s is now online!", self.user.name)
        logger.info("Connected to %s server(s)", len(self.guilds))
        logger.info("Bot ID: %s", self.user.id)
        logger.info("=" * 50)
        
        # Set custom status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="over you~ ♡"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """
        Global error handler for commands.
        
        TODO:
            - [ ] Handle specific error types
            - [ ] Log errors to file
            - [ ] Send user-friendly messages
        """
        if isinstance(error, commands.CommandNotFound):
            return  # Silently ignore unknown commands
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`")
            return
        
        # Log other errors
        log_error(error, context=f"Command error: {ctx.command}")
        await ctx.send("Something went wrong... >.<")

    async def on_command(self, ctx: commands.Context):
        """Track command usage for stats and logging."""
        try:
            await increment_stat("commands_executed")
        except Exception as e:
            logger.warning("Failed to increment commands_executed: %s", e)

        try:
            guild_id = ctx.guild.id if ctx.guild else None
            log_command(ctx.command.name, ctx.author.id, guild_id)
        except Exception as e:
            logger.warning("Failed to log command: %s", e)


# ============================================
# Standalone Sync Command
# ============================================


@commands.command(name='sync')
@commands.has_permissions(manage_guild=True)
async def sync_command(ctx: commands.Context):
    """
    Sync slash commands to this server (instant update).
    Usage: !sync
    """
    ctx.bot.tree.copy_global_to(guild=ctx.guild)
    fmt = await ctx.bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ Synced {len(fmt)} slash commands to **{ctx.guild.name}**! They should appear now.")


async def main():
    """Main entry point for the bot."""
    log_startup()
    bot = Femmy()
    
    # Register the standalone !sync command
    bot.add_command(sync_command)
    
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
