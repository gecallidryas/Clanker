from utils.text_splitter import split_message


def test_split_short_message():
    text = "hello"
    parts = split_message(text, limit=50)
    assert parts == ["hello"]


def test_split_long_message():
    text = "a" * 120
    parts = split_message(text, limit=50)
    assert "".join(parts) == text
    assert all(len(part) <= 50 for part in parts)


def test_split_code_block_preserves_fences():
    text = "```python\n" + ("print('x')\n" * 30) + "```\n"
    parts = split_message(text, limit=80)
    assert all(len(part) <= 80 for part in parts)
    for part in parts:
        assert part.count("```") % 2 == 0
