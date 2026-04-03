from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from tools.contracts import ToolCallEnvelope, ToolDescriptor, ToolTurnContext


class NativeToolTransportAdapter(ABC):
    provider_name: str = ""

    @abstractmethod
    def supports_provider(self, provider_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def build_provider_tool_definitions(
        self,
        *,
        descriptors: list[ToolDescriptor],
        context: ToolTurnContext,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def parse_provider_tool_call(
        self,
        payload: Any,
        *,
        context: ToolTurnContext,
    ) -> Optional[ToolCallEnvelope]:
        raise NotImplementedError


class ProviderNativeToolAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: list[NativeToolTransportAdapter] = []

    def clear(self) -> None:
        self._adapters.clear()

    def register(self, adapter: NativeToolTransportAdapter) -> NativeToolTransportAdapter:
        self._adapters = [
            existing
            for existing in self._adapters
            if existing.provider_name.strip().lower() != adapter.provider_name.strip().lower()
        ]
        self._adapters.append(adapter)
        return adapter

    def resolve(self, provider_name: str | None) -> Optional[NativeToolTransportAdapter]:
        normalized = str(provider_name or "").strip().lower()
        if not normalized:
            return None
        for adapter in self._adapters:
            if adapter.supports_provider(normalized):
                return adapter
        return None

    def list_adapters(self) -> list[NativeToolTransportAdapter]:
        return list(self._adapters)


_native_adapter_registry = ProviderNativeToolAdapterRegistry()


def get_native_tool_adapter_registry() -> ProviderNativeToolAdapterRegistry:
    return _native_adapter_registry
