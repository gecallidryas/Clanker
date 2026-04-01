import pytest

from tools.contracts import ToolDescriptor, ToolSourceType
from tools.registry import ToolRegistry


def test_tool_registry_resolves_public_name_and_aliases():
    registry = ToolRegistry()
    descriptor = ToolDescriptor(
        tool_id="builtin:web_search",
        public_name="web_search",
        description="Search the web",
        source_type=ToolSourceType.BUILTIN,
        category="discovery",
        aliases=("web-search", "brave_web_search"),
    )

    registry.register_descriptor(descriptor)

    assert registry.resolve_descriptor("web_search") == descriptor
    assert registry.resolve_descriptor("web-search") == descriptor
    assert registry.resolve_descriptor("brave_web_search") == descriptor


def test_tool_registry_rejects_public_name_collision():
    registry = ToolRegistry()
    first = ToolDescriptor(
        tool_id="builtin:web_search",
        public_name="web_search",
        description="Search the web",
        source_type=ToolSourceType.BUILTIN,
        category="discovery",
    )
    second = ToolDescriptor(
        tool_id="rest:web_search",
        public_name="web_search",
        description="Search the web via REST",
        source_type=ToolSourceType.REST,
        category="discovery",
    )

    registry.register_descriptor(first)

    with pytest.raises(ValueError, match="public_name collision"):
        registry.register_descriptor(second)
