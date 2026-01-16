"""
Sentiment Analysis Utility for Femmy Discord Bot
=================================================
AI-assisted sentiment detection for negativity detection.

Uses Gemini API to analyze message tone and determine if it's:
- Positive (friendly, kind, supportive)
- Neutral (normal conversation)
- Negative (rude, hostile, dismissive)
"""

from typing import Tuple, Optional
from utils.api_manager import get_gemini_manager, UserInputError
from utils.logger import get_logger

logger = get_logger(__name__)

# Sentiment categories and their affection impact
SENTIMENT_IMPACTS = {
    "very_positive": 5,
    "positive": 2,
    "neutral": 1,
    "negative": -3,
    "very_negative": -10,
    "hostile": -15
}


async def analyze_sentiment(message: str, bot_name: str = "Femmy") -> Tuple[str, int]:
    """
    Analyze the sentiment of a message using Gemini.
    
    Args:
        message: The message to analyze
        bot_name: The bot's name for context
        
    Returns:
        Tuple of (sentiment_category, affection_delta)
    """
    if not message or len(message.strip()) < 3:
        return "neutral", SENTIMENT_IMPACTS["neutral"]
    
    gemini = get_gemini_manager()
    
    prompt = f"""
Analyze the sentiment of this message directed at {bot_name} (a Discord bot with a cute personality).

Message: "{message}"

Classify as EXACTLY one of these categories:
- very_positive (loving, extremely supportive, compliments)
- positive (friendly, appreciative, kind)
- neutral (normal conversation, questions, requests)
- negative (dismissive, slightly rude, impatient)
- very_negative (insulting, mean, aggressive)
- hostile (extremely rude, threatening, abusive)

Respond with ONLY the category name, nothing else.
"""
    
    try:
        response, _ = await gemini.generate(prompt)
        sentiment = response.strip().lower().replace(" ", "_")
        
        # Validate response
        if sentiment in SENTIMENT_IMPACTS:
            logger.debug(f"Sentiment for '{message[:30]}...': {sentiment}")
            return sentiment, SENTIMENT_IMPACTS[sentiment]
        else:
            # Default to neutral if response is unexpected
            logger.warning(f"Unexpected sentiment response: {response}")
            return "neutral", SENTIMENT_IMPACTS["neutral"]
            
    except UserInputError:
        # Content was blocked, might be hostile
        logger.info("Message blocked by safety - treating as negative")
        return "negative", SENTIMENT_IMPACTS["negative"]
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return "neutral", SENTIMENT_IMPACTS["neutral"]


async def is_negative_message(message: str) -> Tuple[bool, int]:
    """
    Quick check if a message is negative.
    
    Returns:
        Tuple of (is_negative, affection_delta)
    """
    sentiment, delta = await analyze_sentiment(message)
    is_negative = sentiment in ("negative", "very_negative", "hostile")
    return is_negative, delta


# Quick keyword-based fallback (no API calls)
NEGATIVE_KEYWORDS = {
    "stupid", "dumb", "idiot", "shut up", "hate you", "annoying",
    "useless", "terrible", "worst", "garbage", "trash", "die",
    "kys", "stfu", "gtfo", "fk", "fck"
}

POSITIVE_KEYWORDS = {
    "love", "thank", "thanks", "awesome", "amazing", "great",
    "good job", "well done", "appreciate", "helpful", "cute",
    "sweet", "kind", "best", "wonderful", "fantastic"
}


def quick_sentiment_check(message: str) -> Optional[Tuple[str, int]]:
    """
    Fast keyword-based sentiment check (no API call).
    Returns None if unsure, use AI analysis instead.
    """
    msg_lower = message.lower()
    
    # Check for strong negative keywords
    for keyword in NEGATIVE_KEYWORDS:
        if keyword in msg_lower:
            return "negative", SENTIMENT_IMPACTS["negative"]
    
    # Check for positive keywords
    for keyword in POSITIVE_KEYWORDS:
        if keyword in msg_lower:
            return "positive", SENTIMENT_IMPACTS["positive"]
    
    return None  # Unsure, use AI
