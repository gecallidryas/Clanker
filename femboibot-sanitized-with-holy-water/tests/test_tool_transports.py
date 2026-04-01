import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))
sys.path.insert(0, str(ROOT))

from tools.contracts import ToolCallEnvelope, ToolDescriptor, ToolSourceType
from tools.transports.native_base import NativeToolTransportAdapter, get_native_tool_adapter_registry
from tools.transports.prompt_emulated import build_prompt_tool_schemas, parse_prompt_tool_call


class _FakeAdapter(NativeToolTransportAdapter):
    provider_name = "fake-provider"

    def supports_provider(self, provider_name: str) -> bool:
        return provider_name == self.provider_name

    async def build_provider_tool_definitions(self, *, descriptors, context):
        return [{"name": descriptor.public_name} for descriptor in descriptors]

    def parse_provider_tool_call(self, payload, *, context):
        return None


class ToolTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_parse_prompt_tool_call_accepts_canonical_payload(self):
        envelope = parse_prompt_tool_call(
            '```tool {"name":"web_search","arguments":{"query":"cats"},"call_id":"abc"} ```'
        )
        self.assertIsInstance(envelope, ToolCallEnvelope)
        self.assertEqual(envelope.tool_name, "web_search")
        self.assertEqual(envelope.arguments, {"query": "cats"})
        self.assertEqual(envelope.call_id, "abc")

    async def test_build_prompt_tool_schemas_uses_runtime_tools(self):
        descriptor = ToolDescriptor(
            tool_id="rest:web_search",
            public_name="web_search",
            description="Search the web",
            source_type=ToolSourceType.REST,
            category="discovery",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Result limit"},
                },
                "required": ["limit"],
                "additionalProperties": False,
            },
        )
        with patch(
            "tools.availability.get_allowed_tool_descriptors",
            AsyncMock(return_value=[descriptor]),
        ):
            schemas = await build_prompt_tool_schemas(context=object())
        self.assertEqual(schemas[0]["name"], "web_search")
        self.assertEqual(schemas[0]["parameters"]["properties"]["limit"]["type"], "integer")
        self.assertEqual(schemas[0]["parameters"]["required"], ["limit"])

    async def test_native_adapter_registry_resolves_by_provider(self):
        registry = get_native_tool_adapter_registry()
        registry.clear()
        adapter = _FakeAdapter()
        registry.register(adapter)
        self.assertIs(registry.resolve("fake-provider"), adapter)
        self.assertIsNone(registry.resolve("other-provider"))


if __name__ == "__main__":
    unittest.main()
