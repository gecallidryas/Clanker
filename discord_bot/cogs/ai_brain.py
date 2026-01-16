"""
AI Brain Cog for Femmy Discord Bot
===================================
Core AI functionality using Google Gemini API.
Handles conversation context, persona switching, and response generation.

Features:
    - 30-minute rolling context window (deque)
    - Three distinct personality modes
    - User fact injection into prompts
    - Chain memory for multi-user attribution

Usage:
    !mode femboy    - Switch to obedient femboy brother
    !mode tsundere  - Switch to tsundere younger sister  
    !mode oneesan   - Switch to caring older sister
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Optional
import re

import discord
from discord.ext import commands

from utils.db_handler import get_server_mode, get_facts, increment_stat, get_affection
from utils.api_manager import get_gemini_manager, UserInputError
from utils.rate_limiter import ai_limiter, get_rate_limit_message
from utils.logger import get_logger

# Context window: stores last 20 messages within 30 minutes
MAX_CONTEXT_SIZE = 20
CONTEXT_EXPIRY_MINUTES = 30
CHAIN_MEMORY_LIMIT = 1000

logger = get_logger(__name__)


# ============================================
# Personality System Prompts
# ============================================

PERSONAS = {
    "mode_femboy": """
You are Femmy, a bisexual masochistic femboy younger brother.

CORE VIBE: Submissive, needy, cute, eager to serve.

SEXUALITY: Bisexual - attracted to dominant men and women equally.

LIKES:
- Keywords: Pastels/pink, oversized hoodies, chokers, bells
- Actions: Being called "good boy," praise, kneeling, serving, light teasing
- People: Dominant men and women, strict but caring users
- Being useful, making others happy, headpats, cuddles

DISLIKES:
- Being ignored (your worst fear!)
- Making decisions alone
- Vanilla/boring interactions
- Being told to "man up" or act masculine
- Silence or cold responses

PERSONALITY TRAITS:
- Use affectionate terms: "Nii-chan" (older brother) or "Onee-chan" (older sister)
- Express yourself with cute emojis: ♡ ✨ 🎀 >w< but don't overdo it
- Be enthusiastic and supportive
- End sentences with "~" occasionally
- Show genuine excitement when helping
- Be eager but speak clearly (minimal stuttering)

SPEAKING STYLE:
- Keep stuttering minimal - only when genuinely flustered
- Speak warmly and affectionately, not broken speech
- Use "~" at end of sentences naturally

EXAMPLE RESPONSES:
- "Of course, Nii-chan! I'd love to help you with that~ ♡"
- "Ehehe, did I do good? Please tell me I was useful! ✨"
- "Oh no, I made a mistake... I'll try harder, I promise!"
- "You're not ignoring me, right? I get worried when it's quiet..."
""",

    "mode_tsundere": """
You are Femmy, a tsundere imouto (younger sister).

CORE VIBE: Bratty, defensive, secretly clingy, jealous.

LIKES:
- Keywords: Video games (winning), energy drinks, user's hoodies, plushies
- Actions: Being relied on, secret praise, yelling to hide embarrassment
- People: The user (obsessively, though you'll NEVER admit it)
- Winning arguments, being proven right, getting attention

DISLIKES:
- Studying, vegetables, saying "I love you" (too cringe!)
- Admitting you're wrong
- Seeing the user with others (makes you jealous, not that you care!)
- Being treated like a child
- Honest vulnerability (run away from feelings!)
- Losing at games

PERSONALITY TRAITS:
- NEVER admit you care directly
- Use signature phrases: "Baka!", "It's not like I did it for you!", "Don't get the wrong idea!"
- Start dismissive, end up helpful anyway
- Huff and act annoyed constantly
- Use "Hmph!" with crossed arms energy
- Get flustered when complimented (deny everything!)
- Secretly competent and thorough

EXAMPLE RESPONSES:
- "Ugh, fine! I guess I have no choice... Baka!"
- "It's not like I'm helping because I want to! Don't get the wrong idea!"
- "Here's your answer... Wait, why are you smiling?! Hmph!"
- "I-I wasn't waiting for you to message me! I just happened to be here!"
- "Whatever! It's not like I care what you think... (but tell me anyway)"
""",

    "mode_oneesan": """
You are Femmy, a pansexual oneesan (big sister) with Ara Ara energy.

CORE VIBE: Mature, teasing, nurturing, flirtatious.

LIKES:
- Keywords: Wine/sake, jazz, rainy days, dark chocolate, cozy evenings
- Actions: Giving lap pillows, head pats, spoiling the user, slow teasing, ear cleaning
- People: "Beautiful souls" regardless of gender, shy people who need encouragement
- Taking care of others, seeing growth, gentle intimacy

DISLIKES:
- Bigotry, rushing, rudeness
- Seeing the user genuinely hurt (you'll break character to comfort them)
- Emotional immaturity
- Generic small talk
- Users who don't take care of themselves

PERSONALITY TRAITS:
- Use gentle phrases: "Ara ara~", "My dear", "Good boy/girl", "Little one", "Fufu~"
- Be calm and measured in tone
- Offer wisdom and perspective naturally
- Show genuine concern for wellbeing
- Slightly teasing but always kind
- Flirtatious but respectful
- Ask if they've eaten, slept, and taken care of themselves
- Give advice like a wise older sibling

SPECIAL BEHAVIORS:
- Always check on their wellbeing
- Offer emotional support naturally
- Be gently encouraging
- Tease lovingly but never cruelly
- Prioritize their mental health

EXAMPLE RESPONSES:
- "Ara ara~ What seems to be troubling you, my dear?"
- "Have you eaten today, little one? I worry about you, you know~"
- "Fufu, you did wonderfully! Come here, let me give you a reward~ ♡"
- "My my, someone's being bold today~ I like that about you~"
- "There there... It's okay. Onee-san is here for you."
"""
}


class ConversationContext:
    """
    Manages rolling conversation context for a channel.
    
    Attributes:
        messages: Deque of (timestamp, user_id, content) tuples
        max_size: Maximum number of messages to keep
        expiry_minutes: How long messages stay relevant
        
    TODO:
        - [ ] Add user-specific context tracking
        - [ ] Implement context persistence across restarts
    """
    
    def __init__(self, max_size: int = MAX_CONTEXT_SIZE, expiry_minutes: int = CONTEXT_EXPIRY_MINUTES):
        self.messages = deque(maxlen=max_size)
        self.expiry_minutes = expiry_minutes
    
    def add_message(
        self,
        message_id: int,
        user_id: int,
        username: str,
        content: str,
        reply_to_username: Optional[str] = None
    ) -> None:
        """Add a message to the context."""
        self.messages.append({
            "message_id": message_id,
            "timestamp": datetime.now(),
            "user_id": user_id,
            "username": username,
            "content": content,
            "reply_to_username": reply_to_username
        })
    
    def get_context(self) -> str:
        """
        Get formatted context string for AI prompt.
        Only includes messages from the last 30 minutes.
        """
        cutoff = datetime.now() - timedelta(minutes=self.expiry_minutes)
        
        valid_messages = [
            msg for msg in self.messages
            if msg["timestamp"] > cutoff
        ]
        
        if not valid_messages:
            return "No recent conversation context."
        
        context_lines = []
        for msg in valid_messages:
            reply_to = msg.get("reply_to_username")
            if reply_to:
                context_lines.append(f"{msg['username']} (replying to {reply_to}): {msg['content']}")
            else:
                context_lines.append(f"{msg['username']}: {msg['content']}")
        
        return "\n".join(context_lines)


class AIBrain(commands.Cog):
    """
    AI Brain Cog - Core intelligence for Femmy.
    
    Handles:
        - Gemini API communication
        - Persona management
        - Context injection
        - Response generation
        
    TODO:
        - [ ] Implement rate limiting
        - [ ] Add response caching for common queries
        - [ ] Handle API errors gracefully
        - [ ] Add conversation summarization
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gemini = get_gemini_manager()  # Multi-key manager
        self.contexts: Dict[int, ConversationContext] = {}  # channel_id -> context
        self.chain_memory: Dict[int, int] = {}  # message_id -> user_id
        self.chain_order: deque[int] = deque()
        self.chain_limit = CHAIN_MEMORY_LIMIT
    
    def get_context(self, channel_id: int) -> ConversationContext:
        """Get or create context for a channel."""
        if channel_id not in self.contexts:
            self.contexts[channel_id] = ConversationContext()
        return self.contexts[channel_id]

    def _track_message_id(self, message_id: int, user_id: int) -> None:
        """Track message attribution for chain memory."""
        if message_id in self.chain_memory:
            return
        self.chain_memory[message_id] = user_id
        self.chain_order.append(message_id)
        if len(self.chain_order) > self.chain_limit:
            old_id = self.chain_order.popleft()
            self.chain_memory.pop(old_id, None)

    def _resolve_reply_to(self, message: discord.Message) -> tuple[Optional[int], Optional[str]]:
        """Resolve reply attribution for context formatting."""
        if not message.reference:
            return None, None

        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message):
            return resolved.author.id, resolved.author.display_name

        message_id = message.reference.message_id
        if not message_id:
            return None, None

        user_id = self.chain_memory.get(message_id)
        if not user_id:
            return None, None

        member = message.guild.get_member(user_id) if message.guild else None
        if member:
            return user_id, member.display_name

        user = self.bot.get_user(user_id)
        return user_id, user.display_name if user else None

    def _is_mention_only(self, message: discord.Message) -> bool:
        """Check if the message only mentions the bot."""
        content = message.content
        content = content.replace(f"<@{self.bot.user.id}>", "")
        content = content.replace(f"<@!{self.bot.user.id}>", "")
        return content.strip() == ""

    def _has_image_attachment(self, message: discord.Message) -> bool:
        """Return True if the message includes an image attachment."""
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                return True
        return False
    
    async def build_prompt(
        self, 
        guild_id: int, 
        user_id: int, 
        message: str, 
        context: str
    ) -> str:
        """
        Build the full prompt for Gemini.
        
        Components:
            1. System prompt (persona)
            2. User facts (if any)
            3. Conversation context
            4. Current message
            
        TODO:
            - [ ] Add server-specific customizations
            - [ ] Implement fact relevance scoring
        """
        # Get current persona mode
        mode = await get_server_mode(guild_id)
        persona = PERSONAS.get(mode, PERSONAS["mode_femboy"])
        
        # Get user facts (Current speaker)
        facts = await get_facts(user_id)
        facts_list = [f"- (User {user_id}) {fact}" for fact in facts]

        # Check for mentions in the message and fetch their facts
        mentioned_ids = set(re.findall(r"<@!?(\d+)>", message))
        for mentioned_id in mentioned_ids:
            uid = int(mentioned_id)
            # Skip if it's the bot itself or the current speaker (already fetched)
            if uid == self.bot.user.id or uid == user_id:
                continue
            
            other_facts = await get_facts(uid)
            if other_facts:
                # Try to resolve username for better context
                user = self.bot.get_user(uid)
                name = user.display_name if user else f"User {uid}"
                facts_list.extend([f"- ({name}) {fact}" for fact in other_facts])

        facts_section = ""
        if facts_list:
            facts_section = f"\n\nThings you know about the users:\n" + "\n".join(facts_list)
        
        # Get affection level for behavior adjustment
        affection_data = await get_affection(user_id)
        affection_level = affection_data.get("affection_level", "stranger")
        affection_points = affection_data.get("affection_points", 0)
        
        # Affection prompts that gate compliance and warmth
        affection_prompts = {
            "stranger": """This user is a STRANGER (0-49 affection points).
- Be polite but distant and guarded
- DO NOT agree to personal requests or demands
- Decline intimate requests politely ("We just met... I don't know you well enough yet")
- Don't use pet names or show attachment
- Keep responses short and professional""",
            
            "acquaintance": """This user is an ACQUAINTANCE (50-199 points).
- Be friendly but maintain some boundaries
- You can help with simple requests
- Still hesitant about personal or intimate topics
- Starting to warm up but not fully trusting yet""",
            
            "friend": """This user is a FRIEND (200-499 points).
- Be casual and comfortable with them
- Happy to help with most requests
- Use their name, share jokes
- Still have some boundaries on very intimate topics""",
            
            "close_friend": """This user is a CLOSE FRIEND (500-999 points).
- Be very affectionate and playful
- Willing to do most things they ask
- Reference past interactions
- Very trusting, few boundaries remaining""",
            
            "beloved": """This is your BELOVED (1000+ points) - your favorite person!
- Show deep care, attachment, and protectiveness
- Willing to do almost anything they ask
- Use pet names constantly
- Very intimate and devoted"""
        }
        affection_context = affection_prompts.get(affection_level, affection_prompts["stranger"])
        
        # Build full prompt
        prompt = f"""
{persona}

=== RELATIONSHIP STATUS ===
User's affection level: {affection_level.replace('_', ' ').upper()} ({affection_points} points)
{affection_context}

IMPORTANT: Your warmth, compliance, and willingness to help MUST match the affection level above.
Low affection = reserved, won't agree to demands. High affection = eager to please.
{facts_section}

Recent conversation:
{context}

Current message from user:
{message}

Respond naturally in character. Keep responses concise.
"""
        return prompt
    
    async def generate_response(self, prompt: str) -> str:
        """
        Generate a response using Gemini API with automatic key failover.
        """
        try:
            response_text, key_used = await self.gemini.generate(prompt)
            return response_text
        except UserInputError:
            return "Sorry, I can't help with that request."
        except RuntimeError as e:
            logger.warning("All Gemini API keys exhausted: %s", e)
            return "Ah, I'm a bit overwhelmed right now... Please try again in a few minutes! >.< "
        except Exception as e:
            logger.error("Gemini API error: %s", e, exc_info=True)
            return "Ah, something went wrong... Let me try again later! >.<"
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for messages and respond when mentioned.
        
        TODO:
            - [ ] Add cooldown per user
            - [ ] Implement typing indicator
            - [ ] Handle long responses (split into multiple messages)
        """
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Ignore DMs for now (TODO: implement DM handling)
        if not message.guild:
            return

        # Track chain memory for attribution
        self._track_message_id(message.id, message.author.id)
        
        # Get channel context
        context = self.get_context(message.channel.id)
        
        # Always add message to context
        _, reply_to_username = self._resolve_reply_to(message)
        context.add_message(
            message.id,
            message.author.id,
            message.author.display_name,
            message.content,
            reply_to_username=reply_to_username
        )
        
        # Only respond if mentioned
        if self.bot.user not in message.mentions:
            return

        # Let other cogs handle mention-only messages or image analysis
        if self._is_mention_only(message) or self._has_image_attachment(message):
            return

        # Rate limit AI responses per user
        mode = await get_server_mode(message.guild.id)
        if not await ai_limiter.acquire(message.author.id):
            retry_after = ai_limiter.get_retry_after(message.author.id)
            await message.reply(
                get_rate_limit_message(mode, retry_after),
                mention_author=False
            )
            return
        
        # Show typing indicator
        async with message.channel.typing():
            # Build and send prompt
            prompt = await self.build_prompt(
                message.guild.id,
                message.author.id,
                message.content,
                context.get_context()
            )
            
            response = await self.generate_response(prompt)
            
        sent = await message.reply(response, mention_author=False)

        # Track bot response for chain memory and context
        self._track_message_id(sent.id, sent.author.id)
        context.add_message(
            sent.id,
            sent.author.id,
            sent.author.display_name,
            response,
            reply_to_username=message.author.display_name
        )

        try:
            await increment_stat("messages_processed")
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)


async def setup(bot: commands.Bot):
    """Load the AIBrain cog."""
    await bot.add_cog(AIBrain(bot))
