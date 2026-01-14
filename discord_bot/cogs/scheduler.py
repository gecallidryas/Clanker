"""
Scheduler Cog for Femmy Discord Bot
====================================
Automated tasks including bump reminders and meal checks.

Features:
    - Auto-bump: Pings configured channel every 2 hours
    - Meal check: DMs users at 10 PM in their timezone (Onee-san mode only)

Configuration:
    !setbump #channel  - Set the bump reminder channel
    !clearbump         - Disable bump reminders
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict

import pytz
import discord
from discord.ext import commands, tasks

from utils.db_handler import (
    get_server_mode,
    get_bump_channel,
    set_bump_channel,
    get_users_with_timezone,
)
from utils.logger import get_logger


# Meal check settings
MEAL_CHECK_HOUR = 22  # 10 PM

logger = get_logger(__name__)


class Scheduler(commands.Cog):
    """
    Scheduler Cog - Automated background tasks.
    
    Tasks:
        - auto_bump_loop: Runs every 2 hours
        - meal_check_loop: Runs every hour
        
    TODO:
        - [ ] Add task status command
        - [ ] Implement task enable/disable
        - [ ] Add logging for task execution
        - [ ] Handle rate limits gracefully
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_meal_check: Dict[int, datetime] = {}  # user_id -> last_check_time

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
        self.auto_bump_loop.start()
        self.meal_check_loop.start()
        logger.info("Scheduler tasks started")
    
    async def cog_unload(self):
        """Stop background tasks when cog unloads."""
        self.auto_bump_loop.cancel()
        self.meal_check_loop.cancel()
    
    # ============================================
    # Auto-Bump Task
    # ============================================
    
    @tasks.loop(hours=2)
    async def auto_bump_loop(self):
        """
        Send bump reminders to configured channels.
        
        TODO:
            - [ ] Add bump command detection
            - [ ] Track last bump time per server
            - [ ] Customize bump message
        """
        for guild in self.bot.guilds:
            channel_id = await get_bump_channel(guild.id)
            
            if not channel_id:
                continue
            
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            
            try:
                # TODO: Customize this message per server
                await channel.send(
                    "⏰ **Bump Reminder!**\n"
                    "It's time to bump the server! Use `/bump` ♡"
                )
            except discord.Forbidden:
                logger.warning("Missing permissions to send bump in %s", guild.name)
            except Exception as e:
                logger.error("Error sending bump in %s: %s", guild.name, e, exc_info=True)
    
    @auto_bump_loop.before_loop
    async def before_auto_bump(self):
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
        
        TODO:
            - [ ] Add opt-out option
            - [ ] Customize meal check message
            - [ ] Track if user already responded today
        """
        users = await get_users_with_timezone()
        
        for user_data in users:
            user_id = user_data["user_id"]
            timezone_str = user_data["timezone"]
            
            try:
                # Get user's local time
                tz = pytz.timezone(timezone_str)
                local_time = datetime.now(tz)
                
                # Check if it's 10 PM (22:00)
                if local_time.hour != MEAL_CHECK_HOUR:
                    continue
                
                # Prevent duplicate checks within the same hour
                last_check = self.last_meal_check.get(user_id)
                if last_check and (datetime.now() - last_check) < timedelta(hours=1):
                    continue
                
                # Mark as checked
                self.last_meal_check[user_id] = datetime.now()
                
                # Get discorduser
                user = self.bot.get_user(user_id)
                if not user:
                    continue
                
                # Check if any of user's mutual servers are in onee-san mode
                target_guild = None
                for guild in user.mutual_guilds:
                    mode = await get_server_mode(guild.id)
                    if mode == "mode_oneesan":
                        target_guild = guild
                        break

                if not target_guild:
                    continue

                # Send meal check DM
                try:
                    await user.send(
                        f"Ara ara~ Good evening, {user.display_name}!\n\n"
                        f"It's getting late, my dear. Have you eaten dinner yet? "
                        f"You need your strength to grow properly~\n\n"
                        f"Make sure to have something nutritious, okay? I worry about you!"
                    )
                except discord.Forbidden:
                    ping_channel = self._select_ping_channel(target_guild)
                    if not ping_channel:
                        logger.warning("Cannot DM user %s - DMs disabled", user_id)
                        continue

                    try:
                        await ping_channel.send(
                            f"Ara ara~ {user.mention}, have you eaten dinner yet? "
                            f"It's getting late, my dear. Please take care of yourself~"
                        )
                    except discord.Forbidden:
                        logger.warning("Cannot ping user %s in %s", user_id, target_guild.name)
            except Exception as e:
                logger.error("Error in meal check for user %s: %s", user_id, e, exc_info=True)
    
    @meal_check_loop.before_loop
    async def before_meal_check(self):
        """Wait for bot to be ready before starting meal check loop."""
        await self.bot.wait_until_ready()
    
    # ============================================
    # Configuration Commands
    # ============================================
    
    @commands.command(name="setbump")
    @commands.has_permissions(manage_guild=True)
    async def set_bump_channel_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Set the channel for bump reminders.
        
        Args:
            channel: The channel for bump reminders (default: current channel)
            
        TODO:
            - [ ] Add custom interval option
        """
        channel = channel or ctx.channel
        await set_bump_channel(ctx.guild.id, channel.id)
        
        await ctx.send(
            f"✅ Bump reminders set to {channel.mention}!\n"
            f"I'll send reminders every 2 hours~ ♡"
        )
    
    @commands.command(name="clearbump")
    @commands.has_permissions(manage_guild=True)
    async def clear_bump_channel_cmd(self, ctx: commands.Context):
        """
        Disable bump reminders for this server.
        
        TODO:
            - [ ] Add confirmation prompt
        """
        await set_bump_channel(ctx.guild.id, None)
        
        await ctx.send("✅ Bump reminders disabled!")


async def setup(bot: commands.Bot):
    """Load the Scheduler cog."""
    await bot.add_cog(Scheduler(bot))
