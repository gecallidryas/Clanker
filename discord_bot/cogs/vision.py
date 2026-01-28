"""
Vision Cog for Femmy Discord Bot
=================================
Image analysis using Gemini Pro Vision.

Features:
    - Check for image attachments FIRST before processing
    - Incorporate message text context into image analysis
    - Describe image contents in character
    - Extract text from images (OCR)

Usage:
    @Femmy [attach image] - Analyze the attached image
    @Femmy what's in this image? [attach image]
"""

from io import BytesIO
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from utils.db_handler import get_server_mode, increment_stat
from utils.api_manager import UserInputError
from utils.guild_ai import generate_guild_gemini_vision, GuildConfigError
from utils.rate_limiter import ai_limiter, get_rate_limit_message
from utils.logger import get_logger


# Gemini Vision model
VISION_MODEL = "gemini-pro-vision"

# Supported image formats
SUPPORTED_FORMATS = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

logger = get_logger(__name__)


class Vision(commands.Cog):
    """
    Vision Cog - Image analysis with Gemini Vision.
    
    Features:
        - Multi-modal AI responses
        - Persona-aware image descriptions
        - OCR capabilities
        
    TODO:
        - [ ] Add image editing commands
        - [ ] Implement image comparison
        - [ ] Add NSFW detection
        - [ ] Support multiple images per message
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def analyze_image(
        self,
        guild_id: int,
        image_bytes: bytes,
        user_message: str,
        persona_mode: str,
        username: str = "User",
    ) -> str:
        """
        Analyze an image using Gemini Vision with full message context.
        
        Args:
            guild_id: Discord guild/server ID
            image_bytes: Raw image data
            user_message: The FULL message text from the user (for context)
            persona_mode: Current bot personality mode
            username: The user's display name
            
        Returns:
            AI-generated description/analysis
        """
        try:
            # Load image
            image = Image.open(BytesIO(image_bytes))
            
            # Build persona-aware prompt
            persona_intros = {
                "mode_femboy": "You are Femmy, a cute, helpful femboy assistant. Respond enthusiastically with occasional cute expressions and emojis~ ♡ Call the user Nii-chan or Onee-chan.",
                "mode_tsundere": "You are Femmy, a tsundere sister. Be helpful but act like you didn't want to help. Use phrases like 'Baka!' and 'It's not like I'm helping you or anything!' Reluctantly describe what you see.",
                "mode_oneesan": "You are Femmy, a caring older sister with Ara Ara energy. Be warm, nurturing, and use 'Ara ara~' occasionally. Be thorough and supportive in your analysis."
            }
            
            persona_intro = persona_intros.get(persona_mode, persona_intros["mode_femboy"])
            
            # Determine what the user is asking about the image
            if user_message.strip():
                context_section = f"""
The user ({username}) shared this image with the message: "{user_message}"

Pay attention to what they said - if they asked a specific question about the image, answer it.
If they made a comment, respond appropriately to both the image and their comment.
"""
            else:
                context_section = f"""
The user ({username}) shared this image without any specific question.
Provide a helpful, detailed description of what you see.
"""
            
            full_prompt = f"""
{persona_intro}
{context_section}
Analyze the image and respond in character. Be helpful and engaging.
"""
            
            # Generate response with multi-key failover
            try:
                response_text, _ = await generate_guild_gemini_vision(guild_id, full_prompt, image)
                try:
                    await increment_stat("images_analyzed")
                except Exception as e:
                    logger.warning("Failed to increment images_analyzed: %s", e)
                return response_text
            except UserInputError:
                return "Sorry, I can't help with that image request."
            except GuildConfigError:
                return (
                    "This server hasn't configured Gemini keys yet. "
                    "Ask an admin to upload keys with /config env upload."
                )
            except RuntimeError as e:
                logger.warning("All vision API keys exhausted: %s", e)
                return "I'm a bit overwhelmed right now... Please try again later! >.< "
            
        except Exception as e:
            logger.error("Vision processing error: %s", e, exc_info=True)
            return "I couldn't analyze that image... Maybe try a different one? >.< "
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for messages with image attachments when mentioned.
        IMPORTANT: Check for image attachments FIRST before doing any processing.
        """
        # Auto vision context handling lives in AIBrain to avoid double replies.
        return
        # Ignore bots
        if message.author.bot:
            return
        
        # ============================================
        # STEP 1: Check for image attachments FIRST
        # ============================================
        if not message.attachments:
            return  # No attachments, exit early
        
        # Find first valid image attachment
        image_attachment: Optional[discord.Attachment] = None
        for attachment in message.attachments:
            # Check content_type exists and is a supported image format
            if attachment.content_type and attachment.content_type in SUPPORTED_FORMATS:
                if attachment.size <= MAX_IMAGE_SIZE:
                    image_attachment = attachment
                    break
        
        # No valid image found, exit early
        if not image_attachment:
            return
        
        # ============================================
        # STEP 2: Now check if bot was mentioned
        # ============================================
        if self.bot.user not in message.mentions:
            return

        # Get server mode (used for rate limiting and response)
        mode = "mode_femboy"
        if message.guild:
            mode = await get_server_mode(message.guild.id)

        # Rate limit image analysis per user
        if not await ai_limiter.acquire(message.author.id):
            retry_after = ai_limiter.get_retry_after(message.author.id)
            await message.reply(
                get_rate_limit_message(mode, retry_after),
                mention_author=False
            )
            return
        
        # ============================================
        # STEP 3: Process the image with full message context
        # ============================================
        
        # Extract the FULL user message (remove bot mention for cleaner context)
        user_message = message.content
        user_message = user_message.replace(f"<@{self.bot.user.id}>", "").strip()
        user_message = user_message.replace(f"<@!{self.bot.user.id}>", "").strip()
        
        async with message.channel.typing():
            # Download image
            try:
                image_bytes = await image_attachment.read()
            except Exception as e:
                await message.reply("Couldn't download the image... >.< ")
                return
            
            # Analyze image with full message context
            response = await self.analyze_image(
                message.guild.id,
                image_bytes,
                user_message,
                mode,
                message.author.display_name,
            )
        
        await message.reply(response, mention_author=False)
    
    @commands.command(name="describe", aliases=["analyze", "whatis"])
    async def describe_image(self, ctx: commands.Context, *, prompt: str = None):
        """
        Analyze an attached or replied-to image.
        
        Args:
            prompt: Optional question about the image
            
        TODO:
            - [ ] Support image URLs as argument
        """
        # Check for attachment in current message
        attachment = None
        if ctx.message.attachments:
            for att in ctx.message.attachments:
                if att.content_type in SUPPORTED_FORMATS:
                    attachment = att
                    break
        
        # Check for replied message with attachment
        if not attachment and ctx.message.reference:
            try:
                replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if replied_msg.attachments:
                    for att in replied_msg.attachments:
                        if att.content_type in SUPPORTED_FORMATS:
                            attachment = att
                            break
            except:
                pass
        
        if not attachment:
            await ctx.send(
                "❌ Please attach an image or reply to a message with an image!\n"
                "Usage: `!describe [question]` with an attached image"
            )
            return
        
        if attachment.size > MAX_IMAGE_SIZE:
            await ctx.send("❌ Image too large! Maximum size is 10 MB.")
            return
        
        # Get server mode
        mode = await get_server_mode(ctx.guild.id) if ctx.guild else "mode_femboy"

        # Rate limit image analysis per user
        if not await ai_limiter.acquire(ctx.author.id):
            retry_after = ai_limiter.get_retry_after(ctx.author.id)
            await ctx.send(get_rate_limit_message(mode, retry_after))
            return
        
        async with ctx.typing():
            image_bytes = await attachment.read()
            response = await self.analyze_image(
                ctx.guild.id,
                image_bytes,
                prompt or "",
                mode,
                ctx.author.display_name,
            )
        
        # Build embed
        embed = discord.Embed(
            title="🖼️ Image Analysis",
            description=response,
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=attachment.url)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="describe", description="Describe an attached image.")
    @app_commands.describe(prompt="Optional question about the image", image="Image attachment")
    async def describe_image_slash(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        prompt: str = None
    ):
        if image.content_type not in SUPPORTED_FORMATS:
            await interaction.response.send_message("Unsupported image format.", ephemeral=True)
            return
        if image.size > MAX_IMAGE_SIZE:
            await interaction.response.send_message("Image too large! Maximum size is 10 MB.", ephemeral=True)
            return

        mode = await get_server_mode(interaction.guild.id) if interaction.guild else "mode_femboy"
        if not await ai_limiter.acquire(interaction.user.id):
            retry_after = ai_limiter.get_retry_after(interaction.user.id)
            await interaction.response.send_message(get_rate_limit_message(mode, retry_after), ephemeral=True)
            return

        await interaction.response.defer()
        image_bytes = await image.read()
        response = await self.analyze_image(
            interaction.guild.id,
            image_bytes,
            prompt or "",
            mode,
            interaction.user.display_name,
        )

        embed = discord.Embed(
            title="Image Analysis",
            description=response,
            color=discord.Color.purple(),
        )
        embed.set_thumbnail(url=image.url)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Load the Vision cog."""
    await bot.add_cog(Vision(bot))
