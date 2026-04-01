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
_DANGLING_SHORTCODE_PATTERN = re.compile(r"(?<!<a)(?<!<):([A-Za-z0-9_]+)(?=$|[\s.,!?;)\]\}])")
_SHORTCODE_IN_TEXT_PATTERN = re.compile(r"(?<!<a)(?<!<):[A-Za-z0-9_]+:")


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
            "Use ONLY shortcode format `:name:` for custom emojis.",
            "Never output raw Discord tags like `<:name:id>` or `<a:name:id>`.",
            "You may use these custom emojis when context and tone match:",
            "",
        ]

        for name, info in available.items():
            lines.append(f"- :{name}: -> {info['usage']}")

        if self._validated_general:
            general_shortcodes = []
            for token in self._validated_general:
                match = _EMOJI_NAME_PATTERN.match(token)
                if match:
                    general_shortcodes.append(f":{match.group(1)}:")
            lines.append("")
            lines.append("General emojis (no restrictions):")
            lines.append(" ".join(general_shortcodes))

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
        combined = f"{user_lower} {response_lower}"

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

        greeting_cues = ["hi", "hello", "hey", "yo", "sup", "good morning", "good night"]
        positive_cues = ["thanks", "thank you", "nice", "good", "great", "love", "cute"]
        excitement_cues = ["yay", "woo", "let's go", "excited", "hype", "omg", "yesss"]
        affection_cues = ["love you", "love u", "my love", "darling", "sweetheart", "kiss"]
        shock_cues = ["wtf", "what the", "no way", "holy", "shocking", "what?!", "bruh"]
        sarcasm_cues = ["dramatic", "sarcastic", "sarcasm", "sure...", "yeah right", "as if"]
        hostile_cues = ["rude", "stupid", "idiot", "trash", "hate you", "shut up", "dumb"]
        annoyed_cues = ["annoy", "annoying", "angry", "mad", "grr", "frustrated"]
        flirty_cues = ["horny", "sexy", "naughty", "kiss", "bed", "make out"]
        ban_cues = ["ban", "banned", "banning"]

        is_hostile = _has_any(combined, hostile_cues)
        is_annoyed = _has_any(combined, annoyed_cues)
        is_sarcastic = _has_any(combined, sarcasm_cues)
        is_shocked = _has_any(combined, shock_cues)
        is_affectionate = _has_any(combined, affection_cues)
        is_excited = _has_any(combined, excitement_cues)
        is_positive = _has_any(combined, positive_cues)
        is_greeting = _has_any(user_lower, greeting_cues)
        is_flirty = _has_any(combined, flirty_cues)

        if _has_any(combined, ban_cues):
            _add("ban")

        if is_hostile:
            _add("thisisfinefrog")
        if is_annoyed:
            _add("pout")
        if is_sarcastic and not is_hostile:
            _add("mikucinema")
        if is_shocked and not is_hostile:
            _add("what")

        if affection >= 800 and is_affectionate and not (is_hostile or is_annoyed):
            _add("inlovehearts")

        if affection >= 500 and is_excited and not (is_hostile or is_annoyed):
            _add("twin_spin")

        if evil_mode and is_flirty and not (is_hostile or is_annoyed):
            _add("horny")
            _add("aah_openingmouth_horny")

        mentioned_name = _has_any(user_lower, ["femmy", "yumi"])
        positive_mention = is_greeting or is_excited or is_affectionate or is_positive
        if mentioned_name and positive_mention and not is_hostile:
            _add("tada")
        if "femmy" in user_lower and positive_mention and not (is_hostile or is_annoyed):
            _add("sneakpeekcat")

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
        existing_shortcodes = _SHORTCODE_IN_TEXT_PATTERN.findall(response_text)
        remaining = max(0, max_emojis - len(existing) - len(existing_shortcodes))
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

        text = _SHORTCODE_PATTERN.sub(_replace, text)
        return _DANGLING_SHORTCODE_PATTERN.sub(_replace, text)
