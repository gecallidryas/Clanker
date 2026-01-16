"""
Admin Cog for Femmy Discord Bot
===============================
Admin commands for managing user data, facts, and affection.

Commands (Admin Only):
    !admin reset @user [type]     - Reset user data (all/facts/affection/aliases)
    !admin setfact @user <fact>   - Add a fact for a user
    !admin delfact @user <id>     - Delete a specific fact by ID
    !admin setaffection @user <n> - Set affection points
    !admin view @user             - View complete user profile
"""

import discord
from discord.ext import commands

from utils.db_handler import (
    reset_user_data,
    set_affection_value,
    get_user_full_profile,
    add_fact_with_source,
    delete_fact_by_id,
    get_facts_detailed
)
from utils.logger import get_logger

logger = get_logger(__name__)


class Admin(commands.Cog):
    """Admin commands for user data management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_check(self, ctx: commands.Context) -> bool:
        """Only allow admins to use these commands."""
        if not ctx.guild:
            return False
        return ctx.author.guild_permissions.manage_guild
    
    @commands.group(name="admin", invoke_without_command=True)
    async def admin_group(self, ctx: commands.Context):
        """Admin commands for user management."""
        embed = discord.Embed(
            title="🔧 Admin Commands",
            description="Manage user data and bot settings.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="User Data",
            value=(
                "`!admin reset @user [type]` - Reset data (all/facts/affection/aliases)\n"
                "`!admin view @user` - View complete profile\n"
            ),
            inline=False
        )
        embed.add_field(
            name="Facts",
            value=(
                "`!admin setfact @user <fact>` - Add a fact\n"
                "`!admin delfact @user <id>` - Delete fact by ID\n"
            ),
            inline=False
        )
        embed.add_field(
            name="Affection",
            value="`!admin setaffection @user <points>` - Set affection",
            inline=False
        )
        await ctx.send(embed=embed)
    
    @admin_group.command(name="reset")
    async def reset_user(self, ctx: commands.Context, member: discord.Member, reset_type: str = "all"):
        """Reset user data. Types: all, facts, affection, aliases"""
        valid_types = ["all", "facts", "affection", "aliases"]
        if reset_type.lower() not in valid_types:
            await ctx.send(f"❌ Invalid type. Use one of: {', '.join(valid_types)}")
            return
        
        deleted = await reset_user_data(member.id, reset_type.lower())
        
        embed = discord.Embed(
            title=f"🗑️ Reset Data for {member.display_name}",
            color=discord.Color.red()
        )
        
        if reset_type == "all":
            embed.add_field(name="Facts Deleted", value=str(deleted["facts"]), inline=True)
            embed.add_field(name="Affection Reset", value="Yes" if deleted["affection"] else "No", inline=True)
            embed.add_field(name="Aliases Deleted", value=str(deleted["aliases"]), inline=True)
        else:
            embed.description = f"Reset `{reset_type}` for {member.mention}"
        
        await ctx.send(embed=embed)
        logger.info(f"Admin {ctx.author} reset {reset_type} for {member}")
    
    @admin_group.command(name="view")
    async def view_user(self, ctx: commands.Context, member: discord.Member):
        """View complete user profile."""
        profile = await get_user_full_profile(member.id)
        
        embed = discord.Embed(
            title=f"👤 Profile: {member.display_name}",
            color=discord.Color.blue()
        )
        
        # Affection
        aff = profile.get("affection", {})
        embed.add_field(
            name="💕 Affection",
            value=f"{aff.get('affection_points', 0)} pts ({aff.get('affection_level', 'stranger')})",
            inline=True
        )
        
        # Timezone
        embed.add_field(
            name="🌍 Timezone",
            value=profile.get("timezone", "Not set"),
            inline=True
        )
        
        # Birthday
        embed.add_field(
            name="🎂 Birthday",
            value=profile.get("birthday") or "Not set",
            inline=True
        )
        
        # Aliases
        aliases = profile.get("aliases", [])
        if aliases:
            embed.add_field(
                name=f"📛 Aliases ({len(aliases)})",
                value=", ".join(aliases[:10]) + ("..." if len(aliases) > 10 else ""),
                inline=False
            )
        
        # Facts
        facts = profile.get("facts", [])
        if facts:
            fact_list = []
            for f in facts[:5]:
                source = f.get("source", "manual")
                source_emoji = "📝" if source == "manual" else "🧠" if source == "learned" else "🔧"
                fact_list.append(f"{source_emoji} `{f['id']}` {f['fact'][:50]}...")
            
            embed.add_field(
                name=f"📋 Facts ({len(facts)} total)",
                value="\n".join(fact_list) if fact_list else "None",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @admin_group.command(name="setfact")
    async def set_fact(self, ctx: commands.Context, member: discord.Member, *, fact: str):
        """Add a fact for a user (admin source)."""
        fact_id = await add_fact_with_source(
            member.id,
            fact,
            source="admin",
            learned_from_user_id=ctx.author.id
        )
        
        await ctx.send(f"✅ Added fact #{fact_id} for {member.display_name}:\n> {fact}")
        logger.info(f"Admin {ctx.author} added fact for {member}: {fact[:50]}")
    
    @admin_group.command(name="delfact")
    async def del_fact(self, ctx: commands.Context, member: discord.Member, fact_id: int):
        """Delete a specific fact by ID."""
        # Verify fact belongs to user
        facts = await get_facts_detailed(member.id)
        fact_ids = [f["id"] for f in facts]
        
        if fact_id not in fact_ids:
            await ctx.send(f"❌ Fact #{fact_id} not found for {member.display_name}")
            return
        
        success = await delete_fact_by_id(fact_id)
        if success:
            await ctx.send(f"✅ Deleted fact #{fact_id} for {member.display_name}")
            logger.info(f"Admin {ctx.author} deleted fact #{fact_id} for {member}")
        else:
            await ctx.send("❌ Failed to delete fact")
    
    @admin_group.command(name="setaffection")
    async def set_affection(self, ctx: commands.Context, member: discord.Member, points: int):
        """Set a user's affection points."""
        if points < 0:
            await ctx.send("❌ Points cannot be negative")
            return
        
        result = await set_affection_value(member.id, points)
        
        await ctx.send(
            f"✅ Set {member.display_name}'s affection to "
            f"**{points}** points (Level: {result['affection_level']})"
        )
        logger.info(f"Admin {ctx.author} set affection for {member} to {points}")


async def setup(bot: commands.Bot):
    """Load the Admin cog."""
    await bot.add_cog(Admin(bot))
