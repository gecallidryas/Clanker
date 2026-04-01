from __future__ import annotations

from utils.feature_flag_mapper import (
    BUILTIN_TOOL_FEATURE_FLAGS,
    DEFAULT_FEATURE_FLAG_VALUES,
    get_required_feature_flag,
)

# Map tool name -> guild_config flag name (or None for always-on tools).
TOOL_FLAG_MAP: dict[str, str | None] = {
    "review_capabilities": None,
    "increase_media_context": None,
    "process_gif": None,
    **BUILTIN_TOOL_FEATURE_FLAGS,
}


DEFAULT_FLAG_VALUES: dict[str, int] = dict(DEFAULT_FEATURE_FLAG_VALUES)


def get_tool_flag(tool_name: str) -> str | None:
    if tool_name in TOOL_FLAG_MAP:
        return TOOL_FLAG_MAP[tool_name]
    return get_required_feature_flag(tool_name)
