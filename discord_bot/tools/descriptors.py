from __future__ import annotations

from tools.categories import normalize_tool_category
from tools.contracts import ToolSourceType


UNCATEGORIZED_TOOL_CATEGORY = normalize_tool_category("uncategorized")

LEGACY_TOOL_CATEGORIES: dict[str, str] = {
    "review_capabilities": "utility",
    "get_current_time": "utility",
    "web_search": "discovery",
    "fetch_url": "discovery",
    "generate_image": "media",
    "select_sticker_for_response": "expression",
    "react_with_emoji": "expression",
    "increase_media_context": "media",
    "process_gif": "media",
    "send_gif": "media",
    "process_youtube_video": "media",
    "pin_message": "moderation",
    "peek_profile_picture": "media",
    "remember_this_fact": "memory",
    "update_short_term_memory": "memory",
    "update_long_term_memory": "memory",
}

LEGACY_SOURCE_TYPE_OVERRIDES: dict[str, ToolSourceType] = {
    "web_search": ToolSourceType.REST,
    "fetch_url": ToolSourceType.REST,
    "generate_image": ToolSourceType.REST,
    "send_gif": ToolSourceType.REST,
    "peek_profile_picture": ToolSourceType.REST,
}

LEGACY_SIDE_EFFECT_LEVELS: dict[str, str] = {
    "generate_image": "write",
    "react_with_emoji": "write",
    "pin_message": "moderation",
    "remember_this_fact": "write",
    "update_short_term_memory": "write",
    "update_long_term_memory": "write",
}


def get_legacy_category(tool_name: str) -> str:
    category = LEGACY_TOOL_CATEGORIES.get((tool_name or "").strip(), UNCATEGORIZED_TOOL_CATEGORY)
    return normalize_tool_category(category)


def get_legacy_source_type(tool_name: str) -> ToolSourceType:
    return LEGACY_SOURCE_TYPE_OVERRIDES.get((tool_name or "").strip(), ToolSourceType.BUILTIN)


def get_legacy_side_effect_level(tool_name: str) -> str:
    return LEGACY_SIDE_EFFECT_LEVELS.get((tool_name or "").strip(), "read")
