from __future__ import annotations

import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import (
    add_persona_attribute,
    add_sample_dialogue,
    set_personal_memory_opt_out,
    get_guild_config,
)
from utils.rag_documents import extract_text_from_bytes
from utils.rag_store import store_document
from utils.i18n import get_locale_from_interaction, t
from utils.memory_limits import (
    get_memory_limit_error_message,
    validate_attribute_content,
    validate_document_text,
    validate_sample_dialogue_content,
)


class Teach(commands.Cog):
    teach_group = app_commands.Group(name="teach", description="Teach the bot new knowledge")
    personal_group = app_commands.Group(name="personal", description="Personal settings")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @teach_group.command(name="attribute", description="Teach a persona attribute.")
    @app_commands.describe(attribute="Attribute name", value="Attribute value")
    async def teach_attribute(self, interaction: discord.Interaction, attribute: str, value: str):
        if not interaction.guild:
            await interaction.response.send_message(
                t("common.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server to add attributes.", ephemeral=True)
            return
        attr_validation = validate_attribute_content(attribute.strip())
        if not attr_validation.is_valid:
            await interaction.response.send_message(
                get_memory_limit_error_message(attr_validation),
                ephemeral=True,
            )
            return
        value_validation = validate_attribute_content(value.strip())
        if not value_validation.is_valid:
            await interaction.response.send_message(
                get_memory_limit_error_message(value_validation),
                ephemeral=True,
            )
            return
        await add_persona_attribute(interaction.guild.id, attribute.strip(), value.strip(), interaction.user.id)
        locale = get_locale_from_interaction(interaction)
        await interaction.response.send_message(t("teach.attribute.saved", locale), ephemeral=True)

    @teach_group.command(name="sampledialogue", description="Teach a sample dialogue line.")
    @app_commands.describe(speaker="Speaker name", dialogue="Dialogue line")
    async def teach_sampledialogue(self, interaction: discord.Interaction, speaker: str, dialogue: str):
        if not interaction.guild:
            await interaction.response.send_message(
                t("common.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server to add sample dialogues.", ephemeral=True)
            return
        speaker_validation = validate_attribute_content(speaker.strip())
        if not speaker_validation.is_valid:
            await interaction.response.send_message(
                get_memory_limit_error_message(speaker_validation),
                ephemeral=True,
            )
            return
        dialogue_validation = validate_sample_dialogue_content(dialogue.strip())
        if not dialogue_validation.is_valid:
            await interaction.response.send_message(
                get_memory_limit_error_message(dialogue_validation),
                ephemeral=True,
            )
            return
        await add_sample_dialogue(interaction.guild.id, speaker.strip(), dialogue.strip(), interaction.user.id)
        locale = get_locale_from_interaction(interaction)
        await interaction.response.send_message(t("teach.sampledialogue.saved", locale), ephemeral=True)

    @teach_group.command(name="document", description="Upload a document for RAG memory.")
    @app_commands.describe(file="Text, markdown, or PDF file", title="Optional title")
    async def teach_document(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        title: Optional[str] = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                t("common.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server to add documents.", ephemeral=True)
            return
        config = await get_guild_config(interaction.guild.id)
        rag_enabled = bool(config.get("rag_enabled") or 0)
        if not rag_enabled or str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() not in {"1", "true", "yes", "on"}:
            await interaction.response.send_message("RAG is disabled for this server.", ephemeral=True)
            return

        if file.size > 8 * 1024 * 1024:
            await interaction.response.send_message("File too large (max 8 MB).", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        data = await file.read()
        text = extract_text_from_bytes(data, file.filename)
        if not text:
            await interaction.followup.send("Unsupported file type. Use .txt, .md, or .pdf.", ephemeral=True)
            return
        text_validation = validate_document_text(text)
        if not text_validation.is_valid:
            await interaction.followup.send(
                get_memory_limit_error_message(text_validation),
                ephemeral=True,
            )
            return
        doc_title = title or file.filename
        try:
            doc_id, chunk_count = await store_document(
                interaction.guild.id,
                doc_title,
                source=file.filename,
                text=text,
                uploader_id=interaction.user.id,
                metadata={"filename": file.filename},
            )
        except Exception as exc:
            await interaction.followup.send(f"Failed to store document: {exc}", ephemeral=True)
            return

        locale = get_locale_from_interaction(interaction)
        await interaction.followup.send(
            t("teach.document.saved", locale, doc_id=doc_id, chunks=chunk_count),
            ephemeral=True,
        )

    @personal_group.command(name="privacy", description="Opt in or out of personal memory.")
    @app_commands.describe(state="on/off (on = opt out)")
    async def personal_privacy(self, interaction: discord.Interaction, state: Optional[str] = None):
        if not interaction.guild:
            await interaction.response.send_message(
                t("common.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return
        if not state:
            await interaction.response.send_message(
                "Use `on` to opt out of personal memory, `off` to opt back in.",
                ephemeral=True,
            )
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_personal_memory_opt_out(interaction.guild.id, interaction.user.id, True)
            locale = get_locale_from_interaction(interaction)
            await interaction.response.send_message(t("personal.privacy.on", locale), ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await set_personal_memory_opt_out(interaction.guild.id, interaction.user.id, False)
            locale = get_locale_from_interaction(interaction)
            await interaction.response.send_message(t("personal.privacy.off", locale), ephemeral=True)
        else:
            await interaction.response.send_message("Use `on` or `off`.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Teach(bot))
