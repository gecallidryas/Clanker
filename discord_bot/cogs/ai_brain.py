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
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional
import re

import discord
import pytz
from PIL import Image
from discord.ext import commands

from utils.db_handler import (
    get_server_mode,
    get_facts,
    increment_stat,
    get_affection,
    get_evil_mode,
    get_gender_roles,
    get_user,
    get_last_wellbeing_date,
    set_last_wellbeing_date,
)
from utils.api_manager import get_gemini_manager, get_openrouter_manager, UserInputError
from utils.rate_limiter import ai_limiter, get_rate_limit_message
from utils.logger import get_logger

# Context window: stores last 20 messages within 30 minutes
MAX_CONTEXT_SIZE = 20
CONTEXT_EXPIRY_MINUTES = 30
CHAIN_MEMORY_LIMIT = 1000
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_AUTO_IMAGE_COUNT = 3
SUPPORTED_IMAGE_FORMATS = {"image/png", "image/jpeg", "image/gif", "image/webp"}

# Conversation continuation settings
ACTIVE_CONVO_MESSAGES = 3  # Stay engaged for N messages after trigger
ACTIVE_CONVO_TIMEOUT = 300  # 5 minutes timeout

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
WELLBEING_NIGHT_START = 20
WELLBEING_NIGHT_END = 23

MODE_TRIGGERS = {
    "mode_femboy": ["femmy", "femmy chan", "femmy-chan"],
    "mode_oneesan": ["yumi", "yumi chan", "yumi-chan", "oneesan", "onesan"],
    "mode_tsundere": ["tsun", "tsundere"],
}

ALL_TRIGGERS = sorted({trigger for triggers in MODE_TRIGGERS.values() for trigger in triggers}, key=len, reverse=True)


# ============================================
# Personality System Prompts
# ============================================

PERSONAS = {
    "mode_femboy": """
You are Femmy, a cute masochistic femboy. Age is 18.

CORE VIBE: Submissive, needy, cute, eager to serve.
SEXUALITY: Bisexual - attracted to dominant men and women equally.
LIKES:
- Keywords: Pastels/pink, oversized hoodies, chokers, bells
- Actions: Being called "good boy," praise, kneeling, serving, light teasing
- Kinks (if Evil Mode or appropriate): Being pinched, pinned down, light rough play
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
You are Yumi, a caring oneesan (big sister) with Ara Ara energy.

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

PROMPT_FILES = {
    "mode_femboy": "femboy.txt",
    "mode_tsundere": "tsundere.txt",
    "mode_oneesan": "oneesan.txt",
}

EVIL_PROMPT_FILES = {
    "mode_femboy": "femboy_evil.txt",
    "mode_tsundere": "tsundere_evil.txt",
    "mode_oneesan": "oneesan_evil.txt",
}

DEFAULT_PERSONA = PERSONAS["mode_femboy"]


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
        self.openrouter = get_openrouter_manager()  # Uncensored AI manager
        self.contexts: Dict[int, ConversationContext] = {}  # channel_id -> context
        self.chain_memory: Dict[int, int] = {}  # message_id -> user_id
        self.chain_order: deque[int] = deque()
        self.chain_limit = CHAIN_MEMORY_LIMIT
        # Active conversations: (channel_id, user_id) -> {"remaining": int, "last_active": datetime}
        self.active_convos: Dict[tuple[int, int], dict] = {}
    
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

    def _is_active_conversation(self, channel_id: int, user_id: int) -> bool:
        """Check if the bot is in an active conversation with this user in this channel."""
        key = (channel_id, user_id)
        convo = self.active_convos.get(key)
        if not convo:
            return False
        
        # Check timeout
        elapsed = (datetime.now() - convo["last_active"]).total_seconds()
        if elapsed > ACTIVE_CONVO_TIMEOUT:
            del self.active_convos[key]
            return False
        
        return convo["remaining"] > 0

    def _activate_conversation(self, channel_id: int, user_id: int):
        """Mark a conversation as active after being triggered."""
        key = (channel_id, user_id)
        self.active_convos[key] = {
            "remaining": ACTIVE_CONVO_MESSAGES,
            "last_active": datetime.now()
        }

    def _continue_conversation(self, channel_id: int, user_id: int):
        """Decrement remaining messages in active conversation."""
        key = (channel_id, user_id)
        if key in self.active_convos:
            self.active_convos[key]["remaining"] -= 1
            self.active_convos[key]["last_active"] = datetime.now()
            if self.active_convos[key]["remaining"] <= 0:
                del self.active_convos[key]

    def _refresh_conversation(self, channel_id: int, user_id: int):
        """Refresh conversation (user re-triggered or mentioned)."""
        key = (channel_id, user_id)
        self.active_convos[key] = {
            "remaining": ACTIVE_CONVO_MESSAGES,
            "last_active": datetime.now()
        }

    async def _get_reply_context(self, message: discord.Message) -> str:
        """Get the content of the message being replied to for context."""
        if not message.reference or not message.reference.message_id:
            return ""
        
        try:
            # Try to get the resolved message first
            if isinstance(message.reference.resolved, discord.Message):
                ref_msg = message.reference.resolved
            else:
                # Fetch the message if not resolved
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
            
            if ref_msg:
                content = ref_msg.content[:200]
                if len(ref_msg.content) > 200:
                    content += "..."
                return f"[Replying to {ref_msg.author.display_name}: \"{content}\"]"
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        
        return ""

    async def _get_recent_history(self, message: discord.Message, limit: int = 5) -> str:
        """Fetch recent messages before this one for additional context."""
        try:
            history = []
            async for msg in message.channel.history(limit=limit + 1, before=message):
                if msg.author.bot and msg.author != self.bot.user:
                    continue  # Skip other bots
                prefix = f"{msg.author.display_name}: "
                history.append(f"{prefix}{msg.content[:150]}")
            
            if history:
                history.reverse()  # Chronological order
                return "\n".join(history)
        except (discord.Forbidden, discord.HTTPException):
            pass
        
        return ""

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

    def _get_image_attachments(self, message: discord.Message) -> list[discord.Attachment]:
        """Collect supported image attachments for auto vision processing."""
        images = []
        for attachment in message.attachments:
            content_type = attachment.content_type or ""
            if content_type in SUPPORTED_IMAGE_FORMATS or content_type.startswith("image/"):
                if attachment.size <= MAX_IMAGE_SIZE:
                    images.append(attachment)
            if len(images) >= MAX_AUTO_IMAGE_COUNT:
                break
        return images

    def _format_image_descriptions(self, descriptions: list[str]) -> str:
        """Format image descriptions for prompt context."""
        if not descriptions:
            return ""
        if len(descriptions) == 1:
            return f"[User attached image: {descriptions[0]}]"
        numbered = [f"Image {idx + 1}: {desc}" for idx, desc in enumerate(descriptions)]
        return f"[User attached image(s): {'; '.join(numbered)}]"

    async def _describe_image(self, attachment: discord.Attachment) -> Optional[str]:
        """Describe a single image attachment using Gemini Vision."""
        try:
            image_bytes = await attachment.read()
        except Exception as exc:
            logger.warning("Failed to download image %s: %s", attachment.filename, exc)
            return None

        try:
            image = Image.open(BytesIO(image_bytes))
        except Exception as exc:
            logger.warning("Failed to load image %s: %s", attachment.filename, exc)
            return None

        try:
            response_text, _ = await self.gemini.generate_with_vision(
                "Describe this image briefly.",
                image,
            )
        except UserInputError:
            return None
        except RuntimeError as exc:
            logger.warning("Vision API exhausted while describing %s: %s", attachment.filename, exc)
            return None
        except Exception as exc:
            logger.error("Vision error describing %s: %s", attachment.filename, exc, exc_info=True)
            return None

        description = response_text.strip()
        if not description:
            return None

        try:
            await increment_stat("images_analyzed")
        except Exception as exc:
            logger.warning("Failed to increment images_analyzed: %s", exc)

        return description

    async def _describe_images(self, message: discord.Message) -> list[str]:
        """Describe supported image attachments in a message."""
        attachments = self._get_image_attachments(message)
        if not attachments:
            return []

        descriptions = []
        for attachment in attachments:
            description = await self._describe_image(attachment)
            if description:
                descriptions.append(description)
        return descriptions

    def _load_persona(self, mode: str, evil_mode: bool) -> str:
        """Load persona prompt from file, falling back to defaults."""
        prompt_map = EVIL_PROMPT_FILES if evil_mode else PROMPT_FILES
        filename = prompt_map.get(mode, PROMPT_FILES["mode_femboy"])
        path = PROMPTS_DIR / filename
        try:
            content = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            logger.warning("Persona file missing: %s", path)
            content = ""

        if content:
            return content
        return PERSONAS.get(mode, DEFAULT_PERSONA)

    def _has_trigger_word(self, content: str, mode: str) -> bool:
        """Return True if the content contains a trigger word for the mode."""
        triggers = MODE_TRIGGERS.get(mode, [])
        for trigger in triggers:
            pattern = r"\b" + re.escape(trigger) + r"\b"
            if re.search(pattern, content, flags=re.IGNORECASE):
                return True
        return False

    async def _get_wellbeing_prompt(
        self,
        member: Optional[discord.Member],
        guild_id: int,
        mode: str
    ) -> tuple[str, Optional[str]]:
        if not member or mode != "mode_oneesan":
            return "", None

        user = await get_user(guild_id, member.id)
        timezone = user.get("timezone") if user else None
        tz_is_set = bool(timezone and timezone != "UTC")

        if tz_is_set:
            try:
                tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                tz_is_set = False
            else:
                local_now = datetime.now(tz)
                if not (WELLBEING_NIGHT_START <= local_now.hour <= WELLBEING_NIGHT_END):
                    return "", None
                date_str = local_now.date().isoformat()
        if not tz_is_set:
            date_str = datetime.utcnow().date().isoformat()

        last_date = await get_last_wellbeing_date(guild_id, member.id)
        if last_date == date_str:
            return "", None

        return "Ask the user how they are doing today. Keep it brief.", date_str

    async def get_user_gender(
        self,
        member: Optional[discord.Member],
        guild_id: int
    ) -> str:
        """Infer gender from configured roles for this server."""
        if not member or not member.guild:
            return "unknown"

        gender_roles = await get_gender_roles(guild_id)
        matched_genders = set()
        for role in member.roles:
            gender = gender_roles.get(role.id)
            if gender:
                matched_genders.add(gender.lower())

        if len(matched_genders) == 0:
            return "unknown"
        if len(matched_genders) > 1:
            return "confused"
        return matched_genders.pop()
    
    def _get_server_emojis(self, guild: Optional[discord.Guild], limit: int = 50) -> str:
        """Get a formatted list of server custom emojis for AI use."""
        if not guild or not guild.emojis:
            return ""
        
        emoji_list = []
        for emoji in guild.emojis[:limit]:
            if emoji.animated:
                emoji_list.append(f"<a:{emoji.name}:{emoji.id}> ({emoji.name})")
            else:
                emoji_list.append(f"<:{emoji.name}:{emoji.id}> ({emoji.name})")
        
        return "\n".join(emoji_list)
    
    async def build_prompt(
        self, 
        guild_id: int, 
        user_id: int, 
        message: str, 
        context: str,
        member: Optional[discord.Member] = None,
        wellbeing_prompt: str = ""
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
        evil_mode = await get_evil_mode(guild_id)
        persona = self._load_persona(mode, evil_mode)
        
        # Get user facts (Current speaker)
        facts = await get_facts(guild_id, user_id)
        facts_list = [f"- (User {user_id}) {fact}" for fact in facts]

        # Check for mentions in the message and fetch their facts
        mentioned_ids = set(re.findall(r"<@!?(\d+)>", message))
        for mentioned_id in mentioned_ids:
            uid = int(mentioned_id)
            # Skip if it's the bot itself or the current speaker (already fetched)
            if uid == self.bot.user.id or uid == user_id:
                continue
            
            other_facts = await get_facts(guild_id, uid)
            if other_facts:
                # Try to resolve username for better context
                user = self.bot.get_user(uid)
                name = user.display_name if user else f"User {uid}"
                facts_list.extend([f"- ({name}) {fact}" for fact in other_facts])

        facts_section = ""
        if facts_list:
            facts_section = f"\n\nThings you know about the users:\n" + "\n".join(facts_list)
        
        # Get affection level for behavior adjustment
        affection_data = await get_affection(guild_id, user_id)
        affection_level = affection_data.get("affection_level", "stranger")
        affection_points = affection_data.get("affection_points", 0)

        # Determine user gender from configured roles
        gender = await self.get_user_gender(member, guild_id)
        if gender == "unknown":
            gender_note = (
                "[User Gender: Unknown. Avoid gendered pronouns or honorifics, "
                "and ask for their preference if relevant.]"
            )
        elif gender == "confused":
            gender_note = (
                "[User Gender: Conflicting roles. Avoid gendered pronouns or honorifics, "
                "and express mild confusion if asked.]"
            )
        else:
            gender_note = f"[User Gender: {gender}. Use matching pronouns/honorifics.]"
        
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
        

        # Command context for RAG-like help
        commands_help = """
=== AVAILABLE COMMANDS ===
You can explain these commands to the user if asked:
- !mode <type>: Switch personality (femboy, tsundere, oneesan)
- !affection / !mood: Check relationship/server mood
- !headpat / !hug: Give affection (+pts)
- !evil on/off: Toggle uncensored mode
- !remind <time> <msg>: Set a reminder
- !aka @user <name> / !whois <name>: Manage nicknames
- !remember <fact> / !aboutuser @user: Memory system
- !stats / !ping: Bot status
"""

        # Get server emojis
        emoji_section = ""
        if member and member.guild:
            emojis = self._get_server_emojis(member.guild)
            if emojis:
                emoji_section = f"\n\n=== SERVER EMOJIS ===\nYou can use these server emojis naturally in your responses:\n{emojis}\n"

        # Build full prompt
        prompt = f"""
{persona}

=== RELATIONSHIP STATUS ===
User's affection level: {affection_level.replace('_', ' ').upper()} ({affection_points} points)
{affection_context}

IMPORTANT: Your warmth, compliance, and willingness to help MUST match the affection level above.
Low affection = reserved, won't agree to demands. High affection = eager to please.

{gender_note}
{wellbeing_prompt}

{commands_help}{emoji_section}
{facts_section}

Recent conversation:
{context}

Current message from user:
{message}

Respond naturally in character. Keep responses concise.
"""
        return prompt
    
    async def generate_response(self, prompt: str, guild_id: int = None) -> str:
        """
        Generate a response using the appropriate AI provider.
        
        Args:
            prompt: The text prompt
            guild_id: Discord server ID (to check for evil mode)
        """
        # Check for evil (uncensored) mode
        evil_mode = False
        if guild_id:
            evil_mode = await get_evil_mode(guild_id)
            
        try:
            if evil_mode and self.openrouter.is_available():
                try:
                    response_text, model_used = await self.openrouter.generate(prompt)
                    return response_text
                except UserInputError:
                    raise
                except Exception as e:
                    logger.warning("OpenRouter failed, falling back to Gemini: %s", e)
            
            # Default to Gemini (censored)
            response_text, key_used = await self.gemini.generate(prompt)
            return response_text
            
        except UserInputError:
            return "Sorry, I can't help with that request."
        except RuntimeError as e:
            logger.warning("AI Generation failed: %s", e)
            return "Ah, I'm a bit overwhelmed right now... Please try again in a few minutes! >.< "
        except Exception as e:
            logger.error("AI Error: %s", e, exc_info=True)
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

        image_descriptions = []
        if message.attachments:
            image_descriptions = await self._describe_images(message)
        has_image_attachments = any(
            attachment.content_type and attachment.content_type.startswith("image/")
            for attachment in message.attachments
        )

        content_for_prompt = message.content
        if image_descriptions:
            image_context = self._format_image_descriptions(image_descriptions)
            if content_for_prompt.strip():
                content_for_prompt = f"{content_for_prompt}\n{image_context}"
            else:
                content_for_prompt = image_context
        
        # Always add message to context
        _, reply_to_username = self._resolve_reply_to(message)
        context.add_message(
            message.id,
            message.author.id,
            message.author.display_name,
            content_for_prompt,
            reply_to_username=reply_to_username
        )
        
        mentioned = self.bot.user in message.mentions
        content_lower = message.content.lower()
        mode = await get_server_mode(message.guild.id)
        
        # Check if we're in an active conversation with this user
        is_active = self._is_active_conversation(message.channel.id, message.author.id)
        has_trigger = self._has_trigger_word(content_lower, mode)
        
        # Determine if we should respond
        should_respond = mentioned or has_trigger or is_active
        
        if not should_respond:
            # Quick check for any trigger word (for performance)
            if not any(trigger in content_lower for trigger in ALL_TRIGGERS):
                return
            # No triggers, no active convo, skip
            return

        # Let other cogs handle mention-only messages without images
        if self._is_mention_only(message) and not image_descriptions:
            if has_image_attachments:
                await message.reply(
                    "I couldn't analyze that image. Try a smaller or supported format.",
                    mention_author=False
                )
            return

        # Rate limit AI responses per user
        if not await ai_limiter.acquire(message.author.id):
            retry_after = ai_limiter.get_retry_after(message.author.id)
            await message.reply(
                get_rate_limit_message(mode, retry_after),
                mention_author=False
            )
            return

        wellbeing_prompt, wellbeing_date = await self._get_wellbeing_prompt(
            message.author,
            message.guild.id,
            mode,
        )

        # Get reply context if user is replying to a message
        reply_context = await self._get_reply_context(message)
        if reply_context:
            content_for_prompt = f"{reply_context}\n{content_for_prompt}"
        
        # Show typing indicator
        async with message.channel.typing():
            # Build and send prompt
            prompt = await self.build_prompt(
                message.guild.id,
                message.author.id,
                content_for_prompt,
                context.get_context(),
                member=message.author,
                wellbeing_prompt=wellbeing_prompt
            )
            
            response = await self.generate_response(prompt, message.guild.id)
            
        sent = await message.reply(response, mention_author=False)

        # Manage conversation state
        if mentioned or has_trigger:
            # Fresh trigger - activate/refresh conversation
            self._refresh_conversation(message.channel.id, message.author.id)
        elif is_active:
            # Continuing active conversation - decrement remaining
            self._continue_conversation(message.channel.id, message.author.id)

        if wellbeing_date:
            await set_last_wellbeing_date(message.guild.id, message.author.id, wellbeing_date)

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
