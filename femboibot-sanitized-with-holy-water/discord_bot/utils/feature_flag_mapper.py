from __future__ import annotations

from typing import Any, Mapping

# Tool -> guild_config feature flag
BUILTIN_TOOL_FEATURE_FLAGS: dict[str, str] = {
    "web_search": "web_search_enabled",
    "fetch_url": "web_search_enabled",
    "generate_image": "image_gen_enabled",
    "select_sticker_for_response": "sticker_usage_enabled",
    "react_with_emoji": "emoji_usage_enabled",
    "pin_message": "pin_message_enabled",
    "process_youtube_video": "youtube_enabled",
    "peek_profile_picture": "profile_peek_enabled",
    "send_gif": "gif_responses_enabled",
    "remember_this_fact": "self_teaching_enabled",
    "update_short_term_memory": "self_teaching_enabled",
    "update_long_term_memory": "self_teaching_enabled",
}

# Optional MCP/alias names mapped to same flags.
MCP_TOOL_FEATURE_FLAGS: dict[str, str] = {
    "web-search": "web_search_enabled",
    "fetch-url": "web_search_enabled",
    "brave_web_search": "web_search_enabled",
    "brave_image_search": "web_search_enabled",
    "brave_video_search": "web_search_enabled",
    "brave_news_search": "web_search_enabled",
}

ALL_TOOL_FEATURE_FLAGS: dict[str, str] = {
    **BUILTIN_TOOL_FEATURE_FLAGS,
    **MCP_TOOL_FEATURE_FLAGS,
}

DEFAULT_FEATURE_FLAG_VALUES: dict[str, int] = {
    "web_search_enabled": 1,
    "image_gen_enabled": 1,
    "sticker_usage_enabled": 1,
    "emoji_usage_enabled": 1,
    "pin_message_enabled": 0,
    "self_teaching_enabled": 0,
    "youtube_enabled": 1,
    "profile_peek_enabled": 0,
    "rag_enabled": 1,
    "gif_responses_enabled": 0,
}


def get_required_feature_flag(tool_name: str) -> str | None:
    return ALL_TOOL_FEATURE_FLAGS.get((tool_name or "").strip())


def tool_requires_feature_flag(tool_name: str, feature_flag: str) -> bool:
    required = get_required_feature_flag(tool_name)
    return required == feature_flag


def get_tools_requiring_feature_flag(feature_flag: str) -> list[str]:
    return [
        tool_name
        for tool_name, required_flag in ALL_TOOL_FEATURE_FLAGS.items()
        if required_flag == feature_flag
    ]


def should_filter_tool(tool_name: str, feature_flags: Mapping[str, bool]) -> bool:
    required = get_required_feature_flag(tool_name)
    if not required:
        return False
    return not bool(feature_flags.get(required, False))


def filter_tools_by_feature_flags(
    tool_names: list[str],
    feature_flags: Mapping[str, bool],
) -> list[str]:
    return [name for name in tool_names if not should_filter_tool(name, feature_flags)]


def config_to_feature_flags(config: Mapping[str, Any]) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for flag_name, default in DEFAULT_FEATURE_FLAG_VALUES.items():
        value = config.get(flag_name, default)
        try:
            flags[flag_name] = bool(int(value))
        except (TypeError, ValueError):
            flags[flag_name] = bool(value)
    return flags

