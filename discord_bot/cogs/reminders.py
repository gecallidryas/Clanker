"""
Reminders Cog for Femmy Discord Bot
=====================================
User reminders with natural time parsing.

Commands:
    !remind <time> <message>  - Set a reminder
    !reminders                - List your reminders
    !remind cancel <id>       - Cancel a reminder

Time Formats:
    - Xm: X minutes (e.g., 30m)
    - Xh: X hours (e.g., 2h)
    - Xd: X days (e.g., 1d)
    - Xw: X weeks (e.g., 1w)
    - tomorrow
    - next week
"""

import re
import random
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.db_handler import (
    add_reminder,
    get_user_reminders,
    get_due_reminders,
    complete_reminder,
    delete_reminder,
    get_server_mode,
)
from utils.logger import get_logger


# Maximum reminders per user
MAX_REMINDERS = 25

logger = get_logger(__name__)

# Time parsing patterns
TIME_PATTERN = re.compile(
    r"^(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|wk|week|weeks)$",
    re.IGNORECASE
)

TIME_MULTIPLIERS = {
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "wk": 604800, "week": 604800, "weeks": 604800,
}


# ============================================
# Reminder Messages
# ============================================

REMINDER_MESSAGES = {
    "mode_femboy": [
        "⏰ Nii-chan! You asked me to remind you: **{message}**",
        "⏰ *tugs sleeve* Don't forget! **{message}** ♡",
        "⏰ Reminder time~! **{message}** ✨"
    ],
    "mode_tsundere": [
        "⏰ Hmph! You told ME to remind YOU: **{message}**",
        "⏰ It's not like I remembered for you or anything! **{message}**",
        "⏰ Here's your reminder, baka: **{message}**"
    ],
    "mode_oneesan": [
        "⏰ Ara ara~ Time for your reminder, dear: **{message}**",
        "⏰ My dear, don't forget: **{message}** ♡",
        "⏰ Here's what you wanted to remember: **{message}**"
    ]
}


def parse_time(time_str: str) -> Optional[int]:
    """
    Parse a time string into seconds.
    
    Returns:
        Seconds or None if invalid
    """
    normalized = time_str.strip().lower()
    if normalized in ("tomorrow", "next day", "nextday"):
        return 24 * 60 * 60
    if normalized in ("next week", "nextweek"):
        return 7 * 24 * 60 * 60

    match = TIME_PATTERN.match(normalized)
    if not match:
        return None
    
    amount = int(match.group(1))
    unit = match.group(2).lower()
    
    multiplier = TIME_MULTIPLIERS.get(unit)
    if not multiplier:
        return None
    
    return amount * multiplier


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h" if hours else f"{days}d"


class Reminders(commands.Cog):
    """
    Reminders Cog - Personal reminder management.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_check_loop.start()
    
    def cog_unload(self):
        self.reminder_check_loop.cancel()
    
    @commands.group(name="remind", aliases=["reminder"], invoke_without_command=True)
    async def remind(self, ctx: commands.Context, time: str = None, *, message: str = None):
        """
        Set a reminder.
        
        Usage:
            !remind 30m drink water
            !remind 2h check oven
            !remind 1d submit assignment
        """
        if time is None:
            await ctx.send(
                "**Usage:** `!remind <time> <message>`\n"
                "**Examples:**\n"
                "• `!remind 30m drink water`\n"
                "• `!remind 2h check the oven`\n"
                "• `!remind 1d submit assignment`\n\n"
                "**Time formats:** `Xm` (minutes), `Xh` (hours), `Xd` (days), `Xw` (weeks), `tomorrow`, `next week`"
            )
            return
        
        if message is None:
            await ctx.send("❌ Please provide a message for your reminder!")
            return
        
        # Check reminder limit
        if not ctx.guild:
            await ctx.send("Please use reminders inside a server.")
            return
        existing = await get_user_reminders(ctx.author.id, ctx.guild.id)
        if len(existing) >= MAX_REMINDERS:
            await ctx.send(f"❌ You have too many reminders! Maximum is {MAX_REMINDERS}.")
            return
        
        # Parse time
        seconds = parse_time(time)
        if seconds is None:
            await ctx.send(
                f"❌ Couldn't parse time: `{time}`\n"
                "Use formats like: `30m`, `2h`, `1d`, `1w`, `tomorrow`, `next week`"
            )
            return
        
        # Minimum 1 minute, maximum 30 days
        if seconds < 60:
            await ctx.send("❌ Minimum reminder time is 1 minute!")
            return
        if seconds > 30 * 86400:
            await ctx.send("❌ Maximum reminder time is 30 days!")
            return
        
        # Calculate remind time
        remind_at = datetime.now() + timedelta(seconds=seconds)
        
        # Store reminder
        reminder_id = await add_reminder(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message=message,
            remind_at=remind_at
        )
        
        # Confirm
        duration = format_duration(seconds)
        embed = discord.Embed(
            title="⏰ Reminder Set!",
            description=f"I'll remind you in **{duration}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Message", value=message, inline=False)
        embed.add_field(name="ID", value=f"`{reminder_id}`", inline=True)
        embed.set_footer(text=f"Reminds at {remind_at.strftime('%Y-%m-%d %H:%M')}")
        
        await ctx.send(embed=embed)
    
    @remind.command(name="list")
    async def remind_list(self, ctx: commands.Context):
        """List all your active reminders."""
        if not ctx.guild:
            await ctx.send("Please use reminders inside a server.")
            return
        reminders = await get_user_reminders(ctx.author.id, ctx.guild.id)
        
        if not reminders:
            await ctx.send("📭 You don't have any active reminders!")
            return
        
        embed = discord.Embed(
            title="📋 Your Reminders",
            color=discord.Color.blue()
        )
        
        for rem in reminders[:10]:  # Show max 10
            remind_at = rem["remind_at"]
            if isinstance(remind_at, str):
                remind_at = datetime.fromisoformat(remind_at)
            
            time_left = remind_at - datetime.now()
            duration = format_duration(int(time_left.total_seconds())) if time_left.total_seconds() > 0 else "Soon!"
            
            embed.add_field(
                name=f"#{rem['id']} - in {duration}",
                value=rem["message"][:100],
                inline=False
            )
        
        if len(reminders) > 10:
            embed.set_footer(text=f"And {len(reminders) - 10} more...")
        
        await ctx.send(embed=embed)
    
    @remind.command(name="cancel", aliases=["delete", "remove"])
    async def remind_cancel(self, ctx: commands.Context, reminder_id: int):
        """Cancel a reminder by ID."""
        if not ctx.guild:
            await ctx.send("Please use reminders inside a server.")
            return
        success = await delete_reminder(reminder_id, ctx.author.id, ctx.guild.id)
        
        if success:
            await ctx.send(f"✅ Reminder #{reminder_id} cancelled!")
        else:
            await ctx.send(f"❌ Couldn't find reminder #{reminder_id} (or it's not yours)")
    
    @commands.command(name="reminders")
    async def reminders_alias(self, ctx: commands.Context):
        """Alias for !remind list."""
        await self.remind_list(ctx)
    
    # ============================================
    # Background Task
    # ============================================
    
    @tasks.loop(seconds=30)
    async def reminder_check_loop(self):
        """Check for due reminders and send them."""
        due = await get_due_reminders()
        
        for reminder in due:
            try:
                # Get channel
                channel = self.bot.get_channel(reminder["channel_id"])
                if not channel:
                    await complete_reminder(reminder["id"], reminder["guild_id"])
                    continue
                
                # Get mode for personality
                mode = "mode_femboy"
                if reminder["guild_id"]:
                    mode = await get_server_mode(reminder["guild_id"])
                
                # Format message
                messages = REMINDER_MESSAGES.get(mode, REMINDER_MESSAGES["mode_femboy"])
                msg = random.choice(messages).format(message=reminder["message"])
                
                # Send reminder
                user_mention = f"<@{reminder['user_id']}>"
                await channel.send(f"{user_mention}\n{msg}")
                
            except Exception as e:
                logger.error("Error sending reminder %s: %s", reminder["id"], e, exc_info=True)
            
            # Mark as complete
            await complete_reminder(reminder["id"], reminder["guild_id"])
    
    @reminder_check_loop.before_loop
    async def before_reminder_check(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="remind", description="Set a reminder.")
    @app_commands.describe(time="When to remind you (e.g., 30m, 2h, tomorrow)", message="Reminder message")
    async def remind_slash(self, interaction: discord.Interaction, time: str, message: str):
        if not time:
            await interaction.response.send_message(
                "**Usage:** `!remind <time> <message>`\n"
                "**Examples:**\n"
                "â€¢ `!remind 30m drink water`\n"
                "â€¢ `!remind 2h check the oven`\n"
                "â€¢ `!remind 1d submit assignment`\n\n"
                "**Time formats:** `Xm` (minutes), `Xh` (hours), `Xd` (days), `Xw` (weeks), `tomorrow`, `next week`",
                ephemeral=True,
            )
            return

        if not message:
            await interaction.response.send_message(
                "âŒ Please provide a message for your reminder!",
                ephemeral=True,
            )
            return

        if not interaction.guild:
            await interaction.response.send_message(
                "Please use reminders inside a server.",
                ephemeral=True,
            )
            return

        existing = await get_user_reminders(interaction.user.id, interaction.guild.id)
        if len(existing) >= MAX_REMINDERS:
            await interaction.response.send_message(
                f"âŒ You have too many reminders! Maximum is {MAX_REMINDERS}.",
                ephemeral=True,
            )
            return

        seconds = parse_time(time)
        if seconds is None:
            await interaction.response.send_message(
                f"âŒ Couldn't parse time: `{time}`\n"
                "Use formats like: `30m`, `2h`, `1d`, `1w`, `tomorrow`, `next week`",
                ephemeral=True,
            )
            return

        if seconds < 60:
            await interaction.response.send_message(
                "âŒ Minimum reminder time is 1 minute!",
                ephemeral=True,
            )
            return
        if seconds > 30 * 86400:
            await interaction.response.send_message(
                "âŒ Maximum reminder time is 30 days!",
                ephemeral=True,
            )
            return

        remind_at = datetime.now() + timedelta(seconds=seconds)

        channel_id = interaction.channel.id if interaction.channel else None
        reminder_id = await add_reminder(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            channel_id=channel_id,
            message=message,
            remind_at=remind_at,
        )

        duration = format_duration(seconds)
        embed = discord.Embed(
            title="â° Reminder Set!",
            description=f"I'll remind you in **{duration}**",
            color=discord.Color.green(),
        )
        embed.add_field(name="Message", value=message, inline=False)
        embed.add_field(name="ID", value=f"`{reminder_id}`", inline=True)
        embed.set_footer(text=f"Reminds at {remind_at.strftime('%Y-%m-%d %H:%M')}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reminders", description="List your active reminders.")
    async def reminders_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "Please use reminders inside a server.",
                ephemeral=True,
            )
            return

        reminders = await get_user_reminders(interaction.user.id, interaction.guild.id)

        if not reminders:
            await interaction.response.send_message(
                "ðŸ“­ You don't have any active reminders!",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="ðŸ“‹ Your Reminders",
            color=discord.Color.blue(),
        )

        for rem in reminders[:10]:
            remind_at = rem["remind_at"]
            if isinstance(remind_at, str):
                remind_at = datetime.fromisoformat(remind_at)

            time_left = remind_at - datetime.now()
            duration = (
                format_duration(int(time_left.total_seconds()))
                if time_left.total_seconds() > 0
                else "Soon!"
            )

            embed.add_field(
                name=f"#{rem['id']} - in {duration}",
                value=rem["message"][:100],
                inline=False,
            )

        if len(reminders) > 10:
            embed.set_footer(text=f"And {len(reminders) - 10} more...")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remindcancel", description="Cancel a reminder by ID.")
    @app_commands.describe(reminder_id="Reminder ID to cancel")
    async def remind_cancel_slash(self, interaction: discord.Interaction, reminder_id: int):
        if not interaction.guild:
            await interaction.response.send_message(
                "Please use reminders inside a server.",
                ephemeral=True,
            )
            return

        success = await delete_reminder(reminder_id, interaction.user.id, interaction.guild.id)

        if success:
            await interaction.response.send_message(
                f"âœ… Reminder #{reminder_id} cancelled!"
            )
        else:
            await interaction.response.send_message(
                f"âŒ Couldn't find reminder #{reminder_id} (or it's not yours)",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))
