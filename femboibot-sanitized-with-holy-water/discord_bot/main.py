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
from utils.expression_cache import ExpressionService
from modes import validate_mode_registry, resolve_mode_key
from utils.emoji_manager import EmojiManager
from utils.activity_rotator import ActivityRotator, is_activity_rotator_enabled

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_OVERRIDE_PATHS = [
    BASE_DIR / ".env.femmy",
    BASE_DIR.parent / ".env.femmy",
]

# Load environment variables
for env_path in ENV_OVERRIDE_PATHS:
    if env_path.exists():
        load_dotenv(env_path, override=True)
load_dotenv(ENV_PATH, override=False)

COG_PACKAGE = "cogs"

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(
        f"Missing required environment variable: {name}. "
        f"Set it in your environment, {ENV_PATH}, or one of: {', '.join(str(p) for p in ENV_OVERRIDE_PATHS)}"
    )


# Bot configuration
DISCORD_TOKEN = _require_env("DISCORD_TOKEN")
_require_env("ENCRYPTION_KEY")

# Optional: Lock bot to a specific personality mode
# Set BOT_MODE=femboy, tsundere, or oneesan to lock the mode
BOT_MODE = os.getenv("BOT_MODE", "").lower()
LOCKED_MODE = resolve_mode_key(BOT_MODE) if BOT_MODE else None

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = False

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
        self.add_check(self._guild_only_check)
        self.expression_service = ExpressionService(self)
        self.emoji_manager = EmojiManager(self)
        self._activity_task: asyncio.Task | None = None
        self._activity_rotator: ActivityRotator | None = None
        self._app_expression_refresh_task: asyncio.Task | None = None

    async def _guild_only_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            await ctx.send("Commands can only be used inside servers.")
            return False
        return True
    
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
        if str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() in {"1", "true", "yes", "on"}:
            try:
                from utils.pg_client import ensure_pg_schema
                await ensure_pg_schema()
            except Exception as exc:
                logger.warning("Failed to initialize RAG Postgres schema: %s", exc)

        # Validate mode registry once on startup
        issues = validate_mode_registry()
        if issues:
            logger.warning("Mode registry issues detected: %s", "; ".join(issues))
        
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

        # Ensure per-guild databases are created/registered
        from utils.db_handler import init_guild_db
        for guild in self.guilds:
            try:
                await init_guild_db(guild.id)
            except Exception as e:
                logger.warning("Failed to init DB for guild %s: %s", guild.id, e)

        try:
            await self.expression_service.get_application_snapshot(force_refresh=True)
            await self.emoji_manager.validate_emojis()
            logger.info(
                "Validated %s emoji rules and %s general emojis",
                len(self.emoji_manager._validated_emojis),
                len(self.emoji_manager._validated_general),
            )
        except Exception as exc:
            logger.warning("Failed to validate emojis: %s", exc)
        
        if is_activity_rotator_enabled():
            if not self._activity_task or self._activity_task.done():
                self._activity_task = asyncio.create_task(self._run_activity_rotator())
        else:
            activity = discord.Game(name="Clanking with humans")
            await self.change_presence(activity=activity)
        if not self._app_expression_refresh_task or self._app_expression_refresh_task.done():
            self._app_expression_refresh_task = asyncio.create_task(self._run_app_expression_refresh())

    async def _run_activity_rotator(self) -> None:
        if not self._activity_rotator:
            self._activity_rotator = ActivityRotator(self)
        await self._activity_rotator.refresh_pool(force=True)
        while not self.is_closed():
            try:
                activity = await self._activity_rotator.next_activity()
                if activity:
                    await self.change_presence(activity=activity)
            except Exception as exc:
                logger.warning("Activity rotator failed to update presence: %s", exc)
            await asyncio.sleep(self._activity_rotator.interval_seconds)

    async def _run_app_expression_refresh(self) -> None:
        while not self.is_closed():
            try:
                await self.expression_service.refresh_application_emojis(background_refresh=True)
                await self.emoji_manager.validate_emojis()
            except Exception as exc:
                logger.warning("Application emoji background refresh failed: %s", exc)
            await asyncio.sleep(self.expression_service.app_ttl_seconds)

    async def on_guild_join(self, guild: discord.Guild):
        """Initialize new guild data and set the server avatar to the guild icon."""
        from utils.db_handler import init_guild_db, get_guild_avatar_path
        from utils.server_avatar import set_custom_avatar

        try:
            await init_guild_db(guild.id)
        except Exception as exc:
            logger.warning("Failed to init DB for guild %s on join: %s", guild.id, exc)

        if not guild.icon:
            return

        try:
            existing_path = await get_guild_avatar_path(guild.id)
        except Exception as exc:
            logger.warning("Failed to fetch avatar path for guild %s: %s", guild.id, exc)
            existing_path = None

        if existing_path:
            logger.info("Skipping guild avatar update for %s: custom avatar already set.", guild.id)
            return

        try:
            icon_asset = guild.icon.replace(size=128)
            icon_bytes = await icon_asset.read()
        except Exception as exc:
            logger.warning("Failed to read guild icon for %s: %s", guild.id, exc)
            return

        try:
            success, reason = await set_custom_avatar(self, guild.id, icon_bytes)
        except Exception as exc:
            logger.warning("Failed to set guild avatar for %s: %s", guild.id, exc)
            return

        if not success:
            logger.warning("Guild avatar update failed for %s: %s", guild.id, reason)

    async def on_guild_emojis_update(self, guild: discord.Guild, _before, _after):
        try:
            await self.expression_service.refresh_guild_snapshot(guild)
        except Exception as exc:
            logger.warning("Guild emoji sync failed for %s: %s", guild.id, exc)

    async def on_guild_stickers_update(self, guild: discord.Guild, _before, _after):
        try:
            await self.expression_service.refresh_guild_snapshot(guild)
        except Exception as exc:
            logger.warning("Guild sticker sync failed for %s: %s", guild.id, exc)

    async def on_resumed(self):
        self.expression_service.mark_all_guilds_suspect()
        self.expression_service.mark_application_stale()
        return await super().on_resumed()

    async def on_interaction(self, interaction: discord.Interaction):
        """Block application commands in DMs (works even without tree.check support)."""
        if interaction.type == discord.InteractionType.application_command and interaction.guild is None:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        "Commands can only be used inside servers.",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "Commands can only be used inside servers.",
                        ephemeral=True,
                    )
            except Exception:
                pass
            return
        await super().on_interaction(interaction)
    
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
    try:
        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(
            f"Synced {len(fmt)} slash commands to **{ctx.guild.name}**! They should appear now."
        )
    except Exception as e:
        logger.error("Sync failed: %s", e, exc_info=True)
        await ctx.send("Sync failed. Check logs for details.")


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
