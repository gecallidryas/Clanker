from utils.memory_id import format_memory_with_id


def test_format_memory_with_id():
    assert format_memory_with_id(42, "likes ramen") == "ID:42 likes ramen"

