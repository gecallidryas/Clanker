import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

if "utils.rag_store" not in sys.modules:
    rag_store_stub = types.ModuleType("utils.rag_store")

    async def _dummy_get_rag_context(*args, **kwargs):
        return ""

    rag_store_stub.get_rag_context = _dummy_get_rag_context
    sys.modules["utils.rag_store"] = rag_store_stub

from cogs.ai_brain import _extract_channel_request, _extract_role_request  # noqa: E402

# The stub is only needed while importing ai_brain for this test module.
sys.modules.pop("utils.rag_store", None)


def test_extract_channel_request_create_text_under_category():
    parsed = _extract_channel_request('create channel "general-chat" under "community"')
    assert parsed is not None
    assert parsed["sub_action"] == "create_text_channel"
    assert parsed["channel_name"] == "general-chat"
    assert parsed["parent_name"] == "community"


def test_extract_channel_request_create_category():
    parsed = _extract_channel_request('create category "Games"')
    assert parsed is not None
    assert parsed["sub_action"] == "create_category"
    assert parsed["channel_name"] == "Games"


def test_extract_channel_request_delete_text_channel():
    parsed = _extract_channel_request('delete channel "old-chat"')
    assert parsed is not None
    assert parsed["sub_action"] == "delete_text_channel"
    assert parsed["channel_name"] == "old-chat"


def test_extract_channel_request_delete_category():
    parsed = _extract_channel_request('remove category "Archive"')
    assert parsed is not None
    assert parsed["sub_action"] == "delete_category"
    assert parsed["channel_name"] == "Archive"


def test_extract_role_request_create_role():
    parsed = _extract_role_request('create role "Raid Leader"')
    assert parsed == {"sub_action": "create", "target_name": "Raid Leader"}


def test_extract_role_request_delete_role():
    parsed = _extract_role_request('delete role "temp role"')
    assert parsed == {"sub_action": "delete", "target_name": "temp role"}
