import asyncio
import sys
import types
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

if "aiosqlite" not in sys.modules:
    aiosqlite_stub = types.ModuleType("aiosqlite")

    class _Connection:
        pass

    async def _connect(*args, **kwargs):
        raise RuntimeError("aiosqlite stub should not be used in this test")

    aiosqlite_stub.Connection = _Connection
    aiosqlite_stub.Row = object
    aiosqlite_stub.connect = _connect
    sys.modules["aiosqlite"] = aiosqlite_stub

if "google" not in sys.modules:
    google_stub = types.ModuleType("google")
    genai_stub = types.ModuleType("google.genai")
    types_stub = types.ModuleType("google.genai.types")

    class _SafetySetting:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class _GenerateContentConfig:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class _Client:
        def __init__(self, *args, **kwargs):
            self.models = types.SimpleNamespace(
                generate_content=lambda *a, **k: None,
                generate_content_stream=lambda *a, **k: [],
            )

    genai_stub.Client = _Client
    types_stub.SafetySetting = _SafetySetting
    types_stub.GenerateContentConfig = _GenerateContentConfig
    genai_stub.types = types_stub
    google_stub.genai = genai_stub
    sys.modules["google"] = google_stub
    sys.modules["google.genai"] = genai_stub
    sys.modules["google.genai.types"] = types_stub

if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _AsyncOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=None)
            )

    class _OpenAIError(Exception):
        pass

    openai_stub.AsyncOpenAI = _AsyncOpenAI
    openai_stub.APIConnectionError = _OpenAIError
    openai_stub.APITimeoutError = _OpenAIError
    openai_stub.APIStatusError = _OpenAIError
    openai_stub.AuthenticationError = _OpenAIError
    openai_stub.BadRequestError = _OpenAIError
    openai_stub.ConflictError = _OpenAIError
    openai_stub.NotFoundError = _OpenAIError
    openai_stub.PermissionDeniedError = _OpenAIError
    openai_stub.RateLimitError = _OpenAIError
    openai_stub.UnprocessableEntityError = _OpenAIError
    sys.modules["openai"] = openai_stub

from utils.guild_ai import get_custom_endpoint_features
from utils.api_manager import (
    _build_gemini_stream_request,
    stream_events_from_text,
    stream_gemini_with_key,
    stream_openai_chat_completions,
)


def test_custom_endpoint_defaults_to_text_only_without_explicit_openai_compat_flags():
    features = get_custom_endpoint_features(["streaming", "tools"])

    assert features.openai_compatible is False
    assert features.supports_streaming is False
    assert features.supports_tools is False
    assert features.text_only is True


def test_custom_endpoint_uses_streaming_and_tools_when_explicitly_marked_openai_compatible():
    features = get_custom_endpoint_features(["openai_compat", "streaming", "tools"])

    assert features.openai_compatible is True
    assert features.supports_streaming is True
    assert features.supports_tools is True
    assert features.text_only is False


def test_one_shot_text_stream_adapter_emits_text_then_done():
    async def _run():
        events = []
        async for event in stream_events_from_text("hello world"):
            events.append((event.type, event.text, event.finish_reason))
        assert events == [
            ("text_delta", "hello world", None),
            ("done", None, "stop"),
        ]

    asyncio.run(_run())


def test_openai_stream_adapter_maps_content_filter_to_moderation_stop():
    class Delta:
        content = None
        tool_calls = None

    class Choice:
        delta = Delta()
        finish_reason = "content_filter"

    class Chunk:
        choices = [Choice()]

    class FakeCompletions:
        async def create(self, **kwargs):
            async def iterator():
                yield Chunk()

            return iterator()

    class FakeClient:
        chat = types.SimpleNamespace(completions=FakeCompletions())

    async def _run():
        events = []
        async for event in stream_openai_chat_completions(
            FakeClient(),
            model="x",
            messages=[{"role": "user", "content": "hi"}],
        ):
            events.append((event.type, event.finish_reason))
        assert events == [("moderation_stop", "content_filter")]

    asyncio.run(_run())


def test_gemini_stream_request_keeps_structured_messages():
    contents, system_instruction = _build_gemini_stream_request(
        "fallback prompt",
        messages=[
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
        system_instruction="system text",
    )

    assert system_instruction == "system text"
    assert contents == [
        {"role": "user", "parts": [{"text": "hello"}]},
        {"role": "model", "parts": [{"text": "hi"}]},
    ]


def test_gemini_stream_yields_incrementally_before_producer_finishes():
    started = asyncio.Event()
    release = asyncio.Event()

    def fake_pump(api_key, model_name, contents, system_instruction, emit):
        emit("hello ")
        started_loop = asyncio.get_event_loop_policy()
        del started_loop
        import time

        while not release.is_set():
            time.sleep(0.01)
        emit("world")

    async def _run():
        with mock.patch("utils.api_manager._pump_gemini_stream_sync", new=fake_pump):
            stream = stream_gemini_with_key(
                "key",
                "model",
                "prompt",
                request_timeout=1.0,
                messages=[{"role": "user", "content": "hello"}],
            )
            first = await asyncio.wait_for(anext(stream), timeout=0.2)
            assert (first.type, first.text) == ("text_delta", "hello ")
            release.set()
            remaining = []
            async for event in stream:
                remaining.append((event.type, event.text, event.finish_reason))
            assert remaining == [
                ("text_delta", "world", None),
                ("done", None, "stop"),
            ]

    asyncio.run(_run())
