"""
Social Cog for Femmy Discord Bot
=================================
Handles bot personality mode switching and mention reactions.

Commands:
    !evil [on/off]   - Toggle uncensored mode
"""

import random
from io import BytesIO
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import (
    add_guild_config_audit,
    get_server_mode,
    get_evil_mode,
    set_evil_mode,
    get_autorole_config,
    get_welcome_config,
    get_dm_welcome_message,
    get_dm_welcome_enabled,
    get_dm_welcome_petpet_enabled,
    set_guild_avatar_path,
)
from utils.guild_ai import generate_guild_gemini_text, GuildConfigError
from utils.logger import get_logger
from utils.petpet import make_petpet
from utils.server_profile import set_custom_profile, set_mode_profile, set_member_nickname
from utils.persona_panel_ui import (
    MANAGE_GUIDANCE,
    set_persona_evil_mode,
)
from modes import get_mode_profile

logger = get_logger(__name__)


# Mode profiles are defined in discord_bot/modes

class Social(commands.Cog):
    """
    Social Cog - Personality mode management and reactions.
    
    Features:
        - Mention reactions
        - Greeting system
        
    TODO:
        - [ ] Add per-user mode preferences
        - [ ] Implement reaction randomization
        - [ ] Add custom greeting messages
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _set_mode_bio(self, guild_id: int, mode_key: str, custom_persona: dict | None = None) -> None:
        if custom_persona:
            bio = (custom_persona.get("bio") or f"Custom persona: {custom_persona.get('name', 'Unknown')}.").strip()
        else:
            bio = get_mode_profile(mode_key).bio
        bios = getattr(self.bot, "mode_bio_by_guild", None)
        if bios is None:
            bios = {}
            setattr(self.bot, "mode_bio_by_guild", bios)
        bios[guild_id] = bio

    def _get_mode_nickname(self, mode_key: str, custom_persona: dict | None = None) -> str:
        if custom_persona and custom_persona.get("name"):
            return str(custom_persona.get("name")).strip()
        if mode_key == "mode_oneesan":
            return "Yumi"
        if mode_key == "mode_default":
            return "Clanker"
        return "Femmy"

    async def _apply_mode_profile_updates(
        self,
        guild_id: int,
        mode_key: str,
        custom_persona: dict | None = None,
    ) -> None:
        self._set_mode_bio(guild_id, mode_key, custom_persona=custom_persona)

        try:
            if custom_persona:
                custom_bio = (custom_persona.get("bio") or f"Custom persona: {custom_persona.get('name', 'custom')}.").strip()
                banner_path = custom_persona.get("banner_path")
                if banner_path:
                    banner_file = Path(banner_path)
                    if banner_file.exists():
                        banner_bytes = banner_file.read_bytes()
                        success, reason = await set_custom_profile(
                            self.bot,
                            guild_id,
                            banner_bytes=banner_bytes,
                            bio=custom_bio,
                        )
                    else:
                        banner_path = None
                if not banner_path:
                    default_profile = get_mode_profile("mode_default")
                    success, reason = await set_mode_profile(
                        self.bot,
                        guild_id,
                        "mode_default",
                        bio=custom_bio,
                        banner_file=default_profile.banner_file,
                    )
            else:
                profile = get_mode_profile(mode_key)
                success, reason = await set_mode_profile(
                    self.bot,
                    guild_id,
                    mode_key,
                    bio=profile.bio,
                    banner_file=profile.banner_file,
                )
            if not success:
                logger.warning("Failed to update guild profile for %s: %s", mode_key, reason)
        except Exception as exc:
            logger.warning("Failed to update guild profile for %s: %s", mode_key, exc)

        try:
            nickname = self._get_mode_nickname(mode_key, custom_persona=custom_persona)
            nickname = nickname[:32].strip() if nickname else None
            if nickname == "":
                nickname = None
            success, reason = await set_member_nickname(self.bot, guild_id, nickname)
            if not success and reason != "forbidden":
                logger.warning("Failed to update guild nickname for %s: %s", mode_key, reason)
        except Exception as exc:
            logger.warning("Failed to update guild nickname for %s: %s", mode_key, exc)

        try:
            if custom_persona and custom_persona.get("avatar_path"):
                avatar_path = custom_persona.get("avatar_path")
                avatar_bytes = Path(avatar_path).read_bytes()
                from utils.server_avatar import set_custom_avatar
                success, reason = await set_custom_avatar(self.bot, guild_id, avatar_bytes)
                if not success:
                    logger.warning("Failed to update server avatar for %s: %s", mode_key, reason)
            else:
                await set_guild_avatar_path(guild_id, None)
                from utils.server_avatar import set_mode_avatar
                evil_mode_enabled = await get_evil_mode(guild_id)
                target_avatar_mode = mode_key if not custom_persona else "mode_default"
                success, reason = await set_mode_avatar(
                    self.bot,
                    guild_id,
                    target_avatar_mode,
                    evil_mode=evil_mode_enabled,
                    force=True,
                )
                if not success and reason != "custom":
                    logger.warning("Failed to update server avatar for %s: %s", mode_key, reason)
        except Exception as exc:
            logger.warning("Failed to update server avatar for %s: %s", mode_key, exc)

    async def _log_persona_presentation_audit(
        self,
        guild_id: int,
        user_id: int,
        *,
        action: str,
        summary: str,
        detail: dict | None = None,
        target_id: str | None = None,
    ) -> None:
        await add_guild_config_audit(
            guild_id,
            user_id,
            action,
            category="persona_presentation",
            target_type="persona_mode",
            target_id=target_id,
            summary=summary,
            detail=detail,
        )

    async def apply_evil_mode_change(
        self,
        guild: discord.Guild,
        actor: discord.abc.User,
        state: bool | None,
    ) -> tuple[bool, str]:
        current_mode = await get_server_mode(guild.id)
        if current_mode == "mode_default":
            await set_evil_mode(guild.id, False)
            return True, "Evil Mode is disabled in default mode."

        if state is None:
            current = await get_evil_mode(guild.id)
            status = "ENABLED" if current else "DISABLED"
            return True, f"Evil Mode is currently **{status}**."

        await set_persona_evil_mode(
            bot=self.bot,
            guild_id=guild.id,
            user_id=actor.id,
            enabled=state,
        )
        if state:
            return True, "Evil Mode ENABLED. Responses will now use uncensored models (Venice/Hermes)."
        return True, "Evil Mode DISABLED. Returning to standard safety protocols."

    def _is_mention_only(self, message: discord.Message) -> bool:
        """Return True when the message only mentions the bot."""
        content = message.content
        content = content.replace(f"<@{self.bot.user.id}>", "")
        content = content.replace(f"<@!{self.bot.user.id}>", "")
        return content.strip() == ""

    def _format_ordinal(self, number: int) -> str:
        if number <= 0:
            return str(number)
        if 10 <= (number % 100) <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
        return f"{number}{suffix}"

    def _apply_welcome_template(
        self,
        template: str,
        member: discord.Member,
        member_count: int,
    ) -> str:
        ordinal = self._format_ordinal(member_count)
        replacements = {
            "@user": member.mention,
            "{member}": member.mention,
            "{member_name}": member.display_name,
            "{member_count}": str(member_count),
            "{member_ordinal}": ordinal,
            "{guild}": member.guild.name,
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def _ensure_join_count_sentence(self, text: str, member_count: int) -> str:
        ordinal = self._format_ordinal(member_count)
        if str(member_count) in text or ordinal in text:
            return text
        sentence = f"You are the {ordinal} member to join~"
        if text.endswith((".", "!", "?", "~")):
            return f"{text} {sentence}"
        return f"{text}. {sentence}"

    async def _build_petpet_bytes(self, member: discord.Member) -> bytes | None:
        avatar = getattr(member, "display_avatar", None)
        if avatar is None or not hasattr(avatar, "read"):
            return None
        try:
            avatar_bytes = await avatar.read()
        except Exception as exc:
            logger.warning("Failed to fetch welcome avatar for %s: %s", member, exc)
            return None
        if not avatar_bytes:
            return None
        try:
            return make_petpet(avatar_bytes)
        except Exception as exc:
            logger.warning("Failed to build petpet for %s: %s", member, exc)
            return None
    
    @commands.command(name="evil", aliases=["uncensored"])
    @commands.has_permissions(manage_guild=True)
    async def toggle_evil_mode(self, ctx: commands.Context, state: str = None):
        """
        Toggle 'Evil' (Uncensored) mode using OpenRouter models.
        
        Usage: !evil [on/off]
        """
        current_mode = await get_server_mode(ctx.guild.id)
        if current_mode == "mode_default":
            await set_evil_mode(ctx.guild.id, False)
            await ctx.send(f"Evil Mode is disabled in default mode. {MANAGE_GUIDANCE}")
            return

        if not state:
            current = await get_evil_mode(ctx.guild.id)
            status = "ENABLED" if current else "DISABLED"
            await ctx.send(f"😈 Evil Mode is currently **{status}**. {MANAGE_GUIDANCE}")
            return

        state = state.lower()
        if state in ["on", "enable", "true", "yes"]:
            await set_persona_evil_mode(
                bot=self.bot,
                guild_id=ctx.guild.id,
                user_id=ctx.author.id,
                enabled=True,
            )
            await ctx.send(f"😈 Evil Mode ENABLED. Responses will now use uncensored models (Venice/Hermes). {MANAGE_GUIDANCE}")
        elif state in ["off", "disable", "false", "no"]:
            await set_persona_evil_mode(
                bot=self.bot,
                guild_id=ctx.guild.id,
                user_id=ctx.author.id,
                enabled=False,
            )
            await ctx.send(f"😇 Evil Mode DISABLED. Returning to standard safety protocols. {MANAGE_GUIDANCE}")
        else:
            await ctx.send(f"Usage: `!evil on` or `!evil off` {MANAGE_GUIDANCE}")

    @app_commands.command(name="evil", description="Toggle uncensored (evil) mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(state="on/off")
    async def toggle_evil_mode_slash(self, interaction: discord.Interaction, state: str = None):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        normalized_state = None
        if state:
            lowered = state.lower().strip()
            if lowered in ["on", "enable", "true", "yes"]:
                normalized_state = True
            elif lowered in ["off", "disable", "false", "no"]:
                normalized_state = False
            else:
                await interaction.response.send_message(
                    "Usage: `/evil on` or `/evil off`\nUse `/persona manage` for the primary persona and presentation panel.",
                    ephemeral=True,
                )
                return

        _, message = await self.apply_evil_mode_change(
            interaction.guild,
            interaction.user,
            normalized_state,
        )
        await interaction.response.send_message(
            f"{message}\nUse `/persona manage` for the primary persona and presentation panel.",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Handle auto-role assignment and optional AI welcome message.
        """
        guild_id = member.guild.id
        mode = await get_server_mode(guild_id)

        # Auto-role
        try:
            autorole_config = await get_autorole_config(guild_id)
            if autorole_config.get("autorole_enabled") and autorole_config.get("autorole_id"):
                role = member.guild.get_role(autorole_config["autorole_id"])
                if role:
                    await member.add_roles(role, reason="Auto-role assignment")
        except discord.Forbidden:
            logger.warning("Missing permissions to assign autorole in %s", member.guild.name)
        except Exception as exc:
            logger.error("Auto-role assignment failed in %s: %s", member.guild.name, exc, exc_info=True)

        # AI Welcome
        welcome_config = await get_welcome_config(guild_id)
        welcome_enabled = welcome_config.get("welcome_enabled")
        channel_id = welcome_config.get("welcome_channel_id") if welcome_enabled else None
        channel = member.guild.get_channel(channel_id) if channel_id else None
        template = welcome_config.get("welcome_message_template") if welcome_enabled else None
        member_count = int(getattr(member.guild, "member_count", 0) or 0)
        petpet_bytes: bytes | None = None

        if channel:
            if template:
                welcome_text = self._apply_welcome_template(template, member, member_count)
            else:
                prompt = (
                    "Write one short, cute, friendly welcome sentence for a new Discord member. "
                    f"Server: {member.guild.name}. User: {member.display_name}. "
                    f"Persona mode: {mode}. Keep it playful, SFW, and unique."
                )

                fallback_messages = {
                    "mode_default": f"Welcome to the server, {member.mention}.",
                    "mode_femboy": f"Welcome to the server, {member.mention}! I hope we can be great friends~",
                    "mode_tsundere": f"Oh, {member.mention} joined... I guess you can stay. ...Welcome.",
                    "mode_oneesan": f"Ara ara~ Welcome, {member.mention}! Make yourself at home, my dear~",
                }

                try:
                    welcome_text, _ = await generate_guild_gemini_text(guild_id, prompt)
                    welcome_text = welcome_text.strip()
                except GuildConfigError:
                    welcome_text = ""
                except Exception as exc:
                    logger.warning("AI welcome failed for %s: %s", member.guild.name, exc)
                    welcome_text = ""

                if not welcome_text:
                    welcome_text = fallback_messages.get(mode, fallback_messages["mode_default"])
                else:
                    if member.mention not in welcome_text:
                        welcome_text = f"{welcome_text} {member.mention}"

            if member_count > 0:
                welcome_text = self._ensure_join_count_sentence(welcome_text, member_count)

            try:
                send_kwargs = {
                    "allowed_mentions": discord.AllowedMentions(users=True, roles=False, everyone=False),
                }
                petpet_bytes = await self._build_petpet_bytes(member)
                if petpet_bytes:
                    send_kwargs["file"] = discord.File(BytesIO(petpet_bytes), filename="petpet.gif")
                await channel.send(
                    welcome_text,
                    **send_kwargs,
                )
            except discord.Forbidden:
                logger.warning("Missing permissions to send welcome in %s", member.guild.name)

        # DM Welcome (Preset message from server staff)
        dm_enabled = await get_dm_welcome_enabled(guild_id)
        dm_petpet_enabled = await get_dm_welcome_petpet_enabled(guild_id)
        dm_text = await get_dm_welcome_message(guild_id)
        if dm_enabled and dm_text:
            try:
                send_kwargs = {}
                if dm_petpet_enabled:
                    if petpet_bytes is None:
                        petpet_bytes = await self._build_petpet_bytes(member)
                    if petpet_bytes:
                        send_kwargs["file"] = discord.File(BytesIO(petpet_bytes), filename="petpet.gif")
                await member.send(dm_text, **send_kwargs)
            except discord.Forbidden:
                logger.warning("Could not DM %s (DMs closed).", member)
            except Exception as exc:
                logger.warning("Failed to DM welcome message to %s: %s", member, exc)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Respond to mention-only messages with a quick reaction.
        """
        if message.author.bot:
            return
        if not message.guild:
            return
        if self.bot.user not in message.mentions:
            return
        if message.attachments:
            return
        if not self._is_mention_only(message):
            return

        mode = await get_server_mode(message.guild.id)
        profile = get_mode_profile(mode)
        responses = profile.mention_reactions or ()
        if not responses:
            return
        response_text = random.choice(responses)
        await message.reply(response_text, mention_author=False)


async def setup(bot: commands.Bot):
    """Load the Social cog."""
    await bot.add_cog(Social(bot))
