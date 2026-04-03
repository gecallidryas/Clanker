from __future__ import annotations

from dataclasses import replace
from typing import Optional

from tools.contracts import ToolDescriptor


class ToolRegistry:
    def __init__(self) -> None:
        self._descriptors_by_id: dict[str, ToolDescriptor] = {}
        self._public_name_index: dict[str, str] = {}
        self._alias_index: dict[str, str] = {}

    def clear(self) -> None:
        self._descriptors_by_id.clear()
        self._public_name_index.clear()
        self._alias_index.clear()

    def register_descriptor(self, descriptor: ToolDescriptor) -> ToolDescriptor:
        existing_tool_id = self._public_name_index.get(descriptor.public_name)
        if existing_tool_id and existing_tool_id != descriptor.tool_id:
            raise ValueError(f"public_name collision for {descriptor.public_name}")

        for alias in descriptor.aliases:
            if not alias.strip():
                raise ValueError("aliases must be non-empty strings")
            existing_alias_id = self._alias_index.get(alias)
            if existing_alias_id and existing_alias_id != descriptor.tool_id:
                raise ValueError(f"alias collision for {alias}")

        canonical_aliases = tuple(dict.fromkeys(alias.strip() for alias in descriptor.aliases if alias.strip()))
        if canonical_aliases != descriptor.aliases:
            descriptor = replace(descriptor, aliases=canonical_aliases)

        self._descriptors_by_id[descriptor.tool_id] = descriptor
        self._public_name_index[descriptor.public_name] = descriptor.tool_id

        for alias, tool_id in list(self._alias_index.items()):
            if tool_id == descriptor.tool_id:
                self._alias_index.pop(alias, None)
        for alias in descriptor.aliases:
            self._alias_index[alias] = descriptor.tool_id
        return descriptor

    def get_descriptor(self, tool_id: str) -> Optional[ToolDescriptor]:
        return self._descriptors_by_id.get(tool_id)

    def remove_descriptor(self, tool_id: str) -> None:
        descriptor = self._descriptors_by_id.pop(tool_id, None)
        if descriptor is None:
            return
        self._public_name_index.pop(descriptor.public_name, None)
        for alias in descriptor.aliases:
            self._alias_index.pop(alias, None)

    def resolve_descriptor(self, name_or_alias: str) -> Optional[ToolDescriptor]:
        if not name_or_alias:
            return None
        tool_id = self._public_name_index.get(name_or_alias) or self._alias_index.get(name_or_alias)
        if not tool_id:
            return None
        return self._descriptors_by_id.get(tool_id)

    def list_descriptors(self) -> list[ToolDescriptor]:
        return list(self._descriptors_by_id.values())

    def remove_descriptors_by_prefix(self, prefix: str) -> None:
        tool_ids = [tool_id for tool_id in self._descriptors_by_id if tool_id.startswith(prefix)]
        for tool_id in tool_ids:
            self.remove_descriptor(tool_id)


_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _tool_registry
