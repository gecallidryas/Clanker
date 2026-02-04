from utils.tool_parser import extract_tool_call, strip_tool_call


def test_extract_tool_call_block():
    text = "Test\n```tool\n{\"tool\":\"web_search\",\"args\":{\"query\":\"cats\"}}\n```"
    call = extract_tool_call(text)
    assert call["tool"] == "web_search"
    assert call["args"]["query"] == "cats"


def test_strip_tool_call_keeps_non_tool_json():
    text = "```json\n{\"foo\": \"bar\"}\n```"
    cleaned = strip_tool_call(text)
    assert "foo" in cleaned
