from utils.tool_parser import extract_tool_call, strip_tool_call


def test_extract_tool_call_block():
    text = "Test\n```tool\n{\"tool\":\"web_search\",\"args\":{\"query\":\"cats\"}}\n```"
    call = extract_tool_call(text)
    assert call["tool"] == "web_search"
    assert call["args"]["query"] == "cats"


def test_extract_tool_call_accepts_canonical_schema():
    text = "```tool\n{\"name\":\"web_search\",\"arguments\":{\"query\":\"cats\"},\"call_id\":\"abc\"}\n```"
    call = extract_tool_call(text)
    assert call["tool"] == "web_search"
    assert call["name"] == "web_search"
    assert call["arguments"]["query"] == "cats"
    assert call["call_id"] == "abc"


def test_strip_tool_call_keeps_non_tool_json():
    text = "```json\n{\"foo\": \"bar\"}\n```"
    cleaned = strip_tool_call(text)
    assert "foo" in cleaned
