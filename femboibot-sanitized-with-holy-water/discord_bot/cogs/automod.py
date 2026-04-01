from __future__ import annotations

import re
from collections import deque
from datetime import timedelta
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import (
    add_automod_rule,
    get_automod_rules,
    get_mod_log_channel_id,
    get_spam_config,
    get_staff_roles,
    get_url_safety_config,
    remove_automod_rule,
    set_spam_config,
)
from utils.logger import get_logger
from utils.url_safety import check_message_urls, describe_reason

logger = get_logger(__name__)


class Automod(commands.Cog):
    automod_group = app_commands.Group(name="automod", description="Automod rules")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._spam_buckets: dict[tuple[int, int], deque[float]] = {}

    def _keyword_match(self, keyword: str, content: str) -> bool:
        keyword = (keyword or "").strip().lower()
        if not keyword:
            return False
        if all(ch.isalnum() or ch == "_" for ch in keyword):
            pattern = rf"\b{re.escape(keyword)}\b"
            return re.search(pattern, content) is not None
        return keyword in content

    async def _is_staff(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
            return True
        if member.guild_permissions.manage_messages:
            return True
        staff_roles = await get_staff_roles(member.guild.id)
        if not staff_roles:
            return False
        staff_role_ids = {role_id for role_id, _ in staff_roles}
        return any(role.id in staff_role_ids for role in member.roles)

    async def _post_mod_log(
        self,
        guild: discord.Guild,
        action: str,
        target: discord.Member,
        keyword: str,
        duration_minutes: Optional[int] = None,
    ) -> None:
        channel_id = await get_mod_log_channel_id(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title="Automod Action",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="User", value=f"{target} ({target.id})", inline=True)
        embed.add_field(name="Keyword", value=keyword, inline=True)
        if duration_minutes:
            embed.add_field(name="Duration", value=f"{duration_minutes} minutes", inline=True)
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    async def _post_url_log(
        self,
        guild: discord.Guild,
        target: discord.Member,
        url: str,
        reason: str,
        action: str,
    ) -> None:
        channel_id = await get_mod_log_channel_id(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title="URL Safety",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="User", value=f"{target} ({target.id})", inline=True)
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="URL", value=url, inline=False)
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    async def _apply_punishment(
        self,
        message: discord.Message,
        action: str,
        keyword: str,
        duration_minutes: int,
    ) -> Optional[str]:
        member = message.author
        if not isinstance(member, discord.Member):
            return None

        if action == "timeout":
            minutes = max(1, int(duration_minutes or 0))
            until = discord.utils.utcnow() + timedelta(minutes=minutes)
            await member.timeout(until, reason=f"Automod: keyword '{keyword}'")
            return f"🚫 **{member.mention}** has been timed out for {minutes} minutes."
        if action == "kick":
            await member.kick(reason=f"Automod: keyword '{keyword}'")
            return f"🥾 **{member.mention}** has been kicked."
        if action == "ban":
            await member.ban(reason=f"Automod: keyword '{keyword}'")
            return f"🔨 **{member.mention}** has been banned."
        return f"⚠️ **{member.mention}**, that word is not allowed here."

    async def process_automod(self, message: discord.Message) -> bool:
        if not message.guild or message.author.bot:
            return False
        if message.webhook_id:
            return False
        if not isinstance(message.author, discord.Member):
            return False
        if await self._is_staff(message.author):
            return False

        if await self._check_spam(message):
            return True

        if await self._check_url_safety(message):
            return True

        rules = await get_automod_rules(message.guild.id)
        if not rules:
            return False

        content = (message.content or "").lower()
        if not content:
            return False

        rules_sorted = sorted(
            rules,
            key=lambda r: len(r.get("keyword") or ""),
            reverse=True,
        )

        for rule in rules_sorted:
            keyword = (rule.get("keyword") or "").strip().lower()
            if not keyword:
                continue
            if not self._keyword_match(keyword, content):
                continue

            action = (rule.get("punishment_type") or "delete_only").strip().lower()
            duration = int(rule.get("duration_minutes") or 0)

            try:
                await message.delete()
            except Exception:
                pass

            try:
                response = await self._apply_punishment(message, action, keyword, duration)
            except discord.Forbidden:
                logger.warning("Missing permissions to apply automod action in %s", message.guild.name)
                return True
            except Exception as exc:
                logger.error("Automod action failed: %s", exc, exc_info=True)
                return True

            if response:
                try:
                    await message.channel.send(response, delete_after=10)
                except discord.Forbidden:
                    pass

            try:
                await self._post_mod_log(
                    message.guild,
                    action,
                    message.author,
                    keyword,
                    duration_minutes=duration if action == "timeout" else None,
                )
            except Exception:
                pass

            return True

        return False

    async def _check_url_safety(self, message: discord.Message) -> bool:
        if not message.content:
            return False

        config = await get_url_safety_config(message.guild.id)
        if not config.get("url_safety_enabled"):
            return False

        matches = check_message_urls(
            message.content,
            config.get("url_allowlist"),
            config.get("url_blocklist"),
        )
        if not matches:
            return False

        action = (config.get("url_safety_action") or "warn").lower()
        first = matches[0]
        reason_text = describe_reason(first.reason)

        if action == "delete":
            try:
                await message.delete()
            except Exception:
                pass

        warning = (
            f"⚠️ **{message.author.mention}**, that link looks suspicious "
            f"({reason_text}). Please be careful."
        )
        try:
            await message.channel.send(warning, delete_after=15)
        except discord.Forbidden:
            pass

        try:
            await self._post_url_log(
                message.guild,
                message.author,
                first.url,
                reason_text,
                action,
            )
        except Exception:
            pass

        return True

    async def _check_spam(self, message: discord.Message) -> bool:
        config = await get_spam_config(message.guild.id)
        if not config.get("spam_timeout_enabled"):
            return False

        max_messages = int(config.get("spam_max_messages") or 0)
        window_seconds = int(config.get("spam_window_seconds") or 0)
        timeout_minutes = int(config.get("spam_timeout_minutes") or 0)

        if max_messages <= 0 or window_seconds <= 0 or timeout_minutes <= 0:
            return False

        key = (message.guild.id, message.author.id)
        bucket = self._spam_buckets.setdefault(key, deque())
        now = time.time()
        cutoff = now - window_seconds
        bucket.append(now)
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) <= max_messages:
            return False

        bucket.clear()

        try:
            until = discord.utils.utcnow() + timedelta(minutes=timeout_minutes)
            await message.author.timeout(until, reason="Automod: spam threshold exceeded")
        except discord.Forbidden:
            logger.warning("Missing permissions to timeout spammer in %s", message.guild.name)
            return True
        except Exception as exc:
            logger.error("Spam timeout failed: %s", exc, exc_info=True)
            return True

        try:
            await message.channel.send(
                f"🚫 **{message.author.mention}** has been timed out for spam "
                f"({max_messages} msgs / {window_seconds}s).",
                delete_after=10,
            )
        except discord.Forbidden:
            pass

        try:
            await self._post_mod_log(
                message.guild,
                "spam_timeout",
                message.author,
                f"{max_messages} msgs / {window_seconds}s",
                duration_minutes=timeout_minutes,
            )
        except Exception:
            pass

        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.process_automod(message)

    # =========================
    # Slash Commands
    # =========================

    @automod_group.command(name="add", description="Add or update an automod rule.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        keyword="Keyword to trigger",
        action="Punishment type",
        duration="Timeout duration in minutes (for timeout only)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="timeout", value="timeout"),
        app_commands.Choice(name="kick", value="kick"),
        app_commands.Choice(name="ban", value="ban"),
        app_commands.Choice(name="delete_only", value="delete_only"),
    ])
    async def automod_add(
        self,
        interaction: discord.Interaction,
        keyword: str,
        action: app_commands.Choice[str],
        duration: Optional[int] = 0,
    ):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        word = (keyword or "").strip().lower()
        if not word:
            await interaction.response.send_message("Keyword cannot be empty.", ephemeral=True)
            return
        dur = int(duration or 0)
        if action.value == "timeout" and dur <= 0:
            dur = 10
        await add_automod_rule(interaction.guild.id, word, action.value, dur)
        await interaction.response.send_message(
            f"Automod rule set: `{word}` -> **{action.value}**"
            + (f" ({dur} min)" if action.value == "timeout" else ""),
            ephemeral=True,
        )

    @automod_group.command(name="remove", description="Remove an automod rule.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(keyword="Keyword to remove")
    async def automod_remove(self, interaction: discord.Interaction, keyword: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        removed = await remove_automod_rule(interaction.guild.id, keyword)
        if removed:
            await interaction.response.send_message(f"Removed rule for `{keyword}`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"No rule found for `{keyword}`.", ephemeral=True)

    @automod_group.command(name="list", description="List automod rules.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_list(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        rules = await get_automod_rules(interaction.guild.id)
        if not rules:
            await interaction.response.send_message("No automod rules configured.", ephemeral=True)
            return
        lines = []
        for rule in rules:
            keyword = rule.get("keyword")
            action = rule.get("punishment_type")
            duration = rule.get("duration_minutes") or 0
            if action == "timeout":
                lines.append(f"- `{keyword}` -> **{action}** ({duration} min)")
            else:
                lines.append(f"- `{keyword}` -> **{action}**")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @automod_group.command(name="spam", description="Configure automod spam timeout.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        max_messages="Max messages allowed in the window",
        window_seconds="Time window in seconds",
        timeout_minutes="Timeout duration in minutes",
        state="on/off (optional)",
    )
    async def automod_spam(
        self,
        interaction: discord.Interaction,
        max_messages: Optional[int] = None,
        window_seconds: Optional[int] = None,
        timeout_minutes: Optional[int] = None,
        state: Optional[str] = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        if max_messages is None and window_seconds is None and timeout_minutes is None and not state:
            config = await get_spam_config(interaction.guild.id)
            enabled = config.get("spam_timeout_enabled")
            await interaction.response.send_message(
                "Spam automod is **{status}**. Threshold: {max} msgs / {window}s. Timeout: {minutes} min.".format(
                    status="ENABLED" if enabled else "DISABLED",
                    max=config.get("spam_max_messages"),
                    window=config.get("spam_window_seconds"),
                    minutes=config.get("spam_timeout_minutes"),
                ),
                ephemeral=True,
            )
            return

        updates = {}
        if max_messages is not None:
            if max_messages < 2:
                await interaction.response.send_message("max_messages must be at least 2.", ephemeral=True)
                return
            updates["spam_max_messages"] = int(max_messages)
        if window_seconds is not None:
            if window_seconds < 2:
                await interaction.response.send_message("window_seconds must be at least 2.", ephemeral=True)
                return
            updates["spam_window_seconds"] = int(window_seconds)
        if timeout_minutes is not None:
            if timeout_minutes < 1:
                await interaction.response.send_message("timeout_minutes must be at least 1.", ephemeral=True)
                return
            timeout_minutes = max(1, min(int(timeout_minutes), 40320))
            updates["spam_timeout_minutes"] = timeout_minutes

        if state:
            state_value = state.lower().strip()
            if state_value in {"on", "enable", "true", "yes"}:
                updates["spam_timeout_enabled"] = 1
            elif state_value in {"off", "disable", "false", "no"}:
                updates["spam_timeout_enabled"] = 0
            else:
                await interaction.response.send_message("state must be on/off.", ephemeral=True)
                return
        elif updates:
            updates["spam_timeout_enabled"] = 1

        await set_spam_config(interaction.guild.id, updates)
        config = await get_spam_config(interaction.guild.id)
        enabled = config.get("spam_timeout_enabled")
        await interaction.response.send_message(
            "Spam automod is **{status}**. Threshold: {max} msgs / {window}s. Timeout: {minutes} min.".format(
                status="ENABLED" if enabled else "DISABLED",
                max=config.get("spam_max_messages"),
                window=config.get("spam_window_seconds"),
                minutes=config.get("spam_timeout_minutes"),
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Automod(bot))
