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
from discord import app_commands
from discord.ext import commands

from utils.db_handler import (
    set_gender_role,
    delete_gender_role,
    reset_user_data,
    set_affection_value,
    get_user_full_profile,
    add_fact_with_source,
    delete_fact_by_id,
    get_facts_detailed
)
from utils.logger import get_logger

logger = get_logger(__name__)


async def _is_owner_check(interaction: discord.Interaction) -> bool:
    return await interaction.client.is_owner(interaction.user)


class Admin(commands.Cog):
    """Admin commands for user data management."""

    admin_app_group = app_commands.Group(
        name="admin",
        description="Admin commands",
    )
    gender_suggestions = [
        "male",
        "female",
        "nonbinary",
        "genderfluid",
        "agender",
        "trans",
        "transmasc",
        "transfem",
        "intersex",
        "queer",
        "other",
    ]
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        pass

    async def cog_unload(self):
        pass
    
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
        
        deleted = await reset_user_data(ctx.guild.id, member.id, reset_type.lower())
        
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
        profile = await get_user_full_profile(ctx.guild.id, member.id)
        
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
            ctx.guild.id,
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
        facts = await get_facts_detailed(ctx.guild.id, member.id)
        fact_ids = [f["id"] for f in facts]
        
        if fact_id not in fact_ids:
            await ctx.send(f"❌ Fact #{fact_id} not found for {member.display_name}")
            return
        
        success = await delete_fact_by_id(ctx.guild.id, fact_id)
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
        
        result = await set_affection_value(ctx.guild.id, member.id, points)
        
        await ctx.send(
            f"✅ Set {member.display_name}'s affection to "
            f"**{points}** points (Level: {result['affection_level']})"
        )
        logger.info(f"Admin {ctx.author} set affection for {member} to {points}")

    @admin_group.command(name="sync")
    async def sync_tree(self, ctx: commands.Context, target: str = "guild"):
        """
        Sync slash commands.
        Usage: 
            !admin sync guild (default) - Instant sync to this server
            !admin sync global - Sync globally (takes up to 1h)
        """
        if target == "guild":
            try:
                self.bot.tree.copy_global_to(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"Synced slash commands to **{ctx.guild.name}**! (Instant)")
            except Exception as e:
                logger.error("Guild sync failed: %s", e, exc_info=True)
                await ctx.send("Sync failed. Check logs for details.")
        elif target == "global":
            if await self.bot.is_owner(ctx.author):
                try:
                    await self.bot.tree.sync()
                    await ctx.send("Synced **global** commands. (Updates take up to 1h)")
                except Exception as e:
                    logger.error("Global sync failed: %s", e, exc_info=True)
                    await ctx.send("Sync failed. Check logs for details.")
            else:
                await ctx.send("Only bot owner can sync globally.")
        else:
            await ctx.send("Usage: `!admin sync [guild|global]`")

    @admin_group.command(name="clearglobal")
    async def clear_global_commands(self, ctx: commands.Context):
        """Clear all global slash commands (owner only)."""
        if not await self.bot.is_owner(ctx.author):
            await ctx.send("Only bot owner can clear global commands.")
            return
        try:
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync()
            await ctx.send("Cleared all global slash commands.")
        except Exception as e:
            logger.error("Clear global commands failed: %s", e, exc_info=True)
            await ctx.send("Clear global commands failed. Check logs for details.")

    @admin_group.command(name="clearguild")
    async def clear_guild_commands(self, ctx: commands.Context):
        """Clear all guild-specific slash commands for this server."""
        if not ctx.guild:
            await ctx.send("Use this command in a server.")
            return
        try:
            self.bot.tree.clear_commands(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"Cleared all guild slash commands for **{ctx.guild.name}**.")
        except Exception as e:
            logger.error("Clear guild commands failed: %s", e, exc_info=True)
            await ctx.send("Clear guild commands failed. Check logs for details.")

    @admin_app_group.command(name="reset", description="Reset user data.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="User to reset", reset_type="all, facts, affection, or aliases")
    @app_commands.choices(reset_type=[
        app_commands.Choice(name="all", value="all"),
        app_commands.Choice(name="facts", value="facts"),
        app_commands.Choice(name="affection", value="affection"),
        app_commands.Choice(name="aliases", value="aliases"),
    ])
    async def reset_user_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reset_type: app_commands.Choice[str] = None
    ):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        target = reset_type.value if reset_type else "all"
        valid_types = ["all", "facts", "affection", "aliases"]
        if target not in valid_types:
            await interaction.response.send_message(
                f"âŒ Invalid type. Use one of: {', '.join(valid_types)}",
                ephemeral=True,
            )
            return

        deleted = await reset_user_data(interaction.guild.id, member.id, target)

        embed = discord.Embed(
            title=f"ðŸ—‘ï¸ Reset Data for {member.display_name}",
            color=discord.Color.red(),
        )

        if target == "all":
            embed.add_field(name="Facts Deleted", value=str(deleted["facts"]), inline=True)
            embed.add_field(name="Affection Reset", value="Yes" if deleted["affection"] else "No", inline=True)
            embed.add_field(name="Aliases Deleted", value=str(deleted["aliases"]), inline=True)
        else:
            embed.description = f"Reset `{target}` for {member.mention}"

        await interaction.response.send_message(embed=embed)
        logger.info("Admin %s reset %s for %s", interaction.user, target, member)

    @admin_app_group.command(name="view", description="View a user's profile.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="User to view")
    async def view_user_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        profile = await get_user_full_profile(interaction.guild.id, member.id)

        embed = discord.Embed(
            title=f"ðŸ‘¤ Profile: {member.display_name}",
            color=discord.Color.blue(),
        )

        aff = profile.get("affection", {})
        embed.add_field(
            name="ðŸ’• Affection",
            value=f"{aff.get('affection_points', 0)} pts ({aff.get('affection_level', 'stranger')})",
            inline=True,
        )

        embed.add_field(
            name="ðŸŒ Timezone",
            value=profile.get("timezone", "Not set"),
            inline=True,
        )

        embed.add_field(
            name="ðŸŽ‚ Birthday",
            value=profile.get("birthday") or "Not set",
            inline=True,
        )

        aliases = profile.get("aliases", [])
        if aliases:
            embed.add_field(
                name=f"ðŸ“› Aliases ({len(aliases)})",
                value=", ".join(aliases[:10]) + ("..." if len(aliases) > 10 else ""),
                inline=False,
            )

        facts = profile.get("facts", [])
        if facts:
            fact_list = []
            for f in facts[:5]:
                source = f.get("source", "manual")
                source_emoji = "ðŸ“" if source == "manual" else "ðŸ§ " if source == "learned" else "ðŸ”§"
                fact_list.append(f"{source_emoji} `{f['id']}` {f['fact'][:50]}...")

            embed.add_field(
                name=f"ðŸ“‹ Facts ({len(facts)} total)",
                value="\n".join(fact_list) if fact_list else "None",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @admin_app_group.command(name="setfact", description="Add a fact for a user.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="User", fact="Fact to store")
    async def set_fact_slash(self, interaction: discord.Interaction, member: discord.Member, fact: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        fact_id = await add_fact_with_source(
            interaction.guild.id,
            member.id,
            fact,
            source="admin",
            learned_from_user_id=interaction.user.id,
        )

        await interaction.response.send_message(
            f"âœ… Added fact #{fact_id} for {member.display_name}:\n> {fact}"
        )
        logger.info("Admin %s added fact for %s: %s", interaction.user, member, fact[:50])

    @admin_app_group.command(name="delfact", description="Delete a fact by ID.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="User", fact_id="Fact ID")
    async def del_fact_slash(self, interaction: discord.Interaction, member: discord.Member, fact_id: int):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        facts = await get_facts_detailed(interaction.guild.id, member.id)
        fact_ids = [f["id"] for f in facts]

        if fact_id not in fact_ids:
            await interaction.response.send_message(
                f"âŒ Fact #{fact_id} not found for {member.display_name}",
                ephemeral=True,
            )
            return

        success = await delete_fact_by_id(interaction.guild.id, fact_id)
        if success:
            await interaction.response.send_message(
                f"âœ… Deleted fact #{fact_id} for {member.display_name}"
            )
            logger.info("Admin %s deleted fact #%s for %s", interaction.user, fact_id, member)
        else:
            await interaction.response.send_message("âŒ Failed to delete fact", ephemeral=True)

    @admin_app_group.command(name="affection", description="Set affection points for a user.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="User", points="Affection points")
    async def set_affection_slash(self, interaction: discord.Interaction, member: discord.Member, points: int):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        if points < 0:
            await interaction.response.send_message("âŒ Points cannot be negative", ephemeral=True)
            return

        result = await set_affection_value(interaction.guild.id, member.id, points)

        await interaction.response.send_message(
            f"âœ… Set {member.display_name}'s affection to "
            f"**{points}** points (Level: {result['affection_level']})"
        )
        logger.info("Admin %s set affection for %s to %s", interaction.user, member, points)

    @admin_app_group.command(name="model", description="Change the active AI model.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="Model key (optional)")
    async def set_model_slash(self, interaction: discord.Interaction, name: str = None):
        await interaction.response.send_message(
            "Model settings are now guild-specific. Use `/config model set` or `/config env upload`.",
            ephemeral=True,
        )

    @admin_app_group.command(name="clearglobal", description="Clear all global slash commands (owner only).")
    @app_commands.check(_is_owner_check)
    async def clear_global_commands_slash(self, interaction: discord.Interaction):
        try:
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync()
            await interaction.response.send_message("Cleared all global slash commands.")
        except Exception as e:
            logger.error("Clear global commands failed: %s", e, exc_info=True)
            await interaction.response.send_message(
                "Clear global commands failed. Check logs for details.",
                ephemeral=True,
            )

    @admin_app_group.command(
        name="clearguild",
        description="Clear all guild-specific slash commands for this server.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_guild_commands_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        try:
            self.bot.tree.clear_commands(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.response.send_message(
                f"Cleared all guild slash commands for **{interaction.guild.name}**.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error("Clear guild commands failed: %s", e, exc_info=True)
            await interaction.response.send_message(
                "Clear guild commands failed. Check logs for details.",
                ephemeral=True,
            )

    @app_commands.command(name="setgenderrole", description="Configure a gender role for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(role="Role to map", gender="Gender label (e.g. male, female, nonbinary) or 'clear'")
    async def set_gender_role_slash(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        gender: str,
    ):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        gender_value = gender.strip()
        if not gender_value:
            await interaction.response.send_message("Gender cannot be empty.", ephemeral=True)
            return
        if len(gender_value) > 32:
            await interaction.response.send_message("Gender must be 32 characters or fewer.", ephemeral=True)
            return
        if gender_value.lower() == "clear":
            removed = await delete_gender_role(interaction.guild.id, role.id)
            message = "Gender role mapping removed." if removed else "No mapping found for that role."
            await interaction.response.send_message(message, ephemeral=True)
            return

        try:
            await set_gender_role(interaction.guild.id, role.id, gender_value)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"Gender role mapping set: {role.mention} -> {gender_value}.",
            ephemeral=True,
        )

    @set_gender_role_slash.autocomplete("gender")
    async def set_gender_role_gender_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        if not current_lower:
            return [
                app_commands.Choice(name=label, value=label)
                for label in self.gender_suggestions[:25]
            ]

        matches = [
            label for label in self.gender_suggestions if current_lower in label
        ]
        if not matches and current_lower not in self.gender_suggestions:
            matches = [current_lower]

        return [
            app_commands.Choice(name=label, value=label)
            for label in matches[:25]
        ]


async def setup(bot: commands.Bot):
    """Load the Admin cog."""
    bot.tree.remove_command("admin")
    await bot.add_cog(Admin(bot), override=True)
