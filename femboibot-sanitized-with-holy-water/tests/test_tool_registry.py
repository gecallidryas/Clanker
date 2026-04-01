from utils.tool_registry import (
    ToolDefinition,
    _reset_registry_for_tests,
    get_unified_tool_registry,
    is_tool_enabled,
    register_tool,
)


def setup_function():
    _reset_registry_for_tests()


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


def test_legacy_registration_mirrors_into_unified_registry():
    async def _noop(context, args):
        return None

    tool = ToolDefinition(
        name="web_search",
        description="Search the web",
        args_schema={"query": "query"},
        handler=_noop,
        feature_flag="web_search_enabled",
    )

    register_tool(tool)

    descriptor = get_unified_tool_registry().resolve_descriptor("web_search")
    assert descriptor is not None
    assert descriptor.tool_id == "rest:web_search"
    assert descriptor.category == "discovery"
    assert descriptor.input_schema == {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "query",
            }
        },
        "additionalProperties": False,
    }
