import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from cogs import ai_brain as ai_brain_mod  # noqa: E402


def test_ai_brain_no_longer_exposes_reply_sequence_runtime():
    source = Path(ROOT / "discord_bot" / "cogs" / "ai_brain.py").read_text(encoding="utf-8")

    assert "ReplySequenceControl" not in source
    assert "ReplySequenceSession" not in source
    assert "reply_sequence_sessions" not in source
    assert "reply_sequence_session" not in source


def test_ai_brain_build_prompt_signature_has_no_reply_sequence_argument():
    parameter_names = inspect.signature(ai_brain_mod.AIBrain.build_prompt).parameters

    assert "reply_sequence_session" not in parameter_names
