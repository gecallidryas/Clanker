import json
import re
from pathlib import Path
from typing import Dict, List

from utils.expression_cache import get_expression_service
from utils.app_emojis import format_custom_emoji, get_application_emojis
from utils.logger import get_logger

logger = get_logger(__name__)

_EMOJI_TOKEN_PATTERN = re.compile(r"<a?:[A-Za-z0-9_]+:(\d+)>")
_EMOJI_NAME_PATTERN = re.compile(r"<a?:([A-Za-z0-9_]+):\d+>")
_EMOJI_IN_TEXT_PATTERN = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
_SHORTCODE_PATTERN = re.compile(r"(?<!<a)(?<!<):([A-Za-z0-9_]+):")
_DANGLING_SHORTCODE_PATTERN = re.compile(r"(?<!<a)(?<!<):([A-Za-z0-9_]+)(?=$|[\s.,!?;)\]\}])")
_SHORTCODE_IN_TEXT_PATTERN = re.compile(r"(?<!<a)(?<!<):[A-Za-z0-9_]+:")
_WORD_PATTERN = re.compile(r"[a-z0-9']+")
_CAMEL_CASE_PATTERN = re.compile(r"([a-z])([A-Z])")

_SIGNAL_KEYWORDS = {
    "celebratory": ("celebrate", "celebrating", "success", "win", "won", "victory", "hype", "excited", "yay", "woo", "lets go", "did it", "finally"),
    "positive": ("good", "great", "nice", "adorable", "cute", "lovely", "sweet", "happy", "glad", "fun"),
    "affectionate": ("love", "loving", "heart", "hearts", "darling", "sweetheart", "affectionate", "warm", "kiss"),
    "playful": ("playful", "cute", "cat", "hehe", "lol", "lmao", "goofy", "silly", "peek", "adorable"),
    "teasing": ("teasing", "tease", "smug", "sassy", "cheeky", "brat"),
    "annoyed": ("annoyed", "annoying", "rude", "hostile", "angry", "mad", "watch your tone", "stop", "enough", "pout"),
    "confused": ("confused", "huh", "what", "wait", "erm", "uh", "hmm", "excuse me"),
    "shocked": ("shocked", "surprised", "surprise", "no way", "omg", "wtf", "wild", "insane"),
    "flirty": ("flirty", "horny", "sexy", "kiss", "make out", "bed", "suggestive"),
    "sad": ("sad", "cry", "crying", "upset", "lonely", "sorry", "hurt"),
    "supportive": ("support", "supportive", "proud", "you got this", "its okay", "it's okay", "there for you", "take care", "comfort"),
    "serious": ("setting", "settings", "channel", "role", "threshold", "policy", "admin", "configure", "configured", "updated", "database", "command", "rule", "moderation"),
}

_DEFAULT_SIGNAL_WEIGHTS = {
    "celebratory": 0.0,
    "positive": 0.0,
    "affectionate": 0.0,
    "playful": 0.0,
    "teasing": 0.0,
    "annoyed": 0.0,
    "confused": 0.0,
    "shocked": 0.0,
    "flirty": 0.0,
    "sad": 0.0,
    "supportive": 0.0,
    "serious": 0.0,
}


class EmojiManager:
    def __init__(self, bot):
        self.bot = bot
        self.config = self._load_config()
        self._validated_emojis: Dict[str, str] = {}
        self._validated_general: List[str] = []
        self._validated_snapshot_version: int = 0

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

        service = get_expression_service(self.bot)
        if service is not None:
            snapshot = await service.get_application_snapshot()
            emojis = snapshot.of_kind("emoji")
            self._validated_snapshot_version = snapshot.snapshot_version
        else:
            emojis = await get_application_emojis(self.bot)
            self._validated_snapshot_version = 0
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

    def _normalize_words(self, text: str) -> list[str]:
        if not text:
            return []
        compact = _CAMEL_CASE_PATTERN.sub(r"\1 \2", text.replace("_", " ").replace("-", " "))
        return _WORD_PATTERN.findall(compact.lower())

    def _signal_weights_for_text(self, text: str, *, weight: float = 1.0) -> Dict[str, float]:
        lowered = (text or "").lower()
        weights = dict(_DEFAULT_SIGNAL_WEIGHTS)

        for signal, keywords in _SIGNAL_KEYWORDS.items():
            for keyword in keywords:
                if " " in keyword:
                    if keyword in lowered:
                        weights[signal] += weight
                else:
                    if re.search(r"\b" + re.escape(keyword) + r"\b", lowered):
                        weights[signal] += weight

        exclamations = lowered.count("!")
        questions = lowered.count("?")
        if exclamations:
            weights["celebratory"] += min(exclamations, 2) * 0.35 * weight
            weights["playful"] += min(exclamations, 2) * 0.2 * weight
        if questions >= 2:
            weights["confused"] += 0.8 * weight
            weights["shocked"] += 0.4 * weight

        return weights

    def _merge_signal_weights(self, *sets: Dict[str, float]) -> Dict[str, float]:
        merged = dict(_DEFAULT_SIGNAL_WEIGHTS)
        for signal_set in sets:
            for signal, value in signal_set.items():
                merged[signal] = merged.get(signal, 0.0) + value
        return merged

    def _infer_candidate_signals(self, name: str, usage: str) -> Dict[str, float]:
        basis = " ".join(part for part in [name, usage] if part).strip()
        weights = self._signal_weights_for_text(basis, weight=1.0)

        words = self._normalize_words(name)
        for word in words:
            if word in {"cat", "cute", "peek"}:
                weights["playful"] += 0.6
                weights["positive"] += 0.3
            if word in {"smirk", "smug"}:
                weights["teasing"] += 0.5
            if word in {"annoyed", "pout"}:
                weights["annoyed"] += 0.7
            if word in {"heart", "love", "kiss"}:
                weights["affectionate"] += 0.7

        return weights

    def _build_context_weights(self, response_text: str, user_text: str) -> Dict[str, float]:
        response_weights = self._signal_weights_for_text(response_text, weight=1.1)
        user_weights = self._signal_weights_for_text(user_text, weight=0.8)
        merged = self._merge_signal_weights(response_weights, user_weights)

        lowered_user = (user_text or "").lower()
        lowered_response = (response_text or "").lower()
        if re.search(r"\b(femmy|yumi)\b", lowered_user) and re.search(r"\b(cute|adorable|hehe|lol|silly)\b", lowered_response):
            merged["playful"] += 1.1
            merged["positive"] += 0.5

        return merged

    def _iter_contextual_candidates(
        self,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False,
    ) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        available = self.get_available_emojis(mode, affection, evil_mode)

        for name, info in available.items():
            token = info.get("emoji", "")
            usage = info.get("usage", "")
            if not token:
                continue
            candidates.append(
                {
                    "name": name,
                    "token": token,
                    "usage": usage,
                    "signals": self._infer_candidate_signals(name, usage),
                }
            )

        for token in self._validated_general:
            match = _EMOJI_NAME_PATTERN.match(token)
            if not match:
                continue
            name = match.group(1)
            candidates.append(
                {
                    "name": name,
                    "token": token,
                    "usage": name,
                    "signals": self._infer_candidate_signals(name, name),
                }
            )

        return candidates

    def _score_candidate(
        self,
        candidate: dict[str, object],
        context_weights: Dict[str, float],
    ) -> float:
        candidate_weights = candidate.get("signals", {})
        if not isinstance(candidate_weights, dict):
            return 0.0

        score = 0.0
        for signal, value in candidate_weights.items():
            score += context_weights.get(signal, 0.0) * float(value)

        if context_weights.get("serious", 0.0) >= 1.5 and context_weights.get("celebratory", 0.0) < 1.0:
            score -= 1.5
        if context_weights.get("annoyed", 0.0) >= 1.0 and candidate_weights.get("positive", 0.0) >= 0.8:
            score -= 1.0
        if context_weights.get("positive", 0.0) >= 1.0 and candidate_weights.get("annoyed", 0.0) >= 0.8:
            score -= 0.8

        return score

    def pick_contextual_emoji(
        self,
        response_text: str,
        user_text: str,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False,
    ) -> str:
        if not response_text:
            return ""

        context_weights = self._build_context_weights(response_text, user_text)
        expressive_weight = (
            context_weights.get("celebratory", 0.0)
            + context_weights.get("positive", 0.0)
            + context_weights.get("affectionate", 0.0)
            + context_weights.get("playful", 0.0)
            + context_weights.get("teasing", 0.0)
            + context_weights.get("annoyed", 0.0)
            + context_weights.get("confused", 0.0)
            + context_weights.get("shocked", 0.0)
            + context_weights.get("flirty", 0.0)
            + context_weights.get("sad", 0.0)
            + context_weights.get("supportive", 0.0)
        )
        if context_weights.get("serious", 0.0) >= 1.5 and expressive_weight < 1.8:
            return ""

        candidates = self._iter_contextual_candidates(mode, affection, evil_mode)
        if not candidates:
            return ""

        scored: list[tuple[float, str]] = []
        for candidate in candidates:
            token = str(candidate.get("token", "") or "")
            if not token:
                continue
            score = self._score_candidate(candidate, context_weights)
            scored.append((score, token))

        if not scored:
            return ""

        scored.sort(key=lambda item: item[0], reverse=True)
        top_score, top_token = scored[0]
        next_score = scored[1][0] if len(scored) > 1 else 0.0

        if top_score < 1.6:
            return ""
        if top_score - next_score < 0.2 and top_score < 2.3:
            return ""
        return top_token

    def strip_known_shortcodes(self, text: str) -> str:
        if not text:
            return text
        lookup = self._build_shortcode_lookup()
        if not lookup:
            return text

        known_names = {name.lower() for name in lookup.keys()}

        def _replace_shortcode(match: re.Match) -> str:
            name = match.group(1).lower()
            return "" if name in known_names else match.group(0)

        cleaned = _SHORTCODE_PATTERN.sub(_replace_shortcode, text)
        cleaned = _DANGLING_SHORTCODE_PATTERN.sub(_replace_shortcode, cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)
        return cleaned.strip()

    def append_contextual_emoji(
        self,
        response_text: str,
        user_text: str,
        mode: str,
        affection: int = 0,
        evil_mode: bool = False,
    ) -> str:
        if not response_text:
            return response_text

        if _EMOJI_IN_TEXT_PATTERN.search(response_text):
            return response_text

        token = self.pick_contextual_emoji(
            response_text=response_text,
            user_text=user_text,
            mode=mode,
            affection=affection,
            evil_mode=evil_mode,
        )
        if not token:
            return response_text
        return response_text.rstrip() + " " + token

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
