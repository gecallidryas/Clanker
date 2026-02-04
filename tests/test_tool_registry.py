from utils.tool_registry import ToolDefinition, is_tool_enabled


def test_tool_flag_defaults():
    async def _noop(context, args):
        return None

    tool_web = ToolDefinition(
        name="web_search",
        description="",
        args_schema={},
        handler=_noop,
        feature_flag="web_search_enabled",
    )
    tool_pin = ToolDefinition(
        name="pin_message",
        description="",
        args_schema={},
        handler=_noop,
        feature_flag="pin_message_enabled",
    )
    assert is_tool_enabled(tool_web, {}) is True
    assert is_tool_enabled(tool_pin, {}) is False
