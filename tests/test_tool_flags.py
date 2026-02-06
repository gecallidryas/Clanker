from utils.feature_flag_mapper import (
    config_to_feature_flags,
    filter_tools_by_feature_flags,
    get_required_feature_flag,
    get_tools_requiring_feature_flag,
    should_filter_tool,
)
from utils.tool_flags import DEFAULT_FLAG_VALUES, get_tool_flag


def test_tool_flag_lookup_uses_feature_mapper():
    assert get_tool_flag("web_search") == "web_search_enabled"
    assert get_tool_flag("send_gif") == "gif_responses_enabled"
    assert get_tool_flag("increase_media_context") is None
    assert get_required_feature_flag("fetch-url") == "web_search_enabled"


def test_default_flag_values_present():
    assert DEFAULT_FLAG_VALUES["web_search_enabled"] == 1
    assert DEFAULT_FLAG_VALUES["pin_message_enabled"] == 0


def test_feature_flag_filtering_helpers():
    flags = config_to_feature_flags({"web_search_enabled": 0, "gif_responses_enabled": 1})
    assert should_filter_tool("web_search", flags) is True
    assert should_filter_tool("send_gif", flags) is False

    filtered = filter_tools_by_feature_flags(["web_search", "send_gif"], flags)
    assert filtered == ["send_gif"]

    tools = get_tools_requiring_feature_flag("web_search_enabled")
    assert "web_search" in tools

