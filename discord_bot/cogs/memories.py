"""
Memories Cog for Femmy Discord Bot
===================================
Handles user personalization through facts and timezone storage.

Commands:
    !set_timezone <Region/City>  - Set your timezone (e.g., Asia/Dhaka)
    !remember <fact>             - Store a fact about yourself
    !forget                      - Clear all stored facts
    !myinfo                      - View your stored timezone and facts

Examples:
    !set_timezone America/New_York
    !remember I love spicy food
    !remember My birthday is March 15th
"""

import pytz
from discord.ext import commands
import discord

from utils.db_handler import (
    set_timezone,
    add_fact,
    get_facts,
    delete_facts,
    get_user,
    create_user,
    add_alias,
    get_aliases,
    find_user_by_alias,
)


class Memories(commands.Cog):
    """
    Memories Cog - User personalization and fact storage.
    
    Stores:
        - User timezones for meal check scheduling
        - Personal facts for AI context injection
        
    TODO:
        - [ ] Add fact categories/tags
        - [ ] Implement fact search
        - [ ] Add export/import functionality
        - [ ] Limit maximum facts per user
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(name="set_timezone", aliases=["tz", "timezone"])
    async def set_user_timezone(self, ctx: commands.Context, *, timezone: str):
        """
        Set your timezone for meal check reminders.
        
        Args:
            timezone: IANA timezone string (e.g., "Asia/Dhaka") or abbreviation (e.g., "EST", "PST")
        """
        # Common timezone abbreviation mappings
        TIMEZONE_ALIASES = {
            # North America
            "EST": "America/New_York",
            "EDT": "America/New_York",
            "CST": "America/Chicago",
            "CDT": "America/Chicago",
            "MST": "America/Denver",
            "MDT": "America/Denver",
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles",
            "AKST": "America/Anchorage",
            "AKDT": "America/Anchorage",
            "HST": "Pacific/Honolulu",
            # Europe
            "GMT": "Europe/London",
            "BST": "Europe/London",
            "CET": "Europe/Paris",
            "CEST": "Europe/Paris",
            "EET": "Europe/Helsinki",
            "EEST": "Europe/Helsinki",
            "WET": "Europe/Lisbon",
            # Asia
            "IST": "Asia/Kolkata",
            "BDT": "Asia/Dhaka",
            "JST": "Asia/Tokyo",
            "KST": "Asia/Seoul",
            "CST_CHINA": "Asia/Shanghai",
            "HKT": "Asia/Hong_Kong",
            "SGT": "Asia/Singapore",
            "PHT": "Asia/Manila",
            "ICT": "Asia/Bangkok",
            "WIB": "Asia/Jakarta",
            # Australia
            "AEST": "Australia/Sydney",
            "AEDT": "Australia/Sydney",
            "ACST": "Australia/Adelaide",
            "AWST": "Australia/Perth",
            # Other
            "UTC": "UTC",
            "MTC": "Europe/Moscow",  # Moscow Time
            "MSK": "Europe/Moscow",
            "GST": "Asia/Dubai",  # Gulf Standard Time
            "AST": "Asia/Riyadh",  # Arabia Standard Time
            "NZST": "Pacific/Auckland",
            "NZDT": "Pacific/Auckland",
        }
        
        # Normalize input
        tz_input = timezone.strip().upper()
        
        # Check for abbreviation first
        if tz_input in TIMEZONE_ALIASES:
            timezone = TIMEZONE_ALIASES[tz_input]
        
        # Validate timezone
        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            # Build abbreviation examples
            abbrev_examples = ", ".join(list(TIMEZONE_ALIASES.keys())[:8])
            await ctx.send(
                f"❌ Unknown timezone: `{timezone}`\n"
                f"**Abbreviations:** `{abbrev_examples}`, ...\n"
                f"**Full format:** `Asia/Dhaka`, `America/New_York`, `Europe/London`\n"
                f"Find more: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
            )
            return
        
        # Store timezone
        await set_timezone(ctx.author.id, timezone)
        
        # Get current time in that timezone
        from datetime import datetime
        current_time = datetime.now(tz).strftime("%H:%M")
        
        await ctx.send(
            f"✅ Timezone set to **{timezone}**!\n"
            f"Your current time: `{current_time}`"
        )
    
    @commands.command(name="remember")
    async def remember_fact(self, ctx: commands.Context, *, fact: str):
        """
        Store a fact about yourself for AI context.
        
        Args:
            fact: Any information you want Femmy to remember
            
        TODO:
            - [ ] Check for duplicate facts
            - [ ] Implement fact limit (e.g., max 50)
            - [ ] Add confirmation for sensitive info
        """
        if not ctx.guild:
            await ctx.send("Facts are server-specific. Use this in a server.")
            return

        if len(fact) > 500:
            await ctx.send("❌ Fact too long! Please keep it under 500 characters.")
            return
        
        # Ensure user exists
        await create_user(ctx.author.id)
        
        # Store the fact
        fact_id = await add_fact(ctx.guild.id, ctx.author.id, fact)
        
        await ctx.send(
            f"📝 Got it! I'll remember that~ ♡\n"
            f"Stored: *\"{fact}\"*"
        )
    
    @commands.command(name="forget")
    async def forget_facts(self, ctx: commands.Context):
        """
        Delete all stored facts about yourself.
        
        TODO:
            - [ ] Add confirmation prompt
            - [ ] Allow deleting specific facts by ID
        """
        if not ctx.guild:
            await ctx.send("Facts are server-specific. Use this in a server.")
            return

        count = await delete_facts(ctx.guild.id, ctx.author.id)
        
        if count == 0:
            await ctx.send("🤔 I don't have any facts stored about you!")
        else:
            await ctx.send(f"🗑️ Cleared {count} fact(s) from memory!")
    
    @commands.command(name="myinfo", aliases=["me", "profile"])
    async def show_user_info(self, ctx: commands.Context):
        """
        Display your stored timezone and facts.
        
        TODO:
            - [ ] Add pagination for many facts
            - [ ] Show fact creation dates
        """
        if not ctx.guild:
            await ctx.send("Profiles are server-specific. Use this in a server.")
            return

        user = await get_user(ctx.author.id)
        facts = await get_facts(ctx.guild.id, ctx.author.id)
        
        # Build embed
        embed = discord.Embed(
            title=f"📋 {ctx.author.display_name}'s Profile",
            color=discord.Color.pink()
        )
        
        # Timezone info
        timezone = user.get("timezone", "Not set") if user else "Not set"
        embed.add_field(
            name="🌍 Timezone",
            value=f"`{timezone}`",
            inline=True
        )
        
        # Facts info
        if facts:
            facts_text = "\n".join(f"• {fact}" for fact in facts[:10])
            if len(facts) > 10:
                facts_text += f"\n... and {len(facts) - 10} more"
            embed.add_field(
                name=f"📝 Remembered Facts ({len(facts)})",
                value=facts_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📝 Remembered Facts",
                value="*No facts stored yet. Use `!remember <fact>` to add some!*",
                inline=False
            )
        
        embed.set_footer(text="Use !remember to add facts, !forget to clear them")
        
        await ctx.send(embed=embed)

    # ============================================
    # User Alias Commands
    # ============================================

    @commands.command(name="aka", aliases=["alias", "nickname"])
    async def add_user_alias(self, ctx: commands.Context, member: discord.Member = None, *, alias: str = None):
        """
        Add an alias for a user.

        Usage:
            !aka @user <alias>
        """
        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return
        if not member or not alias:
            await ctx.send("Usage: `!aka @user <alias>`")
            return

        alias = alias.strip()
        if not alias:
            await ctx.send("Please provide a non-empty alias.")
            return
        if len(alias) > 64:
            await ctx.send("Alias too long. Please keep it under 64 characters.")
            return

        added = await add_alias(ctx.guild.id, member.id, alias, ctx.author.id)
        if added:
            await ctx.send(f"Added alias `{alias}` for {member.display_name}.")
        else:
            await ctx.send(f"`{alias}` is already an alias for {member.display_name}.")

    @commands.command(name="aliases", aliases=["aka_list"])
    async def list_user_aliases(self, ctx: commands.Context, member: discord.Member = None):
        """
        List aliases for a user.

        Usage:
            !aliases @user
        """
        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return

        target = member or ctx.author
        aliases = await get_aliases(ctx.guild.id, target.id)
        if not aliases:
            await ctx.send(f"No aliases found for {target.display_name}.")
            return

        alias_text = ", ".join(aliases[:20])
        if len(aliases) > 20:
            alias_text += f", ... (+{len(aliases) - 20} more)"

        embed = discord.Embed(
            title=f"Aliases for {target.display_name}",
            description=alias_text,
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name="whois")
    async def whois_alias(self, ctx: commands.Context, *, alias: str):
        """
        Find a user by alias.

        Usage:
            !whois <alias>
        """
        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return

        alias = alias.strip()
        if not alias:
            await ctx.send("Usage: `!whois <alias>`")
            return

        user_id = await find_user_by_alias(ctx.guild.id, alias)
        if not user_id:
            await ctx.send(f"No user found with alias `{alias}`.")
            return

        member = ctx.guild.get_member(user_id)
        if member:
            await ctx.send(f"`{alias}` belongs to {member.mention}.")
            return

        user = self.bot.get_user(user_id)
        if user:
            await ctx.send(f"`{alias}` belongs to {user.name} (`{user_id}`).")
        else:
            await ctx.send(f"`{alias}` belongs to user ID `{user_id}`.")

    # ============================================
    # Cross-User Facts
    # ============================================

    @commands.command(name="aboutuser", aliases=["about_user", "userfacts", "facts"])
    async def about_user(self, ctx: commands.Context, member: discord.Member = None):
        """
        View facts about another user.

        Usage:
            !aboutuser @user
        """
        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return

        if member is None:
            await ctx.send("Usage: `!aboutuser @user`")
            return

        facts = await get_facts(ctx.guild.id, member.id)
        if not facts:
            await ctx.send(f"I don't have any facts stored about {member.display_name}.")
            return

        facts_text = "\n".join(f"- {fact}" for fact in facts[:10])
        if len(facts) > 10:
            facts_text += f"\n... and {len(facts) - 10} more"

        embed = discord.Embed(
            title=f"Facts about {member.display_name}",
            description=facts_text,
            color=discord.Color.pink()
        )
        await ctx.send(embed=embed)
    
    # ============================================
    # Birthday Commands
    # ============================================
    
    @commands.group(name="birthday", aliases=["bday"], invoke_without_command=True)
    async def birthday(self, ctx: commands.Context, member: discord.Member = None):
        """
        View your or someone's birthday.
        
        Usage:
            !birthday          - View your birthday
            !birthday @user    - View someone's birthday
            !birthday set MM-DD - Set your birthday
            !birthday upcoming  - See upcoming birthdays
        """
        from utils.db_handler import get_birthday
        
        target = member or ctx.author
        bday = await get_birthday(target.id)
        
        if bday:
            month, day = bday.split("-")
            month_name = [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ][int(month)]
            await ctx.send(f"🎂 {target.display_name}'s birthday is **{month_name} {int(day)}**!")
        else:
            if target == ctx.author:
                await ctx.send("📅 You haven't set your birthday yet! Use `!birthday set MM-DD`")
            else:
                await ctx.send(f"📅 {target.display_name} hasn't set their birthday yet!")
    
    @birthday.command(name="set")
    async def birthday_set(self, ctx: commands.Context, date: str):
        """
        Set your birthday (format: MM-DD).
        
        Examples:
            !birthday set 03-15  (March 15th)
            !birthday set 12-25  (December 25th)
        """
        from utils.db_handler import set_birthday
        import re
        
        # Validate format
        if not re.match(r"^\d{2}-\d{2}$", date):
            await ctx.send("❌ Invalid format! Use `MM-DD` (e.g., `03-15` for March 15th)")
            return
        
        month, day = map(int, date.split("-"))
        
        # Validate month and day
        if month < 1 or month > 12:
            await ctx.send("❌ Month must be between 01 and 12!")
            return
        
        days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if day < 1 or day > days_in_month[month]:
            await ctx.send(f"❌ Invalid day for month {month:02d}!")
            return
        
        await set_birthday(ctx.author.id, date)
        
        month_name = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ][month]
        
        await ctx.send(f"🎂 Birthday set to **{month_name} {day}**! I'll remember~ ♡")
    
    @birthday.command(name="upcoming")
    async def birthday_upcoming(self, ctx: commands.Context):
        """See upcoming birthdays in the next 30 days."""
        from utils.db_handler import get_upcoming_birthdays
        
        upcoming = await get_upcoming_birthdays(30)
        
        if not upcoming:
            await ctx.send("📅 No birthdays coming up in the next 30 days!")
            return
        
        embed = discord.Embed(
            title="🎂 Upcoming Birthdays",
            color=discord.Color.pink()
        )
        
        for entry in upcoming[:10]:
            user = self.bot.get_user(entry["user_id"])
            name = user.display_name if user else f"User {entry['user_id']}"
            days = entry["days_until"]
            
            if days == 0:
                when = "**Today!** 🎉"
            elif days == 1:
                when = "Tomorrow"
            else:
                when = f"In {days} days"
            
            month, day = entry["birthday"].split("-")
            embed.add_field(
                name=f"{name}",
                value=f"{month}/{day} - {when}",
                inline=True
            )
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Load the Memories cog."""
    await bot.add_cog(Memories(bot))
