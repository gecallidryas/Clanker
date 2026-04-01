from __future__ import annotations

from typing import Awaitable, Callable

import discord


class AdminPanelView(discord.ui.View):
    def __init__(
        self,
        *,
        invoker_id: int,
        timeout: float = 300.0,
        timeout_message: str = "This panel expired. Reopen it to continue.",
    ) -> None:
        super().__init__(timeout=timeout)
        self.invoker_id = invoker_id
        self.timeout_message = timeout_message
        self._bound_message: discord.Message | None = None

    def bind_message(self, message: discord.Message) -> None:
        self._bound_message = message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original admin can use this panel. Open your own panel instead.",
                ephemeral=True,
            )
            return False
        return True

    def disable_all_items(self) -> None:
        for child in self.children:
            child.disabled = True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if self._bound_message is not None:
            await self._bound_message.edit(content=self.timeout_message, view=self)


class PasswordAuthModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str,
        on_submit: Callable[[discord.Interaction, str], Awaitable[None]],
    ) -> None:
        super().__init__(title=title[:45])
        self._on_submit = on_submit
        self.password = discord.ui.TextInput(
            label="Config password",
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.password)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._on_submit(interaction, str(self.password.default or self.password.value or ""))


class AuthPromptView(AdminPanelView):
    def __init__(
        self,
        *,
        invoker_id: int,
        title: str,
        on_submit: Callable[[discord.Interaction, str], Awaitable[None]],
        timeout: float = 180.0,
    ) -> None:
        super().__init__(invoker_id=invoker_id, timeout=timeout)
        self.title = title
        self.on_submit = on_submit

    async def open_auth_modal(self, interaction: discord.Interaction) -> None:
        modal = PasswordAuthModal(title=self.title, on_submit=self.on_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Authenticate", style=discord.ButtonStyle.primary)
    async def authenticate_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.open_auth_modal(interaction)
