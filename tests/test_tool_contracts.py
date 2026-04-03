from tools.contracts import ToolDescriptor, ToolSourceType


def test_tool_descriptor_requires_namespaced_id():
    try:
        ToolDescriptor(
            tool_id="web_search",
            public_name="web_search",
            description="Search the web",
            source_type=ToolSourceType.BUILTIN,
            category="discovery",
        )
    except ValueError as exc:
        assert "namespaced" in str(exc)
    else:
        raise AssertionError("Expected a ValueError for a non-namespaced tool_id")


def test_tool_descriptor_defaults_display_name_to_public_name():
    descriptor = ToolDescriptor(
        tool_id="builtin:web_search",
        public_name="web_search",
        description="Search the web",
        source_type=ToolSourceType.BUILTIN,
        category="discovery",
    )

    assert descriptor.effective_display_name == "web_search"
