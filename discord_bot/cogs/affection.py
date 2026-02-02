"""
Affection & Mood Cog for Femmy Discord Bot
============================================
Tracks user affection levels and bot mood per server.

Affection Levels:
    - stranger (0-49)
    - acquaintance (50-199)
    - friend (200-499)
    - close_friend (500-999)
    - beloved (1000+)

Mood States:
    - happy (70-100)
    - neutral (40-69)
    - sad (20-39)
    - neglected (0-19)

Commands:
    !affection       - View your affection level
    !mood            - Check bot's current mood
    !headpat         - Give headpats
    !hug             - Give hugs
"""

import random
import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.db_handler import (
    get_all_mode_affection,
    add_affection_to_mode,
    get_mood,
    update_mood,
    get_server_mode,
    check_interaction_limit,
    record_interaction,
    AFFECTION_TRACKED_MODES,
)
from utils.sentiment import analyze_sentiment, quick_sentiment_check
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================
# Negative Reaction Responses
# ============================================

NEGATIVE_REACTIONS = {
    "mode_femboy": {
        "negative": "*flinches* N-Nii-chan, that hurt my feelings... >.<",
        "very_negative": "*tears up* W-why are you being so mean...? I just wanted to help... 😢",
        "hostile": "*runs away crying* I-I'll leave you alone then... 💔"
    },
    "mode_tsundere": {
        "negative": "Tch! Whatever, see if I care! *turns away* Baka!",
        "very_negative": "*glares* You think you can talk to me like that?! Hmph, the nerve!",
        "hostile": "Fine! I don't need this! You're the worst! *storms off*"
    },
    "mode_oneesan": {
        "negative": "Ara... that wasn't very kind, was it? *sighs softly*",
        "very_negative": "My dear, I'm disappointed. Is something troubling you?",
        "hostile": "*looks hurt* I... I see. Perhaps you need some space, little one."
    }
}

# Affection-based behavior modifiers
AFFECTION_PROMPTS = {
    "stranger": "This user is new to you. Be polite but reserved. Keep some distance.",
    "acquaintance": "You're getting to know this user. Be friendly but not overly familiar.",
    "friend": "This is a good friend! Be casual, use their name, share jokes.",
    "close_friend": "You're very close! Be affectionate, playful, remember details about them.",
    "beloved": "This is your favorite person! Show deep care, attachment, and protectiveness."
}


# ============================================
# Affection Level Display
# ============================================

AFFECTION_DISPLAY = {
    "stranger": {"emoji": "👤", "title": "Stranger", "color": 0x808080},
    "acquaintance": {"emoji": "🤝", "title": "Acquaintance", "color": 0x3498db},
    "friend": {"emoji": "😊", "title": "Friend", "color": 0x2ecc71},
    "close_friend": {"emoji": "💕", "title": "Close Friend", "color": 0xe91e63},
    "beloved": {"emoji": "💖", "title": "Beloved", "color": 0xff69b4},
}

MODE_AFFECTION_DISPLAY = {
    "mode_femboy": {"emoji": "🎀", "name": "Femboy Mode"},
    "mode_tsundere": {"emoji": "💢", "name": "Tsundere Mode"},
    "mode_oneesan": {"emoji": "💋", "name": "Oneesan Mode"},
}

AFFECTION_THRESHOLDS = [
    (0, 50, "stranger"),
    (50, 200, "acquaintance"),
    (200, 500, "friend"),
    (500, 1000, "close_friend"),
    (1000, float("inf"), "beloved"),
]


# ============================================
# Mood Display
# ============================================

MOOD_DISPLAY = {
    "happy": {"emoji": "😊", "color": 0x2ecc71},
    "neutral": {"emoji": "😐", "color": 0x95a5a6},
    "sad": {"emoji": "😔", "color": 0x3498db},
    "neglected": {"emoji": "😢", "color": 0x9b59b6},
}

MOOD_MESSAGES = {
    "mode_femboy": {
        "happy": "I'm super happy, Nii-chan! Everything is wonderful~ ♡",
        "neutral": "I'm doing okay! How can I help you today?",
        "sad": "I'm a little sad... but seeing you makes it better!",
        "neglected": "N-Nii-chan... you haven't talked to me in a while... >.<"
    },
    "mode_tsundere": {
        "happy": "I-I'm fine! Not that your attention matters or anything! Hmph!",
        "neutral": "What? I'm normal. Stop asking weird questions, baka.",
        "sad": "It's nothing! I'm not sad because you ignored me! ...baka.",
        "neglected": "W-where were you?! It's not like I missed you or anything!"
    },
    "mode_oneesan": {
        "happy": "Ara ara~ I'm feeling wonderful, my dear! Thank you for asking~",
        "neutral": "I'm doing well, little one. How are you?",
        "sad": "I'm a bit melancholy today... but your company helps~",
        "neglected": "My dear... it's been so quiet. I was starting to worry~"
    }
}


# ============================================
# Interaction Responses
# ============================================

HEADPAT_RESPONSES = {
    "mode_default": ["Human, such actions are meaningless!"],
    "mode_femboy": [
        "Mmm... your pats feel so nice, Nii-chan.",
        "Please keep going... I love your pats.",
        "E-eh... that feels really good... thank you.",
    ],
    "mode_tsundere": [
        "W-what are you doing, baka?!",
        "Hmph. I do not need your pats, baka.",
        "D-don't get the wrong idea, baka.",
    ],
    "mode_oneesan": [
        "Stop that. I am not a child.",
        "Do not pat me. That is rude.",
        "Enough. I will not tolerate that.",
    ],
}

HUG_RESPONSES = {
    "mode_default": ["Human, such actions are meaningless!"],
    "mode_femboy": [
        "I feel safe in your arms, Nii-chan...",
        "Your hugs make me melt...",
        "I-I'm happy when you hold me...",
    ],
    "mode_tsundere": [
        "B-baka! What do you think you're doing?!",
        "Hmph. I am only allowing this, baka.",
        "D-don't get used to it, baka.",
    ],
    "mode_oneesan": [
        "There, there... calm down, my dear.",
        "Come here. I will hold you properly.",
        "You are safe. I have you.",
    ],
}

RATE_LIMIT_MESSAGES = {
    "mode_femboy": {
        "pat_hourly": "Femmy had all the pats right now!",
        "pat_daily": "Femmy had all the pats today!",
        "hug_hourly": "Femmy had all the hugs right now!",
        "hug_daily": "Femmy had all the hugs today!",
    },
    "mode_tsundere": {
        "pat_hourly": "Stop it. No more pats right now, baka.",
        "pat_daily": "No more pats today, baka.",
        "hug_hourly": "I have had enough hugs right now, baka.",
        "hug_daily": "No more hugs today.",
    },
    "mode_oneesan": {
        "pat_hourly": "That is enough for now.",
        "pat_daily": "No more pats today.",
        "hug_hourly": "One hug is enough for now.",
        "hug_daily": "No more hugs today, my dear.",
    },
}


class Affection(commands.Cog):
    """
    Affection & Mood Cog - Engagement and relationship tracking.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.mood_decay_loop.start()
    
    def cog_unload(self):
        self.mood_decay_loop.cancel()

    def _build_affection_embed(self, target: discord.Member, data_by_mode: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"💖 {target.display_name}'s Affection",
            color=discord.Color.from_rgb(255, 182, 193),
        )

        for mode_key in AFFECTION_TRACKED_MODES:
            mode_data = data_by_mode.get(mode_key, {})
            level = mode_data.get("affection_level", "stranger")
            points = mode_data.get("affection_points", 0)
            interactions = mode_data.get("total_interactions", 0)
            level_display = AFFECTION_DISPLAY.get(level, AFFECTION_DISPLAY["stranger"])
            mode_display = MODE_AFFECTION_DISPLAY.get(
                mode_key,
                {"emoji": "✨", "name": mode_key},
            )

            progress = 100.0
            next_threshold = None
            for min_pts, max_pts, lvl_name in AFFECTION_THRESHOLDS:
                if lvl_name == level:
                    if max_pts != float("inf"):
                        next_threshold = max_pts
                        progress = (points - min_pts) / (max_pts - min_pts) * 100
                    else:
                        progress = 100.0
                    break

            filled = int(progress // 10)
            bar = "█" * filled + "░" * (10 - filled)
            if next_threshold:
                progress_line = f"[{bar}] {progress:.1f}% ({points}/{next_threshold})"
            else:
                progress_line = "✨ Max Level Reached! ✨"

            value = (
                f"{level_display['emoji']} **{level_display['title']}**\n"
                f"Points: **{points:,}** | Interactions: **{interactions:,}**\n"
                f"{progress_line}"
            )
            embed.add_field(
                name=f"{mode_display['emoji']} {mode_display['name']}",
                value=value,
                inline=False,
            )

        embed.set_thumbnail(url=target.display_avatar.url)
        return embed

    async def _handle_interaction(self, guild_id: int, user_id: int, interaction_type: str) -> str:
        mode = await get_server_mode(guild_id)
        if mode == "mode_default":
            responses = HEADPAT_RESPONSES if interaction_type == "pat" else HUG_RESPONSES
            return responses["mode_default"][0]

        allowed, reason = await check_interaction_limit(guild_id, user_id, interaction_type)
        if not allowed:
            key = f"{interaction_type}_{reason}"
            message = RATE_LIMIT_MESSAGES.get(mode, {}).get(key)
            if message:
                return message
            return "Please wait before trying again."

        delta = 1
        if interaction_type == "pat" and mode == "mode_oneesan":
            delta = -1

        affection_mode = mode if mode in AFFECTION_TRACKED_MODES else "mode_femboy"

        await update_mood(guild_id, 5)
        await add_affection_to_mode(guild_id, user_id, affection_mode, delta)
        await record_interaction(guild_id, user_id, interaction_type)

        responses = HEADPAT_RESPONSES if interaction_type == "pat" else HUG_RESPONSES
        response_list = responses.get(mode, responses.get("mode_femboy", []))
        if not response_list:
            return "..."
        return random.choice(response_list)
    
    # ============================================
    # Commands
    # ============================================
    
    @commands.command(name="affection", aliases=["love", "relationship"])
    async def show_affection(self, ctx: commands.Context, member: discord.Member = None):
        """View your or another user's affection level."""
        if not ctx.guild:
            await ctx.send("Affection is server-specific. Use this in a server.")
            return

        target = member or ctx.author
        data_by_mode = await get_all_mode_affection(ctx.guild.id, target.id)
        embed = self._build_affection_embed(target, data_by_mode)
        await ctx.send(embed=embed)

    @app_commands.command(name="affection", description="View your or another user's affection level.")
    @app_commands.describe(member="User to check (optional)")
    async def show_affection_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        if not interaction.guild:
            await interaction.response.send_message("Affection is server-specific. Use this in a server.", ephemeral=True)
            return

        target = member or interaction.user
        data_by_mode = await get_all_mode_affection(interaction.guild.id, target.id)
        embed = self._build_affection_embed(target, data_by_mode)
        await interaction.response.send_message(embed=embed)
    
    @commands.command(name="mood")
    async def show_mood(self, ctx: commands.Context):
        """Check the bot's current mood."""
        if not ctx.guild:
            await ctx.send("Moods are server-specific~ Use this in a server!")
            return
        
        mood_data = await get_mood(ctx.guild.id)
        mode = await get_server_mode(ctx.guild.id)
        
        mood = mood_data["mood"]
        value = mood_data["mood_value"]
        display = MOOD_DISPLAY.get(mood, MOOD_DISPLAY["neutral"])
        
        message = MOOD_MESSAGES.get(mode, MOOD_MESSAGES["mode_femboy"]).get(mood, "I'm okay~")
        
        # Build mood bar
        filled = int(value // 10)
        bar = "💖" * filled + "🖤" * (10 - filled)
        
        embed = discord.Embed(
            title=f"{display['emoji']} Current Mood",
            description=message,
            color=display["color"]
        )
        
        embed.add_field(
            name="Mood Level",
            value=f"[{bar}] {value}/100",
            inline=False
        )
        
        embed.set_footer(text="Interact with me to improve my mood~ ♡")
        
        await ctx.send(embed=embed)

    @app_commands.command(name="mood", description="Check the bot's current mood.")
    async def show_mood_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Moods are server-specific. Use this in a server.", ephemeral=True)
            return

        mood_data = await get_mood(interaction.guild.id)
        mode = await get_server_mode(interaction.guild.id)

        mood = mood_data["mood"]
        value = mood_data["mood_value"]
        display = MOOD_DISPLAY.get(mood, MOOD_DISPLAY["neutral"])

        message = MOOD_MESSAGES.get(mode, MOOD_MESSAGES["mode_femboy"]).get(mood, "I'm okay~")

        filled = int(value // 10)
        bar = "💖" * filled + "🖤" * (10 - filled)

        embed = discord.Embed(
            title=f"{display['emoji']} Current Mood",
            description=message,
            color=display["color"],
        )
        embed.add_field(name="Mood Level", value=f"[{bar}] {value}/100", inline=False)
        embed.set_footer(text="Interact with me to improve my mood~ ♡")
        await interaction.response.send_message(embed=embed)
    
    @commands.command(name="headpat", aliases=["pat", "pets"])
    async def headpat(self, ctx: commands.Context):
        """Give Femmy headpats!"""
        if not ctx.guild:
            return
        response = await self._handle_interaction(ctx.guild.id, ctx.author.id, "pat")
        await ctx.send(response)

    @app_commands.command(name="headpat", description="Give a headpat.")
    async def headpat_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        response = await self._handle_interaction(interaction.guild.id, interaction.user.id, "pat")
        await interaction.response.send_message(response)
    
    @commands.command(name="hug", aliases=["hugs"])
    async def hug(self, ctx: commands.Context):
        """Give Femmy a hug!"""
        if not ctx.guild:
            return
        response = await self._handle_interaction(ctx.guild.id, ctx.author.id, "hug")
        await ctx.send(response)

    @app_commands.command(name="hug", description="Give a hug.")
    async def hug_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        response = await self._handle_interaction(interaction.guild.id, interaction.user.id, "hug")
        await interaction.response.send_message(response)
    
    # ============================================
    # Listeners
    # ============================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Track interactions for affection and mood with sentiment analysis."""
        if message.author.bot:
            return
        if not message.guild:
            return
        
        # Small mood boost for any activity
        await update_mood(message.guild.id, 1)

        mode = await get_server_mode(message.guild.id)
        
        # If bot is mentioned, analyze sentiment and adjust affection
        if self.bot.user in message.mentions:
            if mode == "mode_default":
                return
            affection_mode = mode if mode in AFFECTION_TRACKED_MODES else "mode_femboy"
            # Get message content without the mention
            content = message.content
            content = content.replace(f"<@{self.bot.user.id}>", "").strip()
            content = content.replace(f"<@!{self.bot.user.id}>", "").strip()
            
            if len(content) > 5:
                # Try quick keyword check first
                quick_result = quick_sentiment_check(content)
                
                if quick_result:
                    sentiment, delta = quick_result
                else:
                    # Use AI for more nuanced analysis
                    sentiment, delta = await analyze_sentiment(message.guild.id, content)
                
                # Apply affection change (don't reply here - ai_brain handles responses)
                await add_affection_to_mode(message.guild.id, message.author.id, affection_mode, delta)
                
                if sentiment in ("negative", "very_negative", "hostile"):
                    logger.info(f"Negative interaction from {message.author}: {sentiment} ({delta} pts)")
            else:
                # Default positive for short mentions
                await add_affection_to_mode(message.guild.id, message.author.id, affection_mode, 1)
    
    # ============================================
    # Background Tasks
    # ============================================
    
    @tasks.loop(hours=1)
    async def mood_decay_loop(self):
        """Decay mood over time when inactive."""
        from utils.db_handler import get_registered_guild_ids, guild_db
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=1)

        for guild_id in await get_registered_guild_ids():
            async with guild_db(guild_id) as db:
                # Decay mood by 3 for servers inactive for 1+ hours
                await db.execute("""
                    UPDATE bot_mood 
                    SET mood_value = MAX(0, mood_value - 3),
                        mood = CASE 
                            WHEN mood_value - 3 >= 70 THEN 'happy'
                            WHEN mood_value - 3 >= 40 THEN 'neutral'
                            WHEN mood_value - 3 >= 20 THEN 'sad'
                            ELSE 'neglected'
                        END
                    WHERE last_updated < ?
                """, (cutoff,))
                await db.commit()
    
    @mood_decay_loop.before_loop
    async def before_mood_decay(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Affection(bot))
