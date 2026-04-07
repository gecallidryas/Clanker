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


class OpenRouterManagerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        os.environ["OPENROUTER_REQUEST_TIMEOUT_SECONDS"] = "5"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    async def test_stream_generate_skips_unavailable_primary_model_and_uses_fallback(self):
        manager = api_manager.OpenRouterManager(
            api_key="test-key",
            model="nousresearch/deephermes-3-mistral-24b-preview",
            fallback_models=["cognitivecomputations/dolphin-mistral-24b-venice-edition:free"],
        )

        async def fake_stream(client, model, messages, timeout, tools=None):
            del client, messages, timeout, tools
            if model == "nousresearch/deephermes-3-mistral-24b-preview":
                raise RuntimeError("No endpoints found")
            yield api_manager.StreamEvent.text_delta("worked")
            yield api_manager.StreamEvent.done("stop")

        with (
            mock.patch.object(manager, "_classify_error", side_effect=lambda exc: "model_skip" if "No endpoints found" in str(exc) else "retry"),
            mock.patch.object(api_manager, "stream_openai_chat_completions", new=fake_stream),
        ):
            events = []
            async for event in manager.stream_generate("hi"):
                events.append((event.type, event.text, event.finish_reason))

        self.assertEqual(
            events,
            [
                ("text_delta", "worked", None),
                ("done", None, "stop"),
            ],
        )

    async def test_create_completion_caps_server_side_fallback_models_to_three_total(self):
        manager = api_manager.OpenRouterManager(
            api_key="test-key",
            model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        )
        captured: dict[str, object] = {}

        async def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content="ok"))])

        manager.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
        )

        await manager._create_completion(
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "hi",
            [
                "nousresearch/hermes-3-llama-3.1-405b:free",
                "nousresearch/deephermes-3-mistral-24b-preview",
                "mistralai/mistral-small-3.1-24b-instruct:free",
                "deepseek/deepseek-chat",
            ],
        )

        self.assertEqual(
            captured["extra_body"]["models"],
            [
                "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                "nousresearch/hermes-3-llama-3.1-405b:free",
                "nousresearch/deephermes-3-mistral-24b-preview",
            ],
        )
