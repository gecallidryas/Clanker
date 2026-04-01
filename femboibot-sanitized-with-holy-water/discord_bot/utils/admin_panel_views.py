from __future__ import annotations

from typing import Any, Awaitable, Callable, Sequence

import discord

from utils.admin_panel_logic import paginate_sequence


AsyncTextCallback = Callable[[discord.Interaction], Awaitable[str]]
AsyncRemoveCallback = Callable[[list[str]], Awaitable[None]]
AsyncClearCallback = Callable[[], Awaitable[None]]
AsyncBoolCallback = Callable[[], Awaitable[bool]]
AsyncAuthSubmitter = Callable[[str], Awaitable[bool]]


class AdminPanelView(discord.ui.View):
    def __init__(
        self,
        *,
        user_id: int,
        timeout: float = 300,
        timeout_message: str = "This panel expired. Re-run the command to open a fresh panel.",
    ) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.timeout_message = timeout_message
        self._message: Any = None

    def bind_message(self, message: Any) -> None:
        self._message = message

    def add_timeout_button(self, label: str) -> discord.ui.Button:
        button = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary)
        self.add_item(button)
        return button

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the original admin can use this panel. Open your own panel instead.",
                ephemeral=True,
            )
            return False
        return True

    def disable_all_items(self) -> None:
        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if self._message is not None:
            await self._message.edit(content=self.timeout_message, view=self)


class SaveCancelView(AdminPanelView):
    def __init__(
        self,
        *,
        user_id: int,
        on_save: AsyncTextCallback,
        on_cancel: AsyncTextCallback,
        timeout: float = 300,
    ) -> None:
        super().__init__(user_id=user_id, timeout=timeout)
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._finished = False

    async def _finish(
        self,
        interaction: discord.Interaction,
        callback: AsyncTextCallback,
    ) -> None:
        if self._finished:
            await interaction.response.send_message("This panel is already closed.", ephemeral=True)
            return
        self._finished = True
        self.disable_all_items()
        message = await callback(interaction)
        await interaction.response.edit_message(content=message, view=self)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._finish(interaction, self._on_save)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._finish(interaction, self._on_cancel)


class _PagedItemSelect(discord.ui.Select):
    def __init__(self, parent: "PagedItemEditorView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Select entries on this page",
            min_values=0,
            max_values=1,
            options=[discord.SelectOption(label="Nothing to remove", value="__empty__", default=True)],
            disabled=True,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values == ["__empty__"]:
            self.parent_view.selected_values = []
        else:
            self.parent_view.selected_values = list(self.values)
        await interaction.response.edit_message(view=self.parent_view)


class PagedItemEditorView(AdminPanelView):
    def __init__(
        self,
        *,
        user_id: int,
        items: Sequence[str],
        page_size: int,
        on_remove: AsyncRemoveCallback,
        on_clear: AsyncClearCallback,
        timeout: float = 300,
        auth_checker: AsyncBoolCallback | None = None,
        auth_required_message: str = "Authentication required before completing this action.",
        remove_requires_auth: bool = False,
        clear_requires_auth: bool = False,
    ) -> None:
        super().__init__(user_id=user_id, timeout=timeout)
        self.items = list(items)
        self.page_size = page_size
        self.page = 1
        self.selected_values: list[str] = []
        self._on_remove = on_remove
        self._on_clear = on_clear
        self._auth_checker = auth_checker
        self._auth_required_message = auth_required_message
        self._remove_requires_auth = remove_requires_auth
        self._clear_requires_auth = clear_requires_auth

        self.select = _PagedItemSelect(self)
        self.add_item(self.select)
        self._rebuild()

    async def _check_auth(self, interaction: discord.Interaction, *, required: bool) -> bool:
        if not required:
            return True
        if self._auth_checker is None:
            return False
        if await self._auth_checker():
            return True
        await interaction.response.send_message(self._auth_required_message, ephemeral=True)
        return False

    def _page_slice(self) -> list[str]:
        return paginate_sequence(self.items, page=self.page, page_size=self.page_size).items

    def _rebuild(self) -> None:
        page = paginate_sequence(self.items, page=self.page, page_size=self.page_size)
        self.page = page.page
        page_items = page.items
        if not page_items:
            self.selected_values = []
            self.select.options = [
                discord.SelectOption(label="Nothing to remove", value="__empty__", default=True)
            ]
            self.select.disabled = True
            self.select.max_values = 1
            return

        self.select.options = [
            discord.SelectOption(label=item[:100], value=item, default=item in self.selected_values)
            for item in page_items
        ]
        self.select.disabled = False
        self.select.max_values = len(page_items)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = max(1, self.page - 1)
        self.selected_values = []
        self._rebuild()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        total_pages = paginate_sequence(self.items, page=self.page, page_size=self.page_size).total_pages
        self.page = min(total_pages, self.page + 1)
        self.selected_values = []
        self._rebuild()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Remove Selected", style=discord.ButtonStyle.danger)
    async def remove_selected_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_auth(interaction, required=self._remove_requires_auth):
            return
        values = list(self.selected_values)
        await self._on_remove(values)
        self.items = [item for item in self.items if item not in values]
        self.selected_values = []
        self._rebuild()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Clear All", style=discord.ButtonStyle.danger)
    async def clear_all_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_auth(interaction, required=self._clear_requires_auth):
            return
        await self._on_clear()
        self.items = []
        self.page = 1
        self.selected_values = []
        self._rebuild()
        await interaction.response.edit_message(view=self)


class PasswordAuthModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        auth_submitter: AsyncAuthSubmitter,
        modal_factory: Callable[[], discord.ui.Modal],
    ) -> None:
        super().__init__(title="Authenticate")
        self._auth_submitter = auth_submitter
        self._modal_factory = modal_factory
        self.password = discord.ui.TextInput(
            label="Config password",
            style=discord.TextStyle.short,
            required=True,
        )
        self.add_item(self.password)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self._auth_submitter(self.password.value):
            await interaction.response.send_message("Authentication failed.", ephemeral=True)
            return
        await interaction.response.send_modal(self._modal_factory())


class AuthHandoffView(AdminPanelView):
    def __init__(
        self,
        *,
        user_id: int,
        auth_checker: AsyncBoolCallback,
        auth_submitter: AsyncAuthSubmitter,
        modal_factory: Callable[[], discord.ui.Modal],
        auth_required_message: str,
        timeout: float = 300,
    ) -> None:
        super().__init__(user_id=user_id, timeout=timeout)
        self._auth_checker = auth_checker
        self._auth_submitter = auth_submitter
        self._modal_factory = modal_factory
        self._auth_required_message = auth_required_message

    def auth_modal_factory(self) -> PasswordAuthModal:
        return PasswordAuthModal(
            auth_submitter=self._auth_submitter,
            modal_factory=self._modal_factory,
        )

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if await self._auth_checker():
            await interaction.response.send_modal(self._modal_factory())
            return
        await interaction.response.send_message(self._auth_required_message, ephemeral=True)


class AdminPanelViewBase(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        timeout: float = 300,
        timeout_message: str = "This admin panel expired. Reopen it to continue.",
    ) -> None:
        super().__init__(
            user_id=invoker_id,
            timeout=timeout,
            timeout_message=timeout_message,
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the original admin can use this panel.",
                ephemeral=True,
            )
            return False
        return True


class PostAuthActionView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        launch_label: str,
        modal_factory: Callable[[], Any],
        timeout: float = 300,
    ) -> None:
        super().__init__(
            user_id=invoker_id,
            timeout=timeout,
            timeout_message="This admin panel expired. Reopen it to continue.",
        )
        self.launch_label = launch_label
        self._modal_factory = modal_factory

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.launch(interaction)

    async def launch(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(self._modal_factory())


class ConfigAuthModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        invoker_id: int,
        service: Any,
        launch_label: str,
        modal_factory: Callable[[], Any],
    ) -> None:
        super().__init__(title="Authenticate")
        self.invoker_id = invoker_id
        self.service = service
        self.launch_label = launch_label
        self._modal_factory = modal_factory
        self.password_input = discord.ui.TextInput(
            label="Config password",
            style=discord.TextStyle.short,
            required=True,
        )
        self.add_item(self.password_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        ok = await self.service.verify_password(
            interaction.guild.id,
            interaction.user.id,
            self.password_input.value,
        )
        if not ok:
            await interaction.response.send_message("Authentication failed.", ephemeral=True)
            return
        handoff = PostAuthActionView(
            invoker_id=self.invoker_id,
            launch_label=self.launch_label,
            modal_factory=self._modal_factory,
        )
        await interaction.response.send_message(
            content="Authenticated. Continue to the protected editor.",
            view=handoff,
            ephemeral=True,
        )


class AuthRequiredView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        title: str,
        service: Any,
        launch_label: str,
        modal_factory: Callable[[], Any],
        timeout: float = 300,
    ) -> None:
        super().__init__(
            user_id=invoker_id,
            timeout=timeout,
            timeout_message="This admin panel expired. Reopen it to continue.",
        )
        self.title = title
        self.service = service
        self.launch_label = launch_label
        self._modal_factory = modal_factory

    @discord.ui.button(label="Authenticate", style=discord.ButtonStyle.primary)
    async def authenticate_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.authenticate(interaction)

    async def authenticate(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            ConfigAuthModal(
                invoker_id=self.user_id,
                service=self.service,
                launch_label=self.launch_label,
                modal_factory=self._modal_factory,
            )
        )


class PaginatedListView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        items: Sequence[str],
        page_size: int,
        on_remove: Callable[[list[str]], Awaitable[str]],
        on_clear: Callable[[], Awaitable[str]],
        clear_requires_auth: bool = False,
        auth_factory: Callable[[], AdminPanelView] | None = None,
        timeout: float = 300,
    ) -> None:
        super().__init__(
            user_id=invoker_id,
            timeout=timeout,
            timeout_message="This admin panel expired. Reopen it to continue.",
        )
        self.items = list(items)
        self.page_size = page_size
        self.page = 1
        self.selected_values: list[str] = []
        self._on_remove = on_remove
        self._on_clear = on_clear
        self._clear_requires_auth = clear_requires_auth
        self._auth_factory = auth_factory

    async def next_page(self, interaction: discord.Interaction) -> None:
        total_pages = paginate_sequence(self.items, page=self.page, page_size=self.page_size).total_pages
        self.page = min(total_pages, self.page + 1)
        await interaction.response.edit_message(view=self)

    async def previous_page(self, interaction: discord.Interaction) -> None:
        self.page = max(1, self.page - 1)
        await interaction.response.edit_message(view=self)

    async def remove_selected(self, interaction: discord.Interaction) -> None:
        removed = list(self.selected_values)
        if not removed:
            await interaction.response.send_message("Select at least one entry to remove.", ephemeral=True)
            return
        self.items = [item for item in self.items if item not in removed]
        self.selected_values = []
        result = await self._on_remove(removed)
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(result, ephemeral=True)

    async def clear_all(self, interaction: discord.Interaction) -> None:
        if self._clear_requires_auth and self._auth_factory is not None:
            await interaction.response.send_message(
                content="Authentication required before clearing everything.",
                view=self._auth_factory(),
                ephemeral=True,
            )
            return
        self.items = []
        self.page = 1
        result = await self._on_clear()
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(result, ephemeral=True)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.previous_page(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.next_page(interaction)

    @discord.ui.button(label="Remove Selected", style=discord.ButtonStyle.danger)
    async def remove_selected_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.remove_selected(interaction)

    @discord.ui.button(label="Clear All", style=discord.ButtonStyle.danger)
    async def clear_all_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.clear_all(interaction)
