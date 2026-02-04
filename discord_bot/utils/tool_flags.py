from __future__ import annotations

# Map tool name -> guild_config flag name (or None for always-on tools).
TOOL_FLAG_MAP: dict[str, str | None] = {
    "review_capabilities": None,
    "web_search": "web_search_enabled",
    "fetch_url": "web_search_enabled",
    "generate_image": "image_gen_enabled",
    "select_sticker_for_response": "sticker_usage_enabled",
    "react_with_emoji": "emoji_usage_enabled",
    "pin_message": "pin_message_enabled",
    "process_youtube_video": "youtube_enabled",
    "peek_profile_picture": "profile_peek_enabled",
    "increase_media_context": None,
    "process_gif": None,
    "remember_this_fact": "self_teaching_enabled",
    "update_short_term_memory": "self_teaching_enabled",
    "update_long_term_memory": "self_teaching_enabled",
}


DEFAULT_FLAG_VALUES: dict[str, int] = {
    "web_search_enabled": 1,
    "image_gen_enabled": 1,
    "sticker_usage_enabled": 1,
    "emoji_usage_enabled": 1,
    "pin_message_enabled": 0,
    "self_teaching_enabled": 0,
    "youtube_enabled": 1,
    "profile_peek_enabled": 0,
    "rag_enabled": 1,
}


def get_tool_flag(tool_name: str) -> str | None:
    return TOOL_FLAG_MAP.get(tool_name)
