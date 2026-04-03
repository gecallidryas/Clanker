import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.runtime_guard import RuntimeInstanceGuard


def test_runtime_guard_claims_lock(tmp_path):
    guard = RuntimeInstanceGuard(tmp_path / "bot.lock")

    with guard.claim():
        assert guard.is_claimed is True


def test_runtime_guard_prevents_second_instance(tmp_path):
    lock_path = tmp_path / "bot.lock"
    guard1 = RuntimeInstanceGuard(lock_path)
    guard2 = RuntimeInstanceGuard(lock_path)

    with guard1.claim():
        with pytest.raises(RuntimeError, match="already running"):
            with guard2.claim():
                pass


def test_runtime_guard_releases_lock_on_context_exit(tmp_path):
    lock_path = tmp_path / "bot.lock"

    with RuntimeInstanceGuard(lock_path).claim():
        pass

    with RuntimeInstanceGuard(lock_path).claim():
        pass
