import json
import re
from pathlib import Path
from typing import Dict, List

from utils.app_emojis import format_custom_emoji, get_application_emojis
from utils.logger import get_logger

logger = get_logger(__name__)

_EMOJI_TOKEN_PATTERN = re.compile(r"<a?:[A-Za-z0-9_]+:(\d+)>")
_EMOJI_NAME_PATTERN = re.compile(r"<a?:([A-Za-z0-9_]+):\d+>")
_EMOJI_IN_TEXT_PATTERN = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
_SHORTCODE_PATTERN = re.compile(r"(?<!<a)(?<!<):([A-Za-z0-9_]+):")


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

    def select_trigger_emojis(
        self,
        response_text: str,
        user_text: str,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False,
        max_emojis: int = 2,
    ) -> List[str]:
        available = self.get_available_emojis(mode, affection, evil_mode)
        if not available or max_emojis <= 0:
            return []

        response_lower = (response_text or "").lower()
        user_lower = (user_text or "").lower()

        def _has_any(text: str, phrases: List[str]) -> bool:
            for phrase in phrases:
                if not phrase:
                    continue
                if " " in phrase:
                    if phrase in text:
                        return True
                else:
                    if re.search(r"\b" + re.escape(phrase) + r"\b", text):
                        return True
            return False

        selected: List[str] = []

        def _add(name: str) -> None:
            token = available.get(name, {}).get("emoji")
            if token and token not in selected:
                selected.append(token)

        if _has_any(user_lower, ["femmy", "yumi"]):
            _add("tada")
        if "femmy" in user_lower:
            _add("sneakpeekcat")

        if _has_any(user_lower, ["ban", "banned", "banning"]):
            _add("ban")

        if _has_any(user_lower, ["wtf", "what the", "no way", "holy", "shocking"]):
            _add("what")

        if _has_any(user_lower, ["dramatic", "sarcastic", "sarcasm", "sure...", "yeah right"]):
            _add("mikucinema")

        if _has_any(user_lower, ["rude", "stupid", "idiot", "trash", "hate you", "shut up"]):
            _add("thisisfinefrog")

        if _has_any(user_lower, ["annoy", "annoying", "angry", "mad", "grr"]):
            _add("pout")

        if affection >= 800 and _has_any(
            user_lower + " " + response_lower,
            ["love you", "love u", "my love", "darling", "sweetheart"],
        ):
            _add("inlovehearts")

        if affection >= 500 and _has_any(
            user_lower + " " + response_lower,
            ["yay", "woo", "let's go", "excited", "hype", "omg"],
        ):
            _add("twin_spin")

        if evil_mode and _has_any(
            user_lower + " " + response_lower,
            ["horny", "sexy", "naughty", "kiss", "bed"],
        ):
            _add("horny")
            _add("aah_openingmouth_horny")

        return selected[:max_emojis]

    def apply_trigger_emojis(
        self,
        response_text: str,
        user_text: str,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False,
        max_emojis: int = 2,
    ) -> str:
        if not response_text:
            return response_text

        existing = _EMOJI_IN_TEXT_PATTERN.findall(response_text)
        remaining = max(0, max_emojis - len(existing))
        if remaining <= 0:
            return response_text

        additions = self.select_trigger_emojis(
            response_text=response_text,
            user_text=user_text,
            mode=mode,
            affection=affection,
            evil_mode=evil_mode,
            max_emojis=remaining,
        )
        if not additions:
            return response_text

        return response_text.rstrip() + " " + " ".join(additions)

    def _build_shortcode_lookup(self) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for name, token in self._validated_emojis.items():
            if not token:
                continue
            lookup[name.lower()] = token
            match = _EMOJI_NAME_PATTERN.match(token)
            if match:
                lookup.setdefault(match.group(1).lower(), token)

        for token in self._validated_general:
            match = _EMOJI_NAME_PATTERN.match(token)
            if match:
                lookup.setdefault(match.group(1).lower(), token)

        return lookup

    def replace_shortcodes(self, text: str, strip_unknown: bool = True) -> str:
        if not text:
            return text
        lookup = self._build_shortcode_lookup()

        def _replace(match: re.Match) -> str:
            name = match.group(1).lower()
            token = lookup.get(name)
            if token:
                return token
            return name if strip_unknown else match.group(0)

        return _SHORTCODE_PATTERN.sub(_replace, text)
