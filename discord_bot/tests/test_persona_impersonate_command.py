import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cogs.persona import Persona
from utils.persona_impersonation import CollectedMemberMessages, ImpersonationPayload


class PersonaImpersonateCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_impersonate_requires_manage_guild(self) -> None:
        cog = Persona(bot=SimpleNamespace())
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=123, text_channels=[]),
            user=SimpleNamespace(id=1, guild_permissions=SimpleNamespace(manage_guild=False)),
            response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        member = SimpleNamespace(id=2, display_name="Target", bot=False)

        await cog.impersonate_persona.callback(cog, interaction, member, None)

        interaction.response.send_message.assert_awaited_once()
        interaction.response.defer.assert_not_awaited()
        interaction.followup.send.assert_not_awaited()

    async def test_impersonate_rejects_when_filtered_messages_too_low(self) -> None:
        cog = Persona(bot=SimpleNamespace())
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=123, text_channels=[SimpleNamespace()]),
            user=SimpleNamespace(id=1, guild_permissions=SimpleNamespace(manage_guild=True)),
            response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        member = SimpleNamespace(id=2, display_name="Target", bot=False)

        with patch(
            "cogs.persona.collect_member_messages",
            AsyncMock(
                return_value=CollectedMemberMessages(
                    raw_count=150,
                    usable_count=99,
                    raw_messages=["x"] * 150,
                    usable_messages=["y"] * 99,
                )
            ),
        ):
            await cog.impersonate_persona.callback(cog, interaction, member, None)

        interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        interaction.followup.send.assert_awaited_once()

    async def test_impersonate_creates_inactive_custom_persona(self) -> None:
        cog = Persona(bot=SimpleNamespace())
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=123, text_channels=[SimpleNamespace()]),
            user=SimpleNamespace(id=1, guild_permissions=SimpleNamespace(manage_guild=True)),
            response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        member = SimpleNamespace(id=2, display_name="Target", bot=False)

        payload = ImpersonationPayload(
            bio="bio",
            aliases=["target"],
            normal_prompt="normal prompt",
            evil_prompt="evil prompt",
            sample_dialogues=["one", "two"],
        )

        with patch(
            "cogs.persona.collect_member_messages",
            AsyncMock(
                return_value=CollectedMemberMessages(
                    raw_count=180,
                    usable_count=120,
                    raw_messages=["raw"] * 180,
                    usable_messages=["usable"] * 120,
                )
            ),
        ), patch(
            "cogs.persona.generate_guild_gemini_profile_text",
            AsyncMock(return_value=('{"bio":"bio","normal_prompt":"normal prompt","evil_prompt":"evil prompt","aliases":["target"],"sample_dialogues":["one","two"]}', "gemini")),
        ), patch(
            "cogs.persona.parse_impersonation_payload",
            return_value=payload,
        ), patch(
            "cogs.persona.get_guild_custom_personas",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.persona.choose_unique_persona_name",
            return_value="Target",
        ), patch(
            "cogs.persona.copy_member_avatar",
            AsyncMock(return_value=("/tmp/avatar.webp", None)),
        ), patch(
            "cogs.persona.create_custom_persona",
            AsyncMock(return_value=1),
        ) as create_persona, patch(
            "cogs.persona.upsert_persona_traits",
            AsyncMock(return_value=None),
        ):
            await cog.impersonate_persona.callback(cog, interaction, member, None)

        create_persona.assert_awaited_once()
        kwargs = create_persona.await_args.kwargs
        self.assertEqual(kwargs["guild_id"], 123)
        self.assertEqual(kwargs["name"], "Target")
        self.assertEqual(kwargs["avatar_path"], "/tmp/avatar.webp")
        self.assertEqual(kwargs["sample_dialogues_json"], json.dumps(["one", "two"]))
        interaction.followup.send.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
