"""
Trait parsing and seeding for custom affection logic.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from modes import get_mode_profile
from utils.db_handler import get_persona_traits, sanitize_persona_name, upsert_persona_traits

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

DEFAULT_LIKE_POINTS = 10
DEFAULT_DISLIKE_POINTS = -5

_TRAIT_LINE_RE = re.compile(r"^\s*\+(likes|dislikes)\b(.*)$", re.IGNORECASE)


def _parse_points(token: str) -> Optional[int]:
    value = token.strip()
    if not value:
        return None
    if value.startswith("+") or value.startswith("-"):
        value = value[1:] if value[0] == "+" else value
    try:
        return int(value)
    except ValueError:
        return None


def _split_keywords(value: str) -> List[str]:
    if not value:
        return []
    parts: List[str] = []
    for chunk in value.split(","):
        for sub in chunk.split("|"):
            item = sub.strip()
            if item:
                parts.append(item)
    return parts


def _parse_meta(meta: str, default_points: int, default_one_time: bool) -> Dict[str, Any]:
    points = default_points
    one_time = default_one_time
    keywords: List[str] = []

    lowered_meta = meta.lower()
    if "keywords:" in lowered_meta:
        idx = lowered_meta.index("keywords:")
        keyword_blob = meta[idx + len("keywords:"):]
        keywords.extend(_split_keywords(keyword_blob))
        meta = meta[:idx].strip()

    for raw in meta.split(","):
        token = raw.strip()
        if not token:
            continue
        lowered = token.lower()

        if lowered.startswith("points"):
            if ":" in token:
                parsed = _parse_points(token.split(":", 1)[1])
                if parsed is not None:
                    points = parsed
            continue

        if lowered in {"one_time", "one-time", "onetime", "once"}:
            one_time = True
            continue

        if lowered in {"repeatable", "repeated", "always", "multi"}:
            one_time = False
            continue

        parsed = _parse_points(token)
        if parsed is not None:
            points = parsed

    return {
        "points_value": points,
        "one_time": one_time,
        "trigger_terms": keywords,
    }


def parse_persona_traits(prompt: str) -> List[Dict[str, Any]]:
    """Extract trait definitions from prompt text."""
    traits: Dict[str, Dict[str, Any]] = {}
    for line in (prompt or "").splitlines():
        match = _TRAIT_LINE_RE.match(line)
        if not match:
            continue

        sentiment = match.group(1).lower()
        rest = match.group(2).strip()
        if rest.startswith(":") or rest.startswith("-"):
            rest = rest[1:].strip()

        meta = ""
        trait_text = rest
        if rest.endswith(")") and "(" in rest:
            idx = rest.rfind("(")
            meta = rest[idx + 1:-1]
            trait_text = rest[:idx].strip()

        if not trait_text:
            continue

        if sentiment == "likes":
            default_points = DEFAULT_LIKE_POINTS
            default_one_time = True
        else:
            default_points = DEFAULT_DISLIKE_POINTS
            default_one_time = False

        parsed = _parse_meta(meta, default_points, default_one_time)
        trait_key = sanitize_persona_name(trait_text)
        if not trait_key:
            continue

        traits[trait_key] = {
            "trait_key": trait_key,
            "trait_text": trait_text,
            "trigger_terms": parsed["trigger_terms"],
            "points_value": parsed["points_value"],
            "one_time": parsed["one_time"],
        }

    return list(traits.values())


def extract_persona_traits(normal_prompt: str, evil_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extract traits from normal and evil prompts."""
    combined: Dict[str, Dict[str, Any]] = {}
    for prompt_text in [normal_prompt or "", evil_prompt or ""]:
        for trait in parse_persona_traits(prompt_text):
            combined[trait["trait_key"]] = trait
    return list(combined.values())


def _load_prompt_text(filename: str) -> str:
    if not filename:
        return ""
    path = PROMPTS_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


async def get_or_seed_mode_traits(guild_id: int, mode_key: str) -> List[Dict[str, Any]]:
    """
    Fetch traits for a mode key; for built-ins, seed from prompt files if missing.
    """
    traits = await get_persona_traits(guild_id, mode_key)
    if traits or mode_key.startswith("custom_"):
        return traits

    profile = get_mode_profile(mode_key)
    normal_prompt = _load_prompt_text(profile.prompt_file)
    evil_prompt = _load_prompt_text(profile.evil_prompt_file)
    parsed = extract_persona_traits(normal_prompt, evil_prompt or None)
    if parsed:
        await upsert_persona_traits(guild_id, mode_key, parsed)
        return parsed
    return traits
