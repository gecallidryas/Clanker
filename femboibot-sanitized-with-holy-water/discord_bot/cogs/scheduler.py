"""
Scheduler Cog for Femmy Discord Bot
====================================
Automated tasks including bump reminders and meal checks.

Features:
    - Auto-bump: Smart reminders 2 hours after last /bump (Disboard)
    - Meal check: DMs users at 10 PM in their timezone (Onee-san mode only)

Configuration:
    /bumpchannel #channel  - Set the bump reminder channel
    /bumpstart  - Enable bump reminders
    /bumpstop   - Disable bump reminders
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pytz
import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.db_handler import (
    get_server_mode,
    get_bump_channel,
    set_bump_channel,
    get_bump_config,
    set_bump_enabled,
    set_last_bump_time,
    get_users_with_timezone,
)
from utils.logger import get_logger


# Meal check settings
MEAL_CHECK_HOUR = 22  # 10 PM
# Disboard bot ID
DISBOARD_BOT_ID = 302050872383242240
# Bump reminder interval
BUMP_INTERVAL_HOURS = 2

logger = get_logger(__name__)


class Scheduler(commands.Cog):
    """
    Scheduler Cog - Automated background tasks.
    
    Tasks:
        - bump_check_loop: Checks every 5 minutes for bump reminders
        - meal_check_loop: Runs every hour
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_meal_check: Dict[tuple[int, int], datetime] = {}
        # Track pending bump reminders per guild
        self.pending_bump_reminders: Dict[int, bool] = {}

    @staticmethod
    def _parse_user_timezone_row(row: Any) -> Optional[Tuple[int, str]]:
        """Parse a timezone row from db_handler safely."""
        user_id: Optional[int] = None
        timezone: Optional[str] = None

        if isinstance(row, dict):
            try:
                user_id = int(row.get("user_id")) if row.get("user_id") is not None else None
            except (TypeError, ValueError):
                user_id = None
            timezone_value = row.get("timezone")
            timezone = str(timezone_value).strip() if timezone_value is not None else None
        elif isinstance(row, (list, tuple)):
            if len(row) >= 2:
                try:
                    user_id = int(row[0]) if row[0] is not None else None
                except (TypeError, ValueError):
                    user_id = None
                timezone = str(row[1]).strip() if row[1] is not None else None

        if user_id is None or not timezone:
            return None
        return user_id, timezone

    def _select_ping_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Pick a channel where the bot can ping users."""
        me = guild.me or guild.get_member(self.bot.user.id)
        if not me:
            return None

        if guild.system_channel:
            perms = guild.system_channel.permissions_for(me)
            if perms.send_messages:
                return guild.system_channel

        for channel in guild.text_channels:
            perms = channel.permissions_for(me)
            if perms.send_messages:
                return channel

        return None
    
    async def cog_load(self):
        """Start background tasks when cog loads."""
        self.bump_check_loop.start()
        self.meal_check_loop.start()
        logger.info("Scheduler tasks started")
    
    async def cog_unload(self):
        """Stop background tasks when cog unloads."""
        self.bump_check_loop.cancel()
        self.meal_check_loop.cancel()
    
    # ============================================
    # Disboard /bump Detection
    # ============================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect Disboard's bump success message."""
        if not message.guild:
            return
        
        # Check if it's from Disboard
        if message.author.id != DISBOARD_BOT_ID:
            return
        
        # Check for bump success indicators in embeds
        if message.embeds:
            for embed in message.embeds:
                # Disboard success embed typically contains "Bump done!"
                embed_text = f"{embed.title or ''} {embed.description or ''}"
                if "bump done" in embed_text.lower() or "bumped" in embed_text.lower():
                    # Record the bump time
                    await set_last_bump_time(message.guild.id, datetime.now())
                    logger.info("Bump detected for guild %s", message.guild.name)
                    # Clear pending reminder flag
                    self.pending_bump_reminders[message.guild.id] = False
                    return
    
    # ============================================
    # Auto-Bump Check Task
    # ============================================
    
    @tasks.loop(minutes=5)
    async def bump_check_loop(self):
        """
        Check if it's time to send bump reminders.
        Sends reminder 2 hours after last bump.
        """
        now = datetime.now()
        
        for guild in self.bot.guilds:
            try:
                config = await get_bump_config(guild.id)
                
                # Skip if not enabled or no channel set
                if not config["enabled"] or not config["channel_id"]:
                    continue
                
                # Skip if already sent reminder and waiting for bump
                if self.pending_bump_reminders.get(guild.id, False):
                    continue
                
                channel = guild.get_channel(config["channel_id"])
                if not channel:
                    continue
                
                # Check if 2 hours have passed since last bump
                last_bump = config["last_bump_time"]
                if last_bump:
                    time_since_bump = (now - last_bump).total_seconds()
                    if time_since_bump < BUMP_INTERVAL_HOURS * 3600:
                        continue  # Not time yet
                
                # Send reminder
                try:
                    await channel.send(
                        "⏰ **Bump Reminder!**\n"
                        "It's time to bump the server! Use `/bump` ♡"
                    )
                    # Mark as pending
                    self.pending_bump_reminders[guild.id] = True
                    logger.info("Sent bump reminder to %s", guild.name)
                except discord.Forbidden:
                    logger.warning("Missing permissions to send bump in %s", guild.name)
                except Exception as e:
                    logger.error("Error sending bump in %s: %s", guild.name, e, exc_info=True)
                    
            except Exception as e:
                logger.error("Error checking bump for %s: %s", guild.name, e, exc_info=True)
    
    @bump_check_loop.before_loop
    async def before_bump_check(self):
        """Wait for bot to be ready before starting bump loop."""
        await self.bot.wait_until_ready()
    
    # ============================================
    # Meal Check Task (Onee-san Mode)
    # ============================================
    
    @tasks.loop(hours=1)
    async def meal_check_loop(self):
        """
        Check if it's 10 PM for any user and send meal reminder.
        Only active when server is in Onee-san mode.
        """
        for guild in self.bot.guilds:
            try:
                mode = await get_server_mode(guild.id)
                if mode != "mode_oneesan":
                    continue
                    
                users = await get_users_with_timezone(guild.id)
                ping_channel = self._select_ping_channel(guild)
                if not ping_channel:
                    continue
                    
                for row in users:
                    parsed = self._parse_user_timezone_row(row)
                    if not parsed:
                        logger.warning("Skipping malformed timezone row in guild %s: %r", guild.id, row)
                        continue
                    user_id, timezone = parsed
                    try:
                        tz = pytz.timezone(timezone)
                        local_now = datetime.now(tz)
                        
                        if local_now.hour != MEAL_CHECK_HOUR:
                            continue
                            
                        cache_key = (guild.id, user_id)
                        last_check = self.last_meal_check.get(cache_key)
                        if last_check and (datetime.now() - last_check).total_seconds() < 3600:
                            continue
                            
                        self.last_meal_check[cache_key] = datetime.now()
                        
                        member = guild.get_member(user_id)
                        if not member:
                            continue
                            
                        await ping_channel.send(
                            f"{member.mention} It's getting late~ Have you eaten yet? "
                            f"Make sure to take care of yourself! 💕"
                        )
                        
                    except pytz.UnknownTimeZoneError:
                        continue
                    except discord.Forbidden:
                        continue
                    except Exception as e:
                        logger.error("Error in meal check for user %s: %s", user_id, e, exc_info=True)
                        
            except Exception as e:
                logger.error("Error in meal check for guild %s: %s", guild.name, e, exc_info=True)
    
    @meal_check_loop.before_loop
    async def before_meal_check(self):
        """Wait for bot to be ready before starting meal loop."""
        await self.bot.wait_until_ready()
    
    # ============================================
    # Configuration Commands (Prefix)
    # ============================================
    
    @commands.command(name="setbump", aliases=["bumpstart", "bumpreminderstart"])
    @commands.has_permissions(manage_guild=True)
    async def set_bump_channel_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set and enable bump reminders for a channel."""
        channel = channel or ctx.channel
        await set_bump_channel(ctx.guild.id, channel.id)
        await set_bump_enabled(ctx.guild.id, True)
        
        await ctx.send(
            f"✅ Bump reminders enabled for {channel.mention}!\n"
            f"I'll remind you 2 hours after each `/bump` ♡"
        )
    
    @commands.command(name="clearbump", aliases=["bumpstop", "bumpreminderstop"])
    @commands.has_permissions(manage_guild=True)
    async def clear_bump_channel_cmd(self, ctx: commands.Context):
        """Disable bump reminders for this server."""
        await set_bump_enabled(ctx.guild.id, False)
        await ctx.send("✅ Bump reminders disabled!")

    # ============================================
    # Slash Commands
    # ============================================

    @app_commands.command(name="bumpchannel", description="Set the channel for bump reminders.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Channel for bump reminders")
    async def set_bump_channel_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        channel = channel or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Please select a text channel.", ephemeral=True)
            return
        await set_bump_channel(interaction.guild.id, channel.id)
        await set_bump_enabled(interaction.guild.id, True)
        await interaction.response.send_message(
            f"✅ Bump reminders set to {channel.mention}!\n"
            "I'll remind you 2 hours after each `/bump` ♡"
        )

    @app_commands.command(name="bumpstart", description="Enable bump reminders.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def start_bump_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        
        config = await get_bump_config(interaction.guild.id)
        if not config["channel_id"]:
            await interaction.response.send_message(
                "❌ No bump channel set! Use `/bumpchannel` first.",
                ephemeral=True
            )
            return
        
        await set_bump_enabled(interaction.guild.id, True)
        channel = interaction.guild.get_channel(config["channel_id"])
        channel_mention = channel.mention if channel else "the configured channel"
        await interaction.response.send_message(
            f"✅ Bump reminders enabled for {channel_mention}!\n"
            "I'll remind you 2 hours after each `/bump` ♡"
        )

    @app_commands.command(name="bumpstop", description="Disable bump reminders.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stop_bump_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        await set_bump_enabled(interaction.guild.id, False)
        # Clear pending reminder
        self.pending_bump_reminders[interaction.guild.id] = False
        await interaction.response.send_message("✅ Bump reminders disabled!")


async def setup(bot: commands.Bot):
    """Load the Scheduler cog."""
    await bot.add_cog(Scheduler(bot))
