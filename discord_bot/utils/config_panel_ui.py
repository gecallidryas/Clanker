from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

import discord

from utils.admin_views import AdminPanelView


def _response_is_done(interaction: discord.Interaction) -> bool:
    checker = getattr(interaction.response, "is_done", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:
            return False
    return False


@dataclass(frozen=True)
class FeatureOption:
    key: str
    label: str
    enabled: bool


@dataclass(frozen=True)
class ActionOption:
    label: str
    value: str
    description: str


@dataclass(frozen=True)
class SingleSelectOption:
    label: str
    value: str
    description: str = ""
    default: bool = False


class _ActionSelect(discord.ui.Select):
    def __init__(self, parent: "ActionMenuView", options: Sequence[ActionOption]) -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Choose an action",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=option.label,
                    value=option.value,
                    description=option.description[:100],
                )
                for option in options
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.parent_view.handle_action(interaction, self.values[0])


class ActionMenuView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        options: Sequence[ActionOption],
        on_action: Callable[[discord.Interaction, str], Awaitable[None]],
        timeout: float = 300.0,
    ) -> None:
        super().__init__(invoker_id=invoker_id, timeout=timeout)
        self._on_action = on_action
        self._select = _ActionSelect(self, options)
        self.add_item(self._select)

    async def handle_action(self, interaction: discord.Interaction, value: str) -> None:
        await self._on_action(interaction, value)

    async def close(self, interaction: discord.Interaction) -> None:
        self.disable_all_items()
        if _response_is_done(interaction):
            await interaction.followup.send("Closed.", ephemeral=True)
        else:
            await interaction.response.send_message("Closed.", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.close(interaction)


class _FeatureSelect(discord.ui.Select):
    def __init__(self, parent: "FeatureGroupView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Select features in this group",
            min_values=1,
            max_values=max(1, len(parent.options)),
            options=[
                discord.SelectOption(
                    label=option.label[:100],
                    value=option.key,
                    description=f"Currently {'ON' if option.enabled else 'OFF'}",
                )
                for option in parent.options
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.set_selected(self.values)
        await interaction.response.edit_message(view=self.parent_view)


class FeatureGroupView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        title: str,
        options: Sequence[FeatureOption],
        apply_changes: Callable[[dict[str, bool]], Awaitable[str]],
        timeout: float = 300.0,
    ) -> None:
        super().__init__(invoker_id=invoker_id, timeout=timeout)
        self.title = title
        self.options = list(options)
        self.apply_changes = apply_changes
        self.selected_keys: list[str] = []
        self._select = _FeatureSelect(self)
        self.add_item(self._select)
        self._sync_buttons()

    def set_selected(self, values: Sequence[str]) -> None:
        self.selected_keys = list(dict.fromkeys(str(value) for value in values if str(value)))
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        disabled = not self.selected_keys
        self.enable_button.disabled = disabled
        self.disable_button.disabled = disabled

    async def _send_result(self, interaction: discord.Interaction, content: str) -> None:
        if _response_is_done(interaction):
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)

    async def _apply(self, interaction: discord.Interaction, value: bool) -> None:
        if not self.selected_keys:
            await self._send_result(interaction, "Select at least one feature first.")
            return
        result = await self.apply_changes({key: value for key in self.selected_keys})
        await self._send_result(interaction, result)

    async def enable_selected(self, interaction: discord.Interaction) -> None:
        await self._apply(interaction, True)

    async def disable_selected(self, interaction: discord.Interaction) -> None:
        await self._apply(interaction, False)

    async def cancel(self, interaction: discord.Interaction) -> None:
        self.disable_all_items()
        await self._send_result(interaction, "Cancelled.")

    @discord.ui.button(label="Enable Selected", style=discord.ButtonStyle.success)
    async def enable_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.enable_selected(interaction)

    @discord.ui.button(label="Disable Selected", style=discord.ButtonStyle.danger)
    async def disable_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.disable_selected(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cancel(interaction)


class _PageValueSelect(discord.ui.Select):
    def __init__(self, parent: "PaginatedListEditorView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Select entries on this page",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Nothing to remove", value="__empty__")],
            disabled=True,
        )
        self.refresh()

    def refresh(self) -> None:
        entries = self.parent_view.current_page_entries()
        if not entries:
            self.disabled = True
            self.min_values = 1
            self.max_values = 1
            self.options = [discord.SelectOption(label="Nothing to remove", value="__empty__")]
            return
        self.disabled = False
        self.min_values = 1
        self.max_values = len(entries)
        self.options = [
            discord.SelectOption(label=entry[:100], value=entry, default=entry in self.parent_view.selected_values)
            for entry in entries
        ]

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.set_selected(self.values)
        self.refresh()
        await interaction.response.edit_message(view=self.parent_view)


class PaginatedListEditorView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        entries: Sequence[str],
        apply_remove: Callable[[list[str]], Awaitable[str]],
        apply_clear: Callable[[], Awaitable[str]],
        page_size: int = 10,
        requires_clear_auth: bool = False,
        has_auth: Callable[[], Awaitable[bool]] | None = None,
        request_auth: Callable[[discord.Interaction], Awaitable[None]] | None = None,
        timeout: float = 300.0,
    ) -> None:
        super().__init__(invoker_id=invoker_id, timeout=timeout)
        self.entries = list(entries)
        self.apply_remove = apply_remove
        self.apply_clear = apply_clear
        self.page_size = max(1, page_size)
        self.requires_clear_auth = requires_clear_auth
        self.has_auth = has_auth
        self.request_auth = request_auth
        self.page_index = 0
        self.selected_values: list[str] = []
        self.select = _PageValueSelect(self)
        self.add_item(self.select)
        self._sync_buttons()

    @property
    def total_pages(self) -> int:
        if not self.entries:
            return 1
        return ((len(self.entries) - 1) // self.page_size) + 1

    def current_page_entries(self) -> list[str]:
        start = self.page_index * self.page_size
        end = start + self.page_size
        return self.entries[start:end]

    def set_selected(self, values: Sequence[str]) -> None:
        self.selected_values = list(dict.fromkeys(str(value) for value in values if str(value)))
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.previous_button.disabled = self.page_index <= 0
        self.next_button.disabled = self.page_index >= self.total_pages - 1
        self.remove_button.disabled = not self.selected_values
        self.clear_button.disabled = not self.entries
        self.select.refresh()

    async def _send_message(self, interaction: discord.Interaction, content: str) -> None:
        if _response_is_done(interaction):
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)

    async def go_next(self, interaction: discord.Interaction) -> None:
        if self.page_index < self.total_pages - 1:
            self.page_index += 1
        self.selected_values = []
        self._sync_buttons()
        if _response_is_done(interaction):
            await interaction.followup.send(f"Page {self.page_index + 1}/{self.total_pages}", ephemeral=True)
        else:
            await interaction.response.edit_message(view=self)

    async def go_previous(self, interaction: discord.Interaction) -> None:
        if self.page_index > 0:
            self.page_index -= 1
        self.selected_values = []
        self._sync_buttons()
        if _response_is_done(interaction):
            await interaction.followup.send(f"Page {self.page_index + 1}/{self.total_pages}", ephemeral=True)
        else:
            await interaction.response.edit_message(view=self)

    async def remove_selected_entries(self, interaction: discord.Interaction) -> None:
        if not self.selected_values:
            await self._send_message(interaction, "Nothing selected.")
            return
        result = await self.apply_remove(self.selected_values)
        self.entries = [entry for entry in self.entries if entry not in self.selected_values]
        self.selected_values = []
        if self.page_index >= self.total_pages:
            self.page_index = max(0, self.total_pages - 1)
        self._sync_buttons()
        await self._send_message(interaction, result)

    async def clear_all_entries(self, interaction: discord.Interaction) -> None:
        if self.requires_clear_auth and self.has_auth is not None:
            if not await self.has_auth():
                if self.request_auth is not None:
                    await self.request_auth(interaction)
                    return
        result = await self.apply_clear()
        self.entries = []
        self.page_index = 0
        self.selected_values = []
        self._sync_buttons()
        await self._send_message(interaction, result)

    async def cancel(self, interaction: discord.Interaction) -> None:
        self.disable_all_items()
        await self._send_message(interaction, "Cancelled.")

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.go_previous(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.go_next(interaction)

    @discord.ui.button(label="Remove Selected", style=discord.ButtonStyle.primary)
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.remove_selected_entries(interaction)

    @discord.ui.button(label="Clear All", style=discord.ButtonStyle.danger)
    async def clear_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.clear_all_entries(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cancel(interaction)


class _ChannelAddSelect(discord.ui.ChannelSelect):
    def __init__(self, parent: "ChannelListEditorView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Add channels",
            min_values=1,
            max_values=10,
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        channel_ids = [str(channel.id) for channel in self.values]
        message = await self.parent_view.add_channels(channel_ids)
        await interaction.response.send_message(message, ephemeral=True)


class ChannelListEditorView(PaginatedListEditorView):
    def __init__(
        self,
        *,
        invoker_id: int,
        entries: Sequence[str],
        apply_add: Callable[[list[str]], Awaitable[str]],
        apply_remove: Callable[[list[str]], Awaitable[str]],
        apply_clear: Callable[[], Awaitable[str]],
        page_size: int = 10,
        requires_clear_auth: bool = False,
        has_auth: Callable[[], Awaitable[bool]] | None = None,
        request_auth: Callable[[discord.Interaction], Awaitable[None]] | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.apply_add = apply_add
        super().__init__(
            invoker_id=invoker_id,
            entries=entries,
            apply_remove=apply_remove,
            apply_clear=apply_clear,
            page_size=page_size,
            requires_clear_auth=requires_clear_auth,
            has_auth=has_auth,
            request_auth=request_auth,
            timeout=timeout,
        )
        self.add_item(_ChannelAddSelect(self))

    async def add_channels(self, channel_ids: list[str]) -> str:
        result = await self.apply_add(channel_ids)
        for channel_id in channel_ids:
            if channel_id not in self.entries:
                self.entries.append(channel_id)
        self._sync_buttons()
        return result


class _SingleChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent: "SingleChannelPickerView", placeholder: str) -> None:
        self.parent_view = parent
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        channel_id = int(self.values[0].id)
        message = await self.parent_view.apply(channel_id)
        await interaction.response.send_message(message, ephemeral=True)


class SingleChannelPickerView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        placeholder: str,
        apply_channel: Callable[[int], Awaitable[str]],
        timeout: float = 300.0,
    ) -> None:
        super().__init__(invoker_id=invoker_id, timeout=timeout)
        self.apply = apply_channel
        self.add_item(_SingleChannelSelect(self, placeholder))


class _SingleRoleSelect(discord.ui.RoleSelect):
    def __init__(self, parent: "SingleRolePickerView", placeholder: str) -> None:
        self.parent_view = parent
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        role_id = int(self.values[0].id)
        message = await self.parent_view.apply(role_id)
        await interaction.response.send_message(message, ephemeral=True)


class SingleRolePickerView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        placeholder: str,
        apply_role: Callable[[int], Awaitable[str]],
        timeout: float = 300.0,
    ) -> None:
        super().__init__(invoker_id=invoker_id, timeout=timeout)
        self.apply = apply_role
        self.add_item(_SingleRoleSelect(self, placeholder))


class _SingleValueSelect(discord.ui.Select):
    def __init__(self, parent: "SingleValuePickerView", placeholder: str) -> None:
        self.parent_view = parent
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=option.label[:100],
                    value=option.value,
                    description=option.description[:100] or None,
                    default=option.default,
                )
                for option in parent.options
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        message = await self.parent_view.apply(self.values[0])
        await interaction.response.send_message(message, ephemeral=True)


class SingleValuePickerView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        placeholder: str,
        options: Sequence[SingleSelectOption],
        apply_value: Callable[[str], Awaitable[str]],
        timeout: float = 300.0,
    ) -> None:
        super().__init__(invoker_id=invoker_id, timeout=timeout)
        self.options = list(options)
        self.apply = apply_value
        self.add_item(_SingleValueSelect(self, placeholder))
