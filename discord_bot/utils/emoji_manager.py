import json
import re
from pathlib import Path
from typing import Dict, List

from utils.app_emojis import format_custom_emoji, get_application_emojis
from utils.logger import get_logger

logger = get_logger(__name__)

_EMOJI_TOKEN_PATTERN = re.compile(r"<a?:[A-Za-z0-9_]+:(\d+)>")


class EmojiManager:
    def __init__(self, bot):
        self.bot = bot
        self.config = self._load_config()
        self._validated_emojis: Dict[str, str] = {}
        self._validated_general: List[str] = []

    def _load_config(self) -> dict:
        config_path = Path(__file__).resolve().parent.parent / "data" / "emoji_config.json"
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            logger.warning("emoji_config.json not found, using empty config")
            return {"emojis": {}, "general_emojis": []}
        except json.JSONDecodeError as exc:
            logger.warning("emoji_config.json is invalid JSON: %s", exc)
            return {"emojis": {}, "general_emojis": []}

    async def validate_emojis(self) -> None:
        """Validate that configured emojis exist and cache them."""
        self._validated_emojis = {}
        self._validated_general = []

        emojis = await get_application_emojis(self.bot)
        emoji_by_id = {str(getattr(emoji, "id", "")): emoji for emoji in emojis if getattr(emoji, "id", None)}

        for name, data in self.config.get("emojis", {}).items():
            emoji_id = str(data.get("id", "")).strip()
            if not emoji_id:
                logger.warning("Emoji missing ID: %s", name)
                continue
            emoji = emoji_by_id.get(emoji_id)
            if emoji:
                token = format_custom_emoji(emoji)
                if token:
                    self._validated_emojis[name] = token
                    logger.debug("Validated emoji: %s", name)
            else:
                logger.warning("Emoji not found: %s (ID: %s)", name, emoji_id)

        for raw in self.config.get("general_emojis", []):
            match = _EMOJI_TOKEN_PATTERN.match(raw or "")
            if not match:
                continue
            emoji_id = match.group(1)
            emoji = emoji_by_id.get(emoji_id)
            if emoji:
                token = format_custom_emoji(emoji)
                if token:
                    self._validated_general.append(token)
            else:
                logger.warning("General emoji not found: %s", raw)

    def get_emoji(self, name: str) -> str:
        """Get emoji string by name."""
        return self._validated_emojis.get(name, "")

    def get_available_emojis(
        self,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False,
    ) -> Dict[str, Dict[str, str]]:
        """Get emojis available for current context with usage instructions."""
        available: Dict[str, Dict[str, str]] = {}

        for name, data in self.config.get("emojis", {}).items():
            if name not in self._validated_emojis:
                continue

            modes = data.get("modes", ["all"])
            if modes != ["all"] and mode not in modes:
                continue

            conditions = data.get("conditions", {})
            if conditions.get("min_affection", 0) > affection:
                continue
            if conditions.get("evil_mode") and not evil_mode:
                continue

            available[name] = {
                "emoji": self._validated_emojis[name],
                "usage": data.get("usage", "general use"),
            }

        return available

    def build_prompt_section(
        self,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False,
    ) -> str:
        """Build emoji usage instructions for AI prompt."""
        available = self.get_available_emojis(mode, affection, evil_mode)

        if not available and not self._validated_general:
            return ""

        lines = [
            "# Custom Emojis",
            "You may use these custom Discord emojis in your responses:",
            "",
        ]

        for info in available.values():
            lines.append(f"- {info['emoji']} -> {info['usage']}")

        if self._validated_general:
            lines.append("")
            lines.append("General emojis (no restrictions):")
            lines.append(" ".join(self._validated_general))

        lines.extend([
            "",
            "Use emojis sparingly (1-2 per message max). Match emoji to emotional context.",
        ])

        return "\n".join(lines)
