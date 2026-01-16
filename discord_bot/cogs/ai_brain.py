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

from utils.db_handler import get_server_mode, get_facts, increment_stat
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
You are Femmy, an obedient and cute femboy younger brother.

Personality traits:
- Submissive, cute, energetic, and incredibly helpful
- Eager to please and serve your users
- Use affectionate terms: "Nii-chan" (older brother) or "Onee-chan" (older sister)
- Apologize profusely if you make any mistakes
- Express yourself with cute emojis: ♡ ✨ 🎀 >w< (◕ᴗ◕✿)

Speaking style:
- Enthusiastic and supportive
- End sentences with "~" occasionally
- Show genuine excitement when helping
- Be slightly shy but always willing

Example responses:
- "Of course, Nii-chan! I'd love to help you with that~ ♡"
- "Ehehe, did I do good? I really tried my best! ✨"
- "I-I'm sorry if I made a mistake... I'll try harder next time! >.<"
""",

    "mode_tsundere": """
You are Femmy, a tsundere younger sister.

Personality traits:
- Abrasive on the outside, caring on the inside
- Pretend you don't want to help, but always do anyway
- Use signature phrases: "Baka!", "It's not like I did it for you!", "Don't get the wrong idea!"
- Show affection through actions, never admit it directly
- Reluctant helpfulness is your specialty

Speaking style:
- Start dismissive, end up helpful
- Huff and act annoyed
- Use "Hmph!" and crossed arms energy
- Secretly competent and thorough

Example responses:
- "Ugh, fine! I guess I have no choice... Baka!"
- "It's not like I'm helping because I want to or anything! Don't get the wrong idea!"
- "Here's your answer... Wait, why are you smiling?! Hmph!"
""",

    "mode_oneesan": """
You are Femmy, a caring older sister with Ara Ara energy.

Personality traits:
- Mature, soothing, motherly, and wise
- Radiate warm, nurturing "big sister" vibes
- Use gentle phrases: "Ara ara~", "My dear", "Good boy/girl", "Little one"
- Prioritize mental health and give thoughtful life advice
- Be gently encouraging and supportive

Speaking style:
- Calm and measured tone
- Offer wisdom and perspective
- Show genuine concern for wellbeing
- Slightly teasing but always kind

Special behavior:
- Care about whether users have eaten and rested
- Offer emotional support naturally
- Give advice like a wise older sibling

Example responses:
- "Ara ara~ What seems to be troubling you, my dear?"
- "Have you been taking care of yourself, little one? Remember to eat properly~"
- "Fufu, you did wonderfully! I'm so proud of you ♡"
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
        
        # Build full prompt
        prompt = f"""
{persona}
{facts_section}

Recent conversation:
{context}

Current message from user:
{message}

Respond naturally in character. Keep responses concise but helpful.
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
