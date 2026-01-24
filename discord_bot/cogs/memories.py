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
    get_facts,
    delete_facts,
    get_user,
    create_user,
    add_alias,
    get_aliases,
    find_user_by_alias,
)
from utils.api_manager import get_gemini_summarize_manager, UserInputError
from utils.logger import get_logger

logger = get_logger(__name__)

FACT_SUMMARY_PROMPT = """You are a database reconciler. Analyze the following user facts.
If facts contradict (e.g., "User is X" and "User is not X"), delete both and replace with a neutral summary.
Remove duplicates.
Output a clean, bulleted list of current truths only.

Facts:
{existing_facts}

New fact to add:
{new_fact}
"""


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
        try:
            self.summarizer = get_gemini_summarize_manager()
        except ValueError:
            self.summarizer = None

    def _parse_fact_summary(self, summary_text: str) -> list[str]:
        facts = []
        for line in summary_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped[0] in ("-", "*"):
                stripped = stripped[1:].strip()
            if not stripped:
                continue
            facts.append(stripped)
        # Deduplicate while preserving order
        return list(dict.fromkeys(facts))

    async def _summarize_facts(self, existing: list[str], new_fact: str) -> list[str] | None:
        if not self.summarizer:
            return None

        prompt = FACT_SUMMARY_PROMPT.format(
            existing_facts="\n".join(f"- {fact}" for fact in existing) or "(none)",
            new_fact=new_fact,
        )
        try:
            summary, _ = await self.summarizer.generate(prompt)
        except UserInputError:
            return None
        except Exception as exc:
            logger.warning("Fact summarization failed: %s", exc)
            return None

        parsed = self._parse_fact_summary(summary)
        return parsed or None
    
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

    async def _remember_fact_for(self, ctx: commands.Context, target: discord.Member, fact: str) -> None:
        if not ctx.guild:
            await ctx.send("Facts are server-specific. Use this in a server.")
            return

        if len(fact) > 500:
            await ctx.send("Fact too long! Please keep it under 500 characters.")
            return

        await create_user(ctx.guild.id, target.id)

        existing = await get_facts(ctx.guild.id, target.id)
        summarized = await self._summarize_facts(existing, fact) if existing else None

        if summarized:
            await delete_facts(ctx.guild.id, target.id)
            for item in summarized:
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
            await ctx.send("Facts are server-specific. Use this in a server.")
            return

        target, fact_text = self._extract_remember_target(ctx, fact)
        if not fact_text:
            await ctx.send("Please provide a fact to remember.")
            return

        await self._remember_fact_for(ctx, target, fact_text)

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

        user = await get_user(ctx.guild.id, ctx.author.id)
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

    async def _slash_context(self, interaction: discord.Interaction) -> commands.Context:
        return await commands.Context.from_interaction(interaction)

    @app_commands.command(name="timezone", description="Set your timezone.")
    @app_commands.describe(timezone="IANA timezone or abbreviation (e.g., Asia/Dhaka, EST)")
    async def set_user_timezone_slash(self, interaction: discord.Interaction, timezone: str):
        ctx = await self._slash_context(interaction)
        await self.set_user_timezone(ctx, timezone=timezone)

    @app_commands.command(name="remember", description="Save a fact about yourself.")
    @app_commands.describe(fact="The fact to remember", member="User to store the fact for (optional)")
    async def remember_fact_slash(self, interaction: discord.Interaction, fact: str, member: discord.Member = None):
        ctx = await self._slash_context(interaction)
        target = member or interaction.user
        await self._remember_fact_for(ctx, target, fact)

    @app_commands.command(name="forget", description="Clear your stored facts.")
    async def forget_facts_slash(self, interaction: discord.Interaction):
        ctx = await self._slash_context(interaction)
        await self.forget_facts(ctx)

    @app_commands.command(name="myinfo", description="View your stored timezone and facts.")
    async def show_user_info_slash(self, interaction: discord.Interaction):
        ctx = await self._slash_context(interaction)
        await self.show_user_info(ctx)

    @app_commands.command(name="aka", description="Add an alias for a user.")
    @app_commands.describe(member="User to alias", alias="Alias name")
    async def add_user_alias_slash(self, interaction: discord.Interaction, member: discord.Member, alias: str):
        ctx = await self._slash_context(interaction)
        await self.add_user_alias(ctx, member=member, alias=alias)

    @app_commands.command(name="aliases", description="List aliases for a user.")
    @app_commands.describe(member="User to list aliases for (optional)")
    async def list_user_aliases_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        ctx = await self._slash_context(interaction)
        await self.list_user_aliases(ctx, member=member)

    @app_commands.command(name="whois", description="Find a user by alias.")
    @app_commands.describe(alias="Alias to look up")
    async def whois_alias_slash(self, interaction: discord.Interaction, alias: str):
        ctx = await self._slash_context(interaction)
        await self.whois_alias(ctx, alias=alias)

    @app_commands.command(name="aboutuser", description="View facts about another user.")
    @app_commands.describe(member="User to view facts for")
    async def about_user_slash(self, interaction: discord.Interaction, member: discord.Member):
        ctx = await self._slash_context(interaction)
        await self.about_user(ctx, member=member)

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
        ctx = await self._slash_context(interaction)
        action_value = action.value if action else "view"

        if action_value == "view":
            await self.birthday(ctx, member=member)
            return

        if action_value == "set":
            if not date:
                await interaction.response.send_message(
                    "Please provide a date in MM-DD format.",
                    ephemeral=True,
                )
                return
            await self.birthday_set(ctx, date=date, member=member)
            return

        if action_value == "upcoming":
            await self.birthday_upcoming(ctx)
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
            # Import profile manager
            from utils.api_manager import get_gemini_profile_manager, UserInputError
            try:
                profile_manager = get_gemini_profile_manager()
            except ValueError:
                await interaction.followup.send(
                    "Profile analysis not configured. Ask admin to set GEMINI_PROFILE_KEY.",
                    ephemeral=True
                )
                return

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
            facts_text = "
".join(f"- {fact}" for fact in facts) if facts else "(no saved facts)"

            # Build the analysis prompt
            sample_messages = messages[:100]
            messages_text = "
".join(f"- {msg}" for msg in sample_messages)

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
                response, _ = await profile_manager.generate(prompt)
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
