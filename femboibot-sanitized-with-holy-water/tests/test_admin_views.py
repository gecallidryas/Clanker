import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import discord

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from tests.helpers.discord_fakes import FakeInteraction, FakeMessage  # noqa: E402
from utils.admin_views import AdminPanelView, AuthPromptView, PasswordAuthModal  # noqa: E402


def test_admin_view_rejects_non_invoker():
    async def _run():
        view = AdminPanelView(invoker_id=10, timeout_message="Expired.")
        interaction = FakeInteraction(user_id=99)
        allowed = await view.interaction_check(interaction)

        assert allowed is False
        assert interaction.response.messages[0]["ephemeral"] is True
        assert "original admin" in interaction.response.messages[0]["content"].lower()

    asyncio.run(_run())


def test_admin_view_disables_controls_on_timeout():
    async def _run():
        view = AdminPanelView(invoker_id=10, timeout_message="Expired.")
        button = discord.ui.Button(label="Test")
        view.add_item(button)
        message = FakeMessage()
        view.bind_message(message)

        await view.on_timeout()

        assert button.disabled is True
        assert len(message.edits) == 1
        kwargs = message.edits[0]
        assert kwargs["content"] == "Expired."
        assert kwargs["view"] is view

    asyncio.run(_run())


def test_auth_prompt_opens_password_modal():
    async def _run():
        view = AuthPromptView(
            invoker_id=10,
            title="Authenticate",
            on_submit=AsyncMock(),
        )
        interaction = FakeInteraction(user_id=10)

        await view.open_auth_modal(interaction)

        modal = interaction.response.modal
        assert isinstance(modal, PasswordAuthModal)

    asyncio.run(_run())


def test_password_auth_modal_calls_submit_callback():
    async def _run():
        submit_mock = AsyncMock()
        modal = PasswordAuthModal(title="Authenticate", on_submit=submit_mock)
        modal.password.default = "secret"
        interaction = FakeInteraction(user_id=10)

        await modal.on_submit(interaction)

        submit_mock.assert_awaited_once_with(interaction, "secret")

    asyncio.run(_run())
