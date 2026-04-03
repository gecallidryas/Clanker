import shutil
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp_tests"
TMP_ROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.runtime_guard import RuntimeInstanceGuard


class RuntimeGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp_path = TMP_ROOT / f"runtime_guard_{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def test_runtime_guard_claims_lock(self):
        guard = RuntimeInstanceGuard(self.tmp_path / "bot.lock")

        with guard.claim():
            self.assertTrue(guard.is_claimed)

    def test_runtime_guard_prevents_second_instance(self):
        lock_path = self.tmp_path / "bot.lock"
        guard1 = RuntimeInstanceGuard(lock_path)
        guard2 = RuntimeInstanceGuard(lock_path)

        with guard1.claim():
            with self.assertRaisesRegex(RuntimeError, "already running"):
                with guard2.claim():
                    pass

    def test_runtime_guard_releases_lock_on_context_exit(self):
        lock_path = self.tmp_path / "bot.lock"

        with RuntimeInstanceGuard(lock_path).claim():
            pass

        with RuntimeInstanceGuard(lock_path).claim():
            pass
