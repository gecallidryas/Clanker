"""
Rate Limiter for Femmy Discord Bot
====================================
Token bucket rate limiter for per-user API request limiting.

Features:
    - Configurable rate (default: 10 requests per 60 seconds)
    - Per-user tracking with automatic cleanup
    - Async-safe implementation
    - Personality-aware rate limit messages

Usage:
    from utils.rate_limiter import RateLimiter, get_rate_limit_message
    
    limiter = RateLimiter(rate=10, per=60)
    
    if not await limiter.acquire(user_id):
        retry_after = limiter.get_retry_after(user_id)
        await ctx.send(get_rate_limit_message(mode, retry_after))
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    tokens: float
    last_update: datetime
    max_tokens: int
    refill_rate: float  # tokens per second


class RateLimiter:
    """
    Per-user rate limiter using token bucket algorithm.
    
    Attributes:
        rate: Number of requests allowed
        per: Time period in seconds
        buckets: User ID -> TokenBucket mapping
    """
    
    def __init__(self, rate: int = 10, per: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed (default: 10)
            per: Time period in seconds (default: 60)
        """
        self.rate = rate
        self.per = per
        self.refill_rate = rate / per  # tokens per second
        self.buckets: Dict[int, TokenBucket] = {}
        self._lock = asyncio.Lock()
        self._cleanup_threshold = 1000  # Cleanup when this many users tracked
    
    def _get_bucket(self, user_id: int) -> TokenBucket:
        """Get or create token bucket for user."""
        if user_id not in self.buckets:
            self.buckets[user_id] = TokenBucket(
                tokens=self.rate,
                last_update=datetime.now(),
                max_tokens=self.rate,
                refill_rate=self.refill_rate
            )
        return self.buckets[user_id]
    
    def _refill_bucket(self, bucket: TokenBucket) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.now()
        elapsed = (now - bucket.last_update).total_seconds()
        
        # Add tokens based on elapsed time
        bucket.tokens = min(
            bucket.max_tokens,
            bucket.tokens + (elapsed * bucket.refill_rate)
        )
        bucket.last_update = now
    
    async def acquire(self, user_id: int, tokens: int = 1) -> bool:
        """
        Try to acquire tokens for a request.
        
        Args:
            user_id: Discord user ID
            tokens: Number of tokens to acquire (default: 1)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            bucket = self._get_bucket(user_id)
            self._refill_bucket(bucket)
            
            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                return True
            
            return False
    
    def get_retry_after(self, user_id: int) -> float:
        """
        Get seconds until next request is allowed.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Seconds to wait before retry
        """
        if user_id not in self.buckets:
            return 0.0
        
        bucket = self.buckets[user_id]
        self._refill_bucket(bucket)
        
        if bucket.tokens >= 1:
            return 0.0
        
        # Calculate time needed to refill 1 token
        tokens_needed = 1 - bucket.tokens
        return tokens_needed / bucket.refill_rate
    
    async def cleanup_old_buckets(self, max_age_hours: int = 1) -> int:
        """
        Remove buckets that haven't been used recently.
        
        Args:
            max_age_hours: Remove buckets older than this
            
        Returns:
            Number of buckets removed
        """
        async with self._lock:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            old_buckets = [
                uid for uid, bucket in self.buckets.items()
                if bucket.last_update < cutoff
            ]
            
            for uid in old_buckets:
                del self.buckets[uid]
            
            return len(old_buckets)
    
    def get_usage(self, user_id: int) -> tuple[float, int]:
        """
        Get current usage for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (remaining_tokens, max_tokens)
        """
        if user_id not in self.buckets:
            return (float(self.rate), self.rate)
        
        bucket = self.buckets[user_id]
        self._refill_bucket(bucket)
        return (bucket.tokens, bucket.max_tokens)


# ============================================
# Personality-Aware Messages
# ============================================

RATE_LIMIT_MESSAGES = {
    "mode_femboy": [
        "S-sorry, Nii-chan! I need a little break~ Try again in {seconds}s! ♡",
        "Ehehe, I'm a bit tired... Wait {seconds}s for me? ✨",
        "I-I'll be ready soon! Just {seconds}s more~ >.<"
    ],
    "mode_tsundere": [
        "Hmph! You're way too demanding! Wait {seconds}s, baka!",
        "I-it's not like I'm ignoring you! I just need {seconds}s. Hmph!",
        "Slow down! {seconds}s, then I'll help... maybe."
    ],
    "mode_oneesan": [
        "Ara ara~ Slow down, dear. Take a breath for {seconds}s~",
        "My my, so eager! Rest for {seconds}s, okay? ♡",
        "Patience, little one. I'll be ready in {seconds}s~"
    ]
}


def get_rate_limit_message(mode: str, retry_after: float) -> str:
    """
    Get a personality-appropriate rate limit message.
    
    Args:
        mode: Current persona mode
        retry_after: Seconds until next request allowed
        
    Returns:
        Formatted rate limit message
    """
    import random
    
    messages = RATE_LIMIT_MESSAGES.get(mode, RATE_LIMIT_MESSAGES["mode_femboy"])
    message = random.choice(messages)
    
    return message.format(seconds=int(retry_after) + 1)


# ============================================
# Global Instance
# ============================================

# Shared rate limiter for AI commands (10 per minute)
ai_limiter = RateLimiter(rate=10, per=60)
