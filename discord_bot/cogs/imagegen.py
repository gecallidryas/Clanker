from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import get_guild_config
from utils.tool_context import ToolContext
from utils.tool_registry import get_tool, is_tool_enabled, register_builtin_tools
from utils.image_generation import tool_generate_image
from utils.i18n import get_locale_from_interaction, t


class ImageGen(commands.Cog):
    generate_group = app_commands.Group(name="generate", description="Generate media")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        register_builtin_tools()

    @generate_group.command(name="image", description="Generate an image from a prompt.")
    @app_commands.describe(prompt="Describe the image you want")
    async def generate_image_slash(self, interaction: discord.Interaction, prompt: str):
        if not interaction.guild:
            await interaction.response.send_message(
                t("common.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return

        config = await get_guild_config(interaction.guild.id)
        tool = get_tool("generate_image") or tool_generate_image
        if tool and not is_tool_enabled(tool, config):
            await interaction.response.send_message(
                t("imagegen.disabled", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        context = ToolContext(
            bot=self.bot,
            guild=interaction.guild,
            channel=interaction.channel,
            user=interaction.user,
            message=None,
            guild_config=config,
            locale=get_locale_from_interaction(interaction),
        )
        result = await tool.handler(context, {"prompt": prompt})
        if not result.ok:
            await interaction.followup.send(result.summary, ephemeral=True)
            return
        await interaction.followup.send(
            t("imagegen.generated", get_locale_from_interaction(interaction)),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ImageGen(bot))
