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
    !headpat         - Give headpats (+5 mood, +3 affection)
    !hug             - Give hugs (+5 mood, +3 affection)
"""

import random
import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.db_handler import (
    get_affection,
    add_affection,
    get_mood,
    update_mood,
    get_server_mode,
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
    "mode_femboy": [
        "*purrs happily* Ehehe~ That feels nice, Nii-chan~ ♡",
        "*melts* H-headpats... I love headpats~ ✨",
        "*tail wags* More more more~ >w<"
    ],
    "mode_tsundere": [
        "*blushes furiously* W-what are you doing, baka?! ...don't stop though.",
        "Hmph! I-it's not like I enjoy this or anything! ...pat me more.",
        "*reluctantly leans into hand* ...fine, but only because you insist!"
    ],
    "mode_oneesan": [
        "Ara ara~ How sweet of you, little one~ *pats you back*",
        "Fufu~ You're so adorable when you try to spoil me~",
        "*smiles warmly* Thank you, my dear. That was lovely~"
    ]
}

HUG_RESPONSES = {
    "mode_femboy": [
        "*hugs back tightly* Nii-chan's hugs are the best~ ♡",
        "*nuzzles* I could stay like this forever! ✨",
        "*squeezes* Thank you thank you thank you~!"
    ],
    "mode_tsundere": [
        "*stiffens* W-what?! ...okay, fine. Just this once. *hugs back briefly*",
        "Baka! You can't just- ...okay, I guess this is nice. Don't tell anyone!",
        "*mumbles* It's warm... I hate how nice this feels. Hmph!"
    ],
    "mode_oneesan": [
        "*wraps arms around you* There there, my dear~ *pats back*",
        "Ara ara~ Come here, let me hold you properly~ ♡",
        "*gentle embrace* You give the best hugs, little one~"
    ]
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
        data = await get_affection(ctx.guild.id, target.id)
        
        level = data["affection_level"]
        points = data["affection_points"]
        interactions = data["total_interactions"]
        display = AFFECTION_DISPLAY.get(level, AFFECTION_DISPLAY["stranger"])
        
        # Calculate progress to next level
        next_threshold = None
        for min_pts, max_pts, lvl_name in AFFECTION_THRESHOLDS:
            if lvl_name == level and max_pts != float("inf"):
                next_threshold = max_pts
                progress = (points - min_pts) / (max_pts - min_pts) * 100
                break
        else:
            progress = 100
        
        # Build progress bar
        filled = int(progress // 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        embed = discord.Embed(
            title=f"{display['emoji']} {target.display_name}'s Affection",
            color=display["color"]
        )
        
        embed.add_field(
            name="Level",
            value=f"**{display['title']}**",
            inline=True
        )
        embed.add_field(
            name="Points",
            value=f"**{points:,}** pts",
            inline=True
        )
        embed.add_field(
            name="Interactions",
            value=f"**{interactions:,}**",
            inline=True
        )
        
        if next_threshold:
            embed.add_field(
                name="Progress to Next Level",
                value=f"[{bar}] {progress:.1f}%\n{points}/{next_threshold}",
                inline=False
            )
        else:
            embed.add_field(
                name="Progress",
                value="✨ Max Level Reached! ✨",
                inline=False
            )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="affection", description="View your or another user's affection level.")
    @app_commands.describe(member="User to check (optional)")
    async def show_affection_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        if not interaction.guild:
            await interaction.response.send_message("Affection is server-specific. Use this in a server.", ephemeral=True)
            return

        target = member or interaction.user
        data = await get_affection(interaction.guild.id, target.id)

        level = data["affection_level"]
        points = data["affection_points"]
        interactions = data["total_interactions"]
        display = AFFECTION_DISPLAY.get(level, AFFECTION_DISPLAY["stranger"])

        next_threshold = None
        for min_pts, max_pts, lvl_name in AFFECTION_THRESHOLDS:
            if lvl_name == level and max_pts != float("inf"):
                next_threshold = max_pts
                progress = (points - min_pts) / (max_pts - min_pts) * 100
                break
        else:
            progress = 100

        filled = int(progress // 10)
        bar = "█" * filled + "░" * (10 - filled)

        embed = discord.Embed(
            title=f"{display['emoji']} {target.display_name}'s Affection",
            color=display["color"],
        )
        embed.add_field(name="Level", value=f"**{display['title']}**", inline=True)
        embed.add_field(name="Points", value=f"**{points:,}** pts", inline=True)
        embed.add_field(name="Interactions", value=f"**{interactions:,}**", inline=True)

        if next_threshold:
            embed.add_field(
                name="Progress to Next Level",
                value=f"[{bar}] {progress:.1f}%\n{points}/{next_threshold}",
                inline=False,
            )
        else:
            embed.add_field(name="Progress", value="✨ Max Level Reached! ✨", inline=False)

        embed.set_thumbnail(url=target.display_avatar.url)
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
        
        mode = await get_server_mode(ctx.guild.id)
        
        # Update mood and affection
        await update_mood(ctx.guild.id, 5)
        await add_affection(ctx.guild.id, ctx.author.id, 3)
        
        responses = HEADPAT_RESPONSES.get(mode, HEADPAT_RESPONSES["mode_femboy"])
        response = random.choice(responses)
        
        await ctx.send(response)

    @app_commands.command(name="headpat", description="Give a headpat.")
    async def headpat_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        mode = await get_server_mode(interaction.guild.id)
        await update_mood(interaction.guild.id, 5)
        await add_affection(interaction.guild.id, interaction.user.id, 3)

        responses = HEADPAT_RESPONSES.get(mode, HEADPAT_RESPONSES["mode_femboy"])
        response = random.choice(responses)
        await interaction.response.send_message(response)
    
    @commands.command(name="hug", aliases=["hugs"])
    async def hug(self, ctx: commands.Context):
        """Give Femmy a hug!"""
        if not ctx.guild:
            return
        
        mode = await get_server_mode(ctx.guild.id)
        
        # Update mood and affection
        await update_mood(ctx.guild.id, 5)
        await add_affection(ctx.guild.id, ctx.author.id, 3)
        
        responses = HUG_RESPONSES.get(mode, HUG_RESPONSES["mode_femboy"])
        response = random.choice(responses)
        
        await ctx.send(response)

    @app_commands.command(name="hug", description="Give a hug.")
    async def hug_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        mode = await get_server_mode(interaction.guild.id)
        await update_mood(interaction.guild.id, 5)
        await add_affection(interaction.guild.id, interaction.user.id, 3)

        responses = HUG_RESPONSES.get(mode, HUG_RESPONSES["mode_femboy"])
        response = random.choice(responses)
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
        
        # If bot is mentioned, analyze sentiment and adjust affection
        if self.bot.user in message.mentions:
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
                await add_affection(message.guild.id, message.author.id, delta)
                
                if sentiment in ("negative", "very_negative", "hostile"):
                    logger.info(f"Negative interaction from {message.author}: {sentiment} ({delta} pts)")
            else:
                # Default positive for short mentions
                await add_affection(message.guild.id, message.author.id, 1)
    
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
