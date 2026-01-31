import json
from pathlib import Path
from typing import Any, Dict, Optional

import discord

from utils.db_handler import DATA_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class PersonaManager:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.persona_path = DATA_DIR / "personas.json"
        self._personas_mtime: Optional[float] = None
        self.personas = self._load_personas()
        self.webhook_cache: Dict[int, discord.Webhook] = {}

    def _load_personas(self) -> Dict[str, Dict[str, Any]]:
        try:
            if not self.persona_path.exists():
                logger.warning("personas.json not found at %s", self.persona_path)
                return {}
            self._personas_mtime = self.persona_path.stat().st_mtime
            with self.persona_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to load personas.json: %s", exc)
            return {}

    def _reload_if_changed(self) -> None:
        try:
            if not self.persona_path.exists():
                return
            mtime = self.persona_path.stat().st_mtime
            if self._personas_mtime is None or mtime > self._personas_mtime:
                self.personas = self._load_personas()
        except Exception:
            pass

    async def get_webhook(self, channel: discord.abc.GuildChannel) -> Optional[discord.Webhook]:
        if channel.id in self.webhook_cache:
            return self.webhook_cache[channel.id]

        try:
            webhooks = await channel.webhooks()
        except discord.Forbidden:
            return None
        except discord.HTTPException:
            return None

        webhook = discord.utils.get(webhooks, user=self.bot.user)
        if webhook is None:
            try:
                webhook = await channel.create_webhook(name="Femmy-Proxy")
            except (discord.Forbidden, discord.HTTPException):
                return None

        self.webhook_cache[channel.id] = webhook
        return webhook

    def _resolve_persona(self, mode_id: str, evil_mode: bool) -> Dict[str, Optional[str]]:
        self._reload_if_changed()
        persona = {}
        if evil_mode:
            persona = (
                self.personas.get(f"{mode_id}_evil")
                or self.personas.get("default_evil")
                or {}
            )
        if not persona:
            persona = self.personas.get(mode_id) or self.personas.get("default") or {}
        if not persona:
            name = self.bot.user.display_name if self.bot.user else "Femmy"
            return {"name": name, "avatar_url": None}
        return {
            "name": persona.get("name") or (self.bot.user.display_name if self.bot.user else "Femmy"),
            "avatar_url": persona.get("avatar_url"),
        }

    async def send_as_mode(
        self,
        channel: discord.abc.Messageable,
        content: str,
        mode_id: str,
        evil_mode: bool = False,
        **kwargs,
    ) -> Optional[discord.Message]:
        if mode_id == "mode_default":
            return await channel.send(content, **kwargs)

        if not isinstance(channel, discord.abc.GuildChannel) and not isinstance(channel, discord.Thread):
            return await channel.send(content, **kwargs)

        persona = self._resolve_persona(mode_id, evil_mode)

        if isinstance(channel, discord.Thread):
            webhook_channel = channel.parent
            thread = channel
        else:
            webhook_channel = channel
            thread = None

        webhook = None
        if webhook_channel:
            webhook = await self.get_webhook(webhook_channel)

        if webhook:
            send_kwargs = dict(kwargs)
            send_kwargs.setdefault("wait", True)
            send_kwargs.setdefault("allowed_mentions", discord.AllowedMentions.none())
            if thread:
                send_kwargs["thread"] = thread
            try:
                return await webhook.send(
                    content=content,
                    username=persona.get("name"),
                    avatar_url=persona.get("avatar_url"),
                    **send_kwargs,
                )
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                if webhook_channel and webhook_channel.id in self.webhook_cache:
                    self.webhook_cache.pop(webhook_channel.id, None)

        return await channel.send(content, **kwargs)
