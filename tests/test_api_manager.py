import os
import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils import api_manager


class GeminiManagerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        os.environ["GEMINI_API_KEY"] = "key-one"
        os.environ["GEMINI_API_KEY_2"] = "key-two"
        os.environ["GEMINI_REQUEST_TIMEOUT_SECONDS"] = "5"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    async def test_generate_success_tracks_success(self):
        manager = api_manager.GeminiManager()
        def fake_generate(api_key, model_name, prompt, image):
            return SimpleNamespace(text="ok")

        with mock.patch.object(api_manager, "_generate_content_sync", new=fake_generate):
            text, key_used = await manager.generate("hi")

        self.assertEqual(text, "ok")
        self.assertEqual(key_used, "GEMINI_API_KEY")
        self.assertEqual(manager.keys[0].success_count, 1)
        self.assertEqual(manager.keys[0].error_count, 0)

    async def test_rate_limit_exhausts_key_and_rotates(self):
        manager = api_manager.GeminiManager()
        calls = []

        def fake_generate(api_key, model_name, prompt, image):
            calls.append(api_key)
            if len(calls) == 1:
                raise Exception("Rate limit exceeded")
            return SimpleNamespace(text="ok")

        with mock.patch.object(api_manager, "_generate_content_sync", new=fake_generate):
            text, key_used = await manager.generate("hi")

        self.assertEqual(text, "ok")
        self.assertEqual(key_used, "GEMINI_API_KEY_2")
        self.assertTrue(manager.keys[0].is_exhausted)
        self.assertEqual(manager.keys[0].error_count, 1)
        self.assertEqual(len(calls), 2)

    async def test_user_input_error_does_not_exhaust_or_retry(self):
        manager = api_manager.GeminiManager()
        calls = []

        def fake_generate(api_key, model_name, prompt, image):
            calls.append(api_key)
            raise Exception("Safety blocked")

        with mock.patch.object(api_manager, "_generate_content_sync", new=fake_generate):
            with self.assertRaises(api_manager.UserInputError):
                await manager.generate("hi")

        self.assertFalse(manager.keys[0].is_exhausted)
        self.assertEqual(manager.keys[0].error_count, 0)
        self.assertEqual(len(calls), 1)
