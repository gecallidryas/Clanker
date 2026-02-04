from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import get_guild_config
from utils.tool_context import ToolContext
from utils.tool_registry import get_tool, is_tool_enabled, register_builtin_tools
from utils.image_generation import tool_generate_image


class ImageGen(commands.Cog):
    generate_group = app_commands.Group(name="generate", description="Generate media")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        register_builtin_tools()

    @generate_group.command(name="image", description="Generate an image from a prompt.")
    @app_commands.describe(prompt="Describe the image you want")
    async def generate_image_slash(self, interaction: discord.Interaction, prompt: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        config = await get_guild_config(interaction.guild.id)
        tool = get_tool("generate_image") or tool_generate_image
        if tool and not is_tool_enabled(tool, config):
            await interaction.response.send_message("Image generation is disabled for this server.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        context = ToolContext(
            bot=self.bot,
            guild=interaction.guild,
            channel=interaction.channel,
            user=interaction.user,
            message=None,
            guild_config=config,
            locale=str(interaction.locale) if interaction.locale else "en",
        )
        result = await tool.handler(context, {"prompt": prompt})
        if not result.ok:
            await interaction.followup.send(result.summary, ephemeral=True)
            return
        await interaction.followup.send("Image generated.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ImageGen(bot))
