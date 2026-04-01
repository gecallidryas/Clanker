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
from discord import app_commands

from utils.db_handler import (
    set_timezone,
    add_fact,
    add_server_memory,
    get_facts,
    get_personal_memories,
    get_mention_lookup_personal_memories,
    get_personal_memory_opt_out,
    get_server_memory,
    delete_facts,
    get_user,
    create_user,
    add_alias,
    get_aliases,
    find_user_by_alias,
)
from utils.database_summarizer import DatabaseSummarizer
from utils.logger import get_logger
from utils.i18n import get_locale_from_guild, get_locale_from_interaction, t
from utils.memory_limits import get_memory_limit_error_message, validate_fact_content

logger = get_logger(__name__)


class Memories(commands.Cog):
    remember_group = app_commands.Group(name="remember", description="Save personal or server memories.")

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
        self.db_summarizer = DatabaseSummarizer()

    async def _summarize_facts(
        self,
        existing: list[str],
        new_fact: str,
        scope_label: str = "user memory",
    ) -> list[str] | None:
        return await self.db_summarizer.summarize_fact_entries(
            existing=existing,
            new_entry=new_fact,
            scope_label=scope_label,
        )
    
    @commands.command(name="set_timezone", aliases=["tz", "timezone"])
    async def set_user_timezone(self, ctx: commands.Context, *, timezone: str):
        """
        Set your timezone for meal check reminders.
        
        Args:
            timezone: IANA timezone string (e.g., "Asia/Dhaka") or abbreviation (e.g., "EST", "PST")
        """
        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return

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
        await set_timezone(ctx.guild.id, ctx.author.id, timezone)
        
        # Get current time in that timezone
        from datetime import datetime
        current_time = datetime.now(tz).strftime("%H:%M")
        
        await ctx.send(
            f"✅ Timezone set to **{timezone}**!\n"
            f"Your current time: `{current_time}`"
        )
    
    def _extract_remember_target(self, ctx: commands.Context, fact: str) -> tuple[discord.Member, str]:
        target = ctx.author
        fact_text = fact.strip()
        if ctx.message.mentions:
            mention = ctx.message.mentions[0]
            tokens = [f"<@{mention.id}>", f"<@!{mention.id}>"]
            for token in tokens:
                if fact_text.startswith(token):
                    target = mention
                    fact_text = fact_text[len(token):].strip()
                    break
        return target, fact_text

    @staticmethod
    def _can_override_personal_memory(actor: discord.abc.User) -> bool:
        permissions = getattr(actor, "guild_permissions", None)
        return bool(getattr(permissions, "manage_guild", False))

    async def _remember_fact_for(self, ctx: commands.Context, target: discord.Member, fact: str) -> None:
        if not ctx.guild:
            await ctx.send(t("facts.server_only", get_locale_from_guild(ctx.guild)))
            return
        if target.id != ctx.author.id and not self._can_override_personal_memory(ctx.author):
            await ctx.send(
                "You can only save durable personal memory for yourself. "
                "A moderator or admin must use an explicit override flow for another user."
            )
            return
        validation = validate_fact_content(fact)
        if not validation.is_valid:
            await ctx.send(get_memory_limit_error_message(validation))
            return

        await create_user(ctx.guild.id, target.id)
        if await get_personal_memory_opt_out(ctx.guild.id, target.id):
            await ctx.send(f"{target.display_name} has opted out of personal memory in this server.")
            return

        existing = await get_personal_memories(ctx.guild.id, target.id, include_private=True)
        summarized = await self._summarize_facts(existing, fact) if existing else None

        if summarized:
            validated_items: list[str] = []
            for item in summarized:
                item_validation = validate_fact_content(item)
                if not item_validation.is_valid:
                    await ctx.send(get_memory_limit_error_message(item_validation))
                    return
                validated_items.append(item)

            await delete_facts(ctx.guild.id, target.id)
            for item in validated_items:
                await add_fact(ctx.guild.id, target.id, item)

            await ctx.send(
                f"Updated memory for {target.display_name} with {len(summarized)} fact(s)."
            )
            return

        await add_fact(ctx.guild.id, target.id, fact)
        target_text = f" for {target.display_name}" if target.id != ctx.author.id else ""

        await ctx.send(
            f"Got it! I'll remember that{target_text}."
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
            await ctx.send(t("facts.server_only", get_locale_from_guild(ctx.guild)))
            return

        target, fact_text = self._extract_remember_target(ctx, fact)
        if not fact_text:
            await ctx.send("Please provide a fact to remember.")
            return

        await self._remember_fact_for(ctx, target, fact_text)

    @commands.command(name="forget")
    async def forget_facts(self, ctx: commands.Context, scope: str = None):
        """
        Delete all stored facts about yourself.
        
        TODO:
            - [ ] Add confirmation prompt
            - [ ] Allow deleting specific facts by ID
        """
        if not ctx.guild:
            await ctx.send(t("facts.server_only", get_locale_from_guild(ctx.guild)))
            return
        scope_value = (scope or "").lower().strip()
        memory_types = ["personal"]
        target_id = ctx.author.id

        if scope_value in {"short", "short_term"}:
            memory_types = ["short_term"]
        elif scope_value in {"long", "long_term"}:
            memory_types = ["personal"]
        elif scope_value in {"all"}:
            memory_types = ["personal", "short_term"]
        elif scope_value in {"server"}:
            if not ctx.author.guild_permissions.manage_guild:
                await ctx.send("You need Manage Server to clear server memory.")
                return
            memory_types = ["server"]
            target_id = 0

        count = await delete_facts(ctx.guild.id, target_id, memory_types=memory_types)

        if count == 0:
            await ctx.send("🤔 I don't have any facts stored for that scope.")
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
            await ctx.send(t("profiles.server_only", get_locale_from_guild(ctx.guild)))
            return

        user = await get_user(ctx.guild.id, ctx.author.id)
        facts = await get_personal_memories(ctx.guild.id, ctx.author.id, include_private=True)
        
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

        facts = await get_mention_lookup_personal_memories(ctx.guild.id, member.id, limit=10)
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
            !birthday set MM-DD - Set a birthday
            !birthday set MM-DD @user - Set someone else's birthday
            !birthday upcoming  - See upcoming birthdays
        """
        from utils.db_handler import get_birthday

        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return
        
        target = member or ctx.author
        bday = await get_birthday(ctx.guild.id, target.id)
        
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
    async def birthday_set(self, ctx: commands.Context, date: str, member: discord.Member = None):
        """
        Set a birthday (format: MM-DD).
        
        Examples:
            !birthday set 03-15  (March 15th)
            !birthday set 12-25  (December 25th)
            !birthday set 03-15 @user
        """
        from utils.db_handler import set_birthday
        import re

        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return
        
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
        
        target = member or ctx.author
        await set_birthday(ctx.guild.id, target.id, date)
        
        month_name = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ][month]
        
        target_text = target.display_name if target.id != ctx.author.id else "you"
        await ctx.send(f"🎂 Birthday set to **{month_name} {day}** for {target_text}! I'll remember~ ♡")
    
    @birthday.command(name="upcoming")
    async def birthday_upcoming(self, ctx: commands.Context):
        """See upcoming birthdays in the next 3 months."""
        from utils.db_handler import get_upcoming_birthdays

        if not ctx.guild:
            await ctx.send("Please use this command in a server.")
            return
        
        upcoming = await get_upcoming_birthdays(ctx.guild.id, 90)
        
        if not upcoming:
            await ctx.send("📅 No birthdays coming up in the next 3 months!")
            return
        
        embed = discord.Embed(
            title="🎂 Upcoming Birthdays (Next 3 Months)",
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

    @app_commands.command(name="timezone", description="Set your timezone.")
    @app_commands.describe(timezone="IANA timezone or abbreviation (e.g., Asia/Dhaka, EST)")
    async def set_user_timezone_slash(self, interaction: discord.Interaction, timezone: str):
        if not interaction.guild:
            await interaction.response.send_message("Please use this command in a server.", ephemeral=True)
            return

        TIMEZONE_ALIASES = {
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
            "GMT": "Europe/London",
            "BST": "Europe/London",
            "CET": "Europe/Paris",
            "CEST": "Europe/Paris",
            "EET": "Europe/Helsinki",
            "EEST": "Europe/Helsinki",
            "WET": "Europe/Lisbon",
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
            "AEST": "Australia/Sydney",
            "AEDT": "Australia/Sydney",
            "ACST": "Australia/Adelaide",
            "AWST": "Australia/Perth",
            "UTC": "UTC",
            "MTC": "Europe/Moscow",
            "MSK": "Europe/Moscow",
            "GST": "Asia/Dubai",
            "AST": "Asia/Riyadh",
            "NZST": "Pacific/Auckland",
            "NZDT": "Pacific/Auckland",
        }

        tz_input = timezone.strip().upper()
        if tz_input in TIMEZONE_ALIASES:
            timezone = TIMEZONE_ALIASES[tz_input]

        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            abbrev_examples = ", ".join(list(TIMEZONE_ALIASES.keys())[:8])
            await interaction.response.send_message(
                f"❌ Unknown timezone: `{timezone}`\n"
                f"**Abbreviations:** `{abbrev_examples}`, ...\n"
                f"**Full format:** `Asia/Dhaka`, `America/New_York`, `Europe/London`\n"
                f"Find more: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
                ephemeral=True,
            )
            return

        await set_timezone(interaction.guild.id, interaction.user.id, timezone)

        from datetime import datetime
        current_time = datetime.now(tz).strftime("%H:%M")

        await interaction.response.send_message(
            f"✅ Timezone set to **{timezone}**!\n"
            f"Your current time: `{current_time}`"
        )

    @remember_group.command(name="personal", description="Save a personal fact.")
    @app_commands.describe(fact="The fact to remember", member="User to store the fact for (optional)")
    async def remember_fact_slash(self, interaction: discord.Interaction, fact: str, member: discord.Member = None):
        if not interaction.guild:
            await interaction.response.send_message(
                t("facts.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return

        if not fact.strip():
            await interaction.response.send_message("Please provide a fact to remember.", ephemeral=True)
            return
        validation = validate_fact_content(fact.strip())
        if not validation.is_valid:
            await interaction.response.send_message(
                get_memory_limit_error_message(validation),
                ephemeral=True,
            )
            return

        target = member or interaction.user
        if target.id != interaction.user.id and not self._can_override_personal_memory(interaction.user):
            await interaction.response.send_message(
                "You can only save durable personal memory for yourself. "
                "A moderator or admin must use an explicit override flow for another user.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(thinking=True)

        await create_user(interaction.guild.id, target.id)
        if await get_personal_memory_opt_out(interaction.guild.id, target.id):
            await interaction.followup.send(
                f"{target.display_name} has opted out of personal memory in this server.",
                ephemeral=True,
            )
            return
        existing = await get_personal_memories(interaction.guild.id, target.id, include_private=True)
        summarized = await self._summarize_facts(existing, fact) if existing else None

        if summarized:
            validated_items: list[str] = []
            for item in summarized:
                item_validation = validate_fact_content(item)
                if not item_validation.is_valid:
                    await interaction.followup.send(
                        get_memory_limit_error_message(item_validation),
                        ephemeral=True,
                    )
                    return
                validated_items.append(item)

            await delete_facts(interaction.guild.id, target.id)
            for item in validated_items:
                await add_fact(interaction.guild.id, target.id, item)

            await interaction.followup.send(
                f"Updated memory for {target.display_name} with {len(summarized)} fact(s)."
            )
            return

        await add_fact(interaction.guild.id, target.id, fact)
        target_text = f" for {target.display_name}" if target.id != interaction.user.id else ""
        await interaction.followup.send(f"Got it! I'll remember that{target_text}.")

    @remember_group.command(name="server", description="Save a server memory.")
    @app_commands.describe(fact="Server-wide memory entry")
    async def remember_server_slash(self, interaction: discord.Interaction, fact: str):
        if not interaction.guild:
            await interaction.response.send_message(
                t("facts.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server to add server memory.",
                ephemeral=True,
            )
            return

        if not fact.strip():
            await interaction.response.send_message("Please provide a server memory to remember.", ephemeral=True)
            return
        validation = validate_fact_content(fact.strip())
        if not validation.is_valid:
            await interaction.response.send_message(
                get_memory_limit_error_message(validation),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        clean_fact = fact.strip()
        existing = await get_server_memory(interaction.guild.id)
        summarized = (
            await self._summarize_facts(existing, clean_fact, scope_label="server memory")
            if existing
            else None
        )

        if summarized:
            validated_items: list[str] = []
            for item in summarized:
                item_validation = validate_fact_content(item)
                if not item_validation.is_valid:
                    await interaction.followup.send(
                        get_memory_limit_error_message(item_validation),
                        ephemeral=True,
                    )
                    return
                validated_items.append(item)

            await delete_facts(interaction.guild.id, 0, memory_types=["server"])
            for item in validated_items:
                await add_server_memory(
                    interaction.guild.id,
                    item,
                    source="manual",
                    learned_from_user_id=interaction.user.id,
                )
            await interaction.followup.send(
                f"Updated server memory with {len(validated_items)} reconciled fact(s).",
                ephemeral=True,
            )
            return

        await add_server_memory(
            interaction.guild.id,
            clean_fact,
            source="manual",
            learned_from_user_id=interaction.user.id,
        )
        locale = get_locale_from_interaction(interaction)
        await interaction.followup.send(
            t("remember.server.saved", locale),
            ephemeral=True,
        )

    @app_commands.command(name="forget", description="Clear stored memory.")
    @app_commands.describe(scope="Memory scope to clear", document_id="Document ID (for scope=document)")
    @app_commands.choices(scope=[
        app_commands.Choice(name="personal", value="personal"),
        app_commands.Choice(name="short_term", value="short_term"),
        app_commands.Choice(name="all", value="all"),
        app_commands.Choice(name="server", value="server"),
        app_commands.Choice(name="document", value="document"),
    ])
    async def forget_facts_slash(
        self,
        interaction: discord.Interaction,
        scope: app_commands.Choice[str] = None,
        document_id: int = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                t("facts.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return
        scope_value = scope.value if scope else "personal"
        memory_types = ["personal"]
        target_id = interaction.user.id

        if scope_value == "short_term":
            memory_types = ["short_term"]
        elif scope_value == "all":
            memory_types = ["personal", "short_term"]
        elif scope_value == "server":
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "You need Manage Server to clear server memory.",
                    ephemeral=True,
                )
                return
            memory_types = ["server"]
            target_id = 0
        elif scope_value == "document":
            from utils.rag_store import delete_document
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "You need Manage Server to delete documents.",
                    ephemeral=True,
                )
                return
            if not document_id:
                await interaction.response.send_message(
                    "Provide a document ID to delete.",
                    ephemeral=True,
                )
                return
            deleted = await delete_document(interaction.guild.id, int(document_id))
            if deleted:
                await interaction.response.send_message("Document deleted.", ephemeral=True)
            else:
                await interaction.response.send_message("Document not found.", ephemeral=True)
            return

        count = await delete_facts(interaction.guild.id, target_id, memory_types=memory_types)

        if count == 0:
            await interaction.response.send_message("🤔 I don't have any facts stored for that scope!")
        else:
            await interaction.response.send_message(f"🗑️ Cleared {count} fact(s) from memory!")

    @app_commands.command(name="myinfo", description="View your stored timezone and facts.")
    async def show_user_info_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                t("profiles.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return

        user = await get_user(interaction.guild.id, interaction.user.id)
        facts = await get_personal_memories(interaction.guild.id, interaction.user.id, include_private=True)

        embed = discord.Embed(
            title=f"📋 {interaction.user.display_name}'s Profile",
            color=discord.Color.pink(),
        )

        timezone = user.get("timezone", "Not set") if user else "Not set"
        embed.add_field(
            name="🌍 Timezone",
            value=f"`{timezone}`",
            inline=True,
        )

        if facts:
            facts_text = "\n".join(f"• {fact}" for fact in facts[:10])
            if len(facts) > 10:
                facts_text += f"\n... and {len(facts) - 10} more"
            embed.add_field(
                name=f"📝 Remembered Facts ({len(facts)})",
                value=facts_text,
                inline=False,
            )
        else:
            embed.add_field(
                name="📝 Remembered Facts",
                value="*No facts stored yet. Use `/remember personal <fact>` to add some!*",
                inline=False,
            )

        embed.set_footer(text="Use /remember personal to add facts, /forget to clear them")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="aka", description="Add an alias for a user.")
    @app_commands.describe(member="User to alias", alias="Alias name")
    async def add_user_alias_slash(self, interaction: discord.Interaction, member: discord.Member, alias: str):
        if not interaction.guild:
            await interaction.response.send_message("Please use this command in a server.", ephemeral=True)
            return
        if not member or not alias:
            await interaction.response.send_message("Usage: `/aka @user <alias>`", ephemeral=True)
            return

        alias = alias.strip()
        if not alias:
            await interaction.response.send_message("Please provide a non-empty alias.", ephemeral=True)
            return
        if len(alias) > 64:
            await interaction.response.send_message("Alias too long. Please keep it under 64 characters.", ephemeral=True)
            return

        added = await add_alias(interaction.guild.id, member.id, alias, interaction.user.id)
        if added:
            await interaction.response.send_message(f"Added alias `{alias}` for {member.display_name}.")
        else:
            await interaction.response.send_message(
                f"`{alias}` is already an alias for {member.display_name}.",
                ephemeral=True,
            )

    @app_commands.command(name="aliases", description="List aliases for a user.")
    @app_commands.describe(member="User to list aliases for (optional)")
    async def list_user_aliases_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        if not interaction.guild:
            await interaction.response.send_message("Please use this command in a server.", ephemeral=True)
            return

        target = member or interaction.user
        aliases = await get_aliases(interaction.guild.id, target.id)
        if not aliases:
            await interaction.response.send_message(
                f"No aliases found for {target.display_name}.",
                ephemeral=True,
            )
            return

        alias_text = ", ".join(aliases[:20])
        if len(aliases) > 20:
            alias_text += f", ... (+{len(aliases) - 20} more)"

        embed = discord.Embed(
            title=f"Aliases for {target.display_name}",
            description=alias_text,
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="whois", description="Find a user by alias.")
    @app_commands.describe(alias="Alias to look up")
    async def whois_alias_slash(self, interaction: discord.Interaction, alias: str):
        if not interaction.guild:
            await interaction.response.send_message("Please use this command in a server.", ephemeral=True)
            return

        alias = alias.strip()
        if not alias:
            await interaction.response.send_message("Usage: `/whois <alias>`", ephemeral=True)
            return

        user_id = await find_user_by_alias(interaction.guild.id, alias)
        if not user_id:
            await interaction.response.send_message(
                f"No user found with alias `{alias}`.",
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(user_id)
        if member:
            await interaction.response.send_message(f"`{alias}` belongs to {member.mention}.")
            return

        user = self.bot.get_user(user_id)
        if user:
            await interaction.response.send_message(f"`{alias}` belongs to {user.name} (`{user_id}`).")
        else:
            await interaction.response.send_message(f"`{alias}` belongs to user ID `{user_id}`.")

    @app_commands.command(name="aboutuser", description="View facts about another user.")
    @app_commands.describe(member="User to view facts for")
    async def about_user_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.guild:
            await interaction.response.send_message("Please use this command in a server.", ephemeral=True)
            return

        if member is None:
            await interaction.response.send_message("Usage: `/aboutuser @user`", ephemeral=True)
            return

        facts = await get_mention_lookup_personal_memories(interaction.guild.id, member.id, limit=10)
        if not facts:
            await interaction.response.send_message(
                f"I don't have any facts stored about {member.display_name}.",
                ephemeral=True,
            )
            return

        facts_text = "\n".join(f"- {fact}" for fact in facts[:10])
        if len(facts) > 10:
            facts_text += f"\n... and {len(facts) - 10} more"

        embed = discord.Embed(
            title=f"Facts about {member.display_name}",
            description=facts_text,
            color=discord.Color.pink(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="birthday", description="View or set birthdays.")
    @app_commands.describe(
        action="view, set, or upcoming",
        member="User to view or set (optional)",
        date="MM-DD (required for set)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="set", value="set"),
        app_commands.Choice(name="upcoming", value="upcoming"),
    ])
    async def birthday_slash(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str] = None,
        date: str = None,
        member: discord.Member = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message("Please use this command in a server.", ephemeral=True)
            return

        from utils.db_handler import get_birthday, set_birthday, get_upcoming_birthdays
        import re

        action_value = action.value if action else "view"

        if action_value == "view":
            target = member or interaction.user
            bday = await get_birthday(interaction.guild.id, target.id)

            if bday:
                month, day = bday.split("-")
                month_name = [
                    "", "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"
                ][int(month)]
                await interaction.response.send_message(
                    f"🎂 {target.display_name}'s birthday is **{month_name} {int(day)}**!"
                )
            else:
                if target == interaction.user:
                    await interaction.response.send_message(
                        "📅 You haven't set your birthday yet! Use `/birthday set MM-DD`",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"📅 {target.display_name} hasn't set their birthday yet!",
                        ephemeral=True,
                    )
            return

        if action_value == "set":
            if not date:
                await interaction.response.send_message(
                    "Please provide a date in MM-DD format.",
                    ephemeral=True,
                )
                return

            if not re.match(r"^\d{2}-\d{2}$", date):
                await interaction.response.send_message(
                    "❌ Invalid format! Use `MM-DD` (e.g., `03-15` for March 15th)",
                    ephemeral=True,
                )
                return

            month, day = map(int, date.split("-"))
            if month < 1 or month > 12:
                await interaction.response.send_message("❌ Month must be between 01 and 12!", ephemeral=True)
                return

            days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if day < 1 or day > days_in_month[month]:
                await interaction.response.send_message(
                    f"❌ Invalid day for month {month:02d}!",
                    ephemeral=True,
                )
                return

            target = member or interaction.user
            await set_birthday(interaction.guild.id, target.id, date)

            month_name = [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ][month]

            target_text = target.display_name if target.id != interaction.user.id else "you"
            await interaction.response.send_message(
                f"🎂 Birthday set to **{month_name} {day}** for {target_text}! I'll remember~ ♡"
            )
            return

        if action_value == "upcoming":
            upcoming = await get_upcoming_birthdays(interaction.guild.id, 90)

            if not upcoming:
                await interaction.response.send_message(
                    "📅 No birthdays coming up in the next 3 months!",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="🎂 Upcoming Birthdays (Next 3 Months)",
                color=discord.Color.pink(),
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
                    inline=True,
                )

            await interaction.response.send_message(embed=embed)
            return


    # ============================================
    # User Profile Analysis
    # ============================================

    @app_commands.command(name="analyze", description="Get a fun, AI-generated summary of someone's personality based on their messages.")
    @app_commands.describe(member="User to analyze (default: yourself)")
    async def analyze_user(self, interaction: discord.Interaction, member: discord.Member = None):
        """Analyze a user's message history and generate a character summary."""
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        target = member or interaction.user
        
        # Defer response since this takes time
        await interaction.response.defer(thinking=True)

        try:
            from utils.api_manager import UserInputError
            from utils.guild_ai import generate_guild_gemini_profile_text, GuildConfigError

            # Collect messages from all channels the bot can see
            messages = []
            for channel in interaction.guild.text_channels:
                try:
                    async for msg in channel.history(limit=500):
                        if msg.author.id == target.id and msg.content.strip():
                            messages.append(msg.content[:200])
                            if len(messages) >= 500:
                                break
                    if len(messages) >= 500:
                        break
                except Exception:
                    continue

            if len(messages) < 10:
                await interaction.followup.send(
                    f"Not enough messages for {target.display_name}. Need 10, found {len(messages)}.",
                    ephemeral=True
                )
                return

            # Get saved facts
            facts = await get_facts(interaction.guild.id, target.id)
            facts_text = "\n".join(f"- {fact}" for fact in facts) if facts else "(no saved facts)"

            # Build the analysis prompt
            sample_messages = messages[:100]
            messages_text = "\n".join(f"- {msg}" for msg in sample_messages)

            prompt = f"""You are a witty personality analyst. Based on these messages and facts about a Discord user, write a hilarious, thought-provoking character analysis.

Be creative and make interesting observations about:
- Communication style
- Likely interests/hobbies
- Personality quirks
- What they might be like IRL
- A funny "warning label" for them
- A creative nickname

Keep it playful, not mean. Use emojis. Be creative!

=== FACTS ===
{facts_text}

=== MESSAGES ({len(sample_messages)}/{len(messages)}) ===
{messages_text}

Write the analysis:"""

            try:
                response, _ = await generate_guild_gemini_profile_text(interaction.guild.id, prompt)
            except GuildConfigError:
                await interaction.followup.send(
                    "Profile analysis not configured. Ask admin to set GEMINI_PROFILE_KEY.",
                    ephemeral=True,
                )
                return
            except UserInputError:
                await interaction.followup.send("Could not analyze - content may be sensitive.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"Character Analysis: {target.display_name}",
                description=response[:4000] if len(response) > 4000 else response,
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text=f"Based on {len(messages)} messages | By {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Error in analyze: %s", e, exc_info=True)
            await interaction.followup.send("Something went wrong. Try again later.", ephemeral=True)




async def setup(bot: commands.Bot):
    """Load the Memories cog."""
    await bot.add_cog(Memories(bot))
