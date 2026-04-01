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

from cogs.ai_brain import _is_admin_intent_content  # noqa: E402


def test_admin_intent_detects_starboard_setup_text():
    assert _is_admin_intent_content(
        "Can you set up starboard for this channel and send posts there?"
    )


def test_admin_intent_detects_channel_role_management_text():
    assert _is_admin_intent_content("Please create channel announcements and delete role temp")


def test_admin_intent_ignores_regular_chat():
    assert not _is_admin_intent_content("how are you doing today?")
