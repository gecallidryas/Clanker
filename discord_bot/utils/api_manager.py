"""
API Key Manager for Femmy Discord Bot
=======================================
Manages multiple Gemini API keys with automatic rotation and failover.

Features:
    - Load multiple API keys from environment
    - Automatic failover on rate limit/error
    - Track exhausted keys with cooldown
    - Round-robin distribution for load balancing

Usage:
    from utils.api_manager import GeminiManager
    
    manager = GeminiManager()
    response = await manager.generate(prompt)
"""

import os
import asyncio
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List
import google.generativeai as genai
import aiohttp

from utils.logger import get_logger

logger = get_logger(__name__)


class UserInputError(RuntimeError):
    """Raised when the request fails due to user input or content policy."""


_GENAI_CALL_LOCK = threading.Lock()  # genai.configure is global; serialize per call.

_RATE_LIMIT_HINTS = (
    "rate limit",
    "ratelimit",
    "quota",
    "too many requests",
    "429",
    "exhausted",
)

_USER_INPUT_HINTS = (
    "safety",
    "blocked",
    "unsafe",
    "harm",
    "content policy",
    "policy violation",
    "prohibited",
    "disallowed",
)

_USER_INPUT_TOKEN_HINTS = (
    "too many tokens",
    "token limit",
    "context length",
    "context window",
    "input too long",
    "request too large",
)


def _is_rate_limit_error(error_str: str) -> bool:
    if any(hint in error_str for hint in _RATE_LIMIT_HINTS):
        return True
    return "limit" in error_str and any(hint in error_str for hint in ("rate", "quota", "requests", "429"))


def _is_user_input_error(error_str: str) -> bool:
    if any(hint in error_str for hint in _USER_INPUT_HINTS):
        return True
    if any(hint in error_str for hint in _USER_INPUT_TOKEN_HINTS):
        return True
    if "invalid argument" in error_str and any(hint in error_str for hint in ("prompt", "input", "content")):
        return True
    if "bad request" in error_str and any(hint in error_str for hint in ("prompt", "input", "content")):
        return True
    return False


def _parse_timeout(value: Optional[str], fallback: float) -> float:
    if value is None:
        return fallback
    try:
        timeout = float(value)
    except ValueError:
        logger.warning("Invalid GEMINI_REQUEST_TIMEOUT_SECONDS=%s; using %.1fs", value, fallback)
        return fallback
    if timeout <= 0:
        logger.warning("Non-positive GEMINI_REQUEST_TIMEOUT_SECONDS=%s; using %.1fs", value, fallback)
        return fallback
    return timeout


def _generate_content_sync(api_key: str, model_name: str, prompt: str, image) -> object:
    # Maximum permissive safety settings - BLOCK_NONE
    # Note: Google may still block PROHIBITED_CONTENT regardless of settings
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    with _GENAI_CALL_LOCK:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        if image is None:
            return model.generate_content(prompt, safety_settings=safety_settings)
        return model.generate_content([prompt, image], safety_settings=safety_settings)


@dataclass
class APIKey:
    """Represents a single API key with status tracking."""
    key: str
    name: str  # e.g., "GEMINI_API_KEY_1"
    is_exhausted: bool = False
    exhausted_at: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0
    
    def mark_exhausted(self, cooldown_minutes: int = 5):
        """Mark key as temporarily exhausted."""
        self.is_exhausted = True
        self.exhausted_at = datetime.now()
        logger.warning(f"API key {self.name} marked exhausted, cooldown {cooldown_minutes}m")
    
    def check_cooldown(self, cooldown_minutes: int = 5) -> bool:
        """Check if cooldown has passed and reset if so."""
        if not self.is_exhausted:
            return True
        
        if self.exhausted_at is None:
            self.is_exhausted = False
            return True
        
        elapsed = datetime.now() - self.exhausted_at
        if elapsed >= timedelta(minutes=cooldown_minutes):
            self.is_exhausted = False
            self.exhausted_at = None
            logger.info(f"API key {self.name} cooldown expired, available again")
            return True
        
        return False
    
    def mark_success(self):
        """Mark a successful request."""
        self.success_count += 1
        self.error_count = 0  # Reset error streak


class GeminiManager:
    """
    Manages multiple Gemini API keys with automatic failover.
    
    Environment Variables:
        GEMINI_API_KEY   - Primary key (required)
        GEMINI_API_KEY_2 - Second key (optional)
        GEMINI_API_KEY_3 - Third key (optional)
        ... up to GEMINI_API_KEY_10
        GEMINI_TEXT_MODEL   - Optional text model name (default: gemini-2.5-flash)
        GEMINI_VISION_MODEL - Optional vision model name (default: gemini-2.5-flash)
        GEMINI_REQUEST_TIMEOUT_SECONDS - Optional request timeout (default: 30)
    """
    
    def __init__(self, cooldown_minutes: int = 5, request_timeout: Optional[float] = None):
        self.cooldown_minutes = cooldown_minutes
        self.keys: List[APIKey] = []
        self.current_index = 0
        self.text_model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
        self.vision_model_name = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
        if request_timeout is None:
            request_timeout = 30.0
        self.request_timeout = _parse_timeout(
            os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"),
            request_timeout
        )
        
        self._load_keys()
    
    def _load_keys(self):
        """Load all available API keys from environment."""
        # Primary key
        primary = os.getenv("GEMINI_API_KEY")
        if primary:
            self.keys.append(APIKey(key=primary, name="GEMINI_API_KEY"))
        
        # Additional keys (2-10)
        for i in range(2, 11):
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if key:
                self.keys.append(APIKey(key=key, name=f"GEMINI_API_KEY_{i}"))
        
        if not self.keys:
            raise ValueError("No Gemini API keys found! Set GEMINI_API_KEY in .env")
        
        logger.info(f"Loaded {len(self.keys)} Gemini API key(s)")
        
    def _get_next_key(self) -> Optional[APIKey]:
        """Get next available API key using round-robin."""
        checked = 0
        total = len(self.keys)
        
        while checked < total:
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % total
            
            if key.check_cooldown(self.cooldown_minutes):
                return key
            
            checked += 1
        
        return None  # All keys exhausted
    
    def get_status(self) -> dict:
        """Get status of all API keys."""
        return {
            "total_keys": len(self.keys),
            "available": sum(1 for k in self.keys if not k.is_exhausted),
            "exhausted": sum(1 for k in self.keys if k.is_exhausted),
            "keys": [
                {
                    "name": k.name,
                    "available": not k.is_exhausted,
                    "success_count": k.success_count,
                    "error_count": k.error_count
                }
                for k in self.keys
            ]
        }
    
    async def generate(
        self,
        prompt: str,
        max_retries: int = None
    ) -> tuple[str, str]:
        """
        Generate content using available API keys with automatic failover.
        
        Args:
            prompt: The prompt to send
            max_retries: Maximum keys to try (default: all keys)
            
        Returns:
            Tuple of (response_text, key_name_used)
            
        Raises:
            RuntimeError: If all keys are exhausted
            UserInputError: If the request is rejected due to user input
            TimeoutError: If the request times out
        """
        if max_retries is None:
            max_retries = len(self.keys)
        
        last_error = None
        attempts = 0
        
        while attempts < max_retries:
            api_key = self._get_next_key()
            
            if api_key is None:
                break
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        _generate_content_sync,
                        api_key.key,
                        self.text_model_name,
                        prompt,
                        None
                    ),
                    timeout=self.request_timeout
                )
                
                api_key.mark_success()
                logger.info(f"Generated response using {api_key.name}")
                
                return response.text, api_key.name
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limit or quota errors
                if _is_user_input_error(error_str):
                    logger.info("User input error from %s: %s", api_key.name, e)
                    raise UserInputError(str(e)) from e
                if isinstance(e, TimeoutError):
                    api_key.error_count += 1
                    if api_key.error_count >= 3:
                        api_key.mark_exhausted(self.cooldown_minutes)
                    logger.warning("Key %s request timed out after %.1fs", api_key.name, self.request_timeout)
                elif _is_rate_limit_error(error_str):
                    api_key.error_count += 1
                    api_key.mark_exhausted(self.cooldown_minutes)
                    logger.warning(f"Key {api_key.name} rate limited: {e}")
                else:
                    # Other error - might be temporary, increment error but don't exhaust
                    api_key.error_count += 1
                    if api_key.error_count >= 3:
                        api_key.mark_exhausted(self.cooldown_minutes)
                    logger.error(f"Key {api_key.name} error: {e}")
                
                last_error = e
                attempts += 1
        
        # All keys failed
        error_msg = f"All {len(self.keys)} API keys exhausted or failed"
        if last_error:
            error_msg += f". Last error: {last_error}"
        
        raise RuntimeError(error_msg)
    
    async def generate_with_vision(
        self,
        prompt: str,
        image,
        max_retries: int = None
    ) -> tuple[str, str]:
        """
        Generate content with image using available API keys.
        
        Args:
            prompt: The prompt to send
            image: PIL Image object
            max_retries: Maximum keys to try
            
        Returns:
            Tuple of (response_text, key_name_used)
            
        Raises:
            RuntimeError: If all keys are exhausted
            UserInputError: If the request is rejected due to user input
            TimeoutError: If the request times out
        """
        if max_retries is None:
            max_retries = len(self.keys)
        
        last_error = None
        attempts = 0
        
        while attempts < max_retries:
            api_key = self._get_next_key()
            
            if api_key is None:
                break
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        _generate_content_sync,
                        api_key.key,
                        self.vision_model_name,
                        prompt,
                        image
                    ),
                    timeout=self.request_timeout
                )
                
                api_key.mark_success()
                logger.info(f"Generated vision response using {api_key.name}")
                
                return response.text, api_key.name
                
            except Exception as e:
                error_str = str(e).lower()
                
                if _is_user_input_error(error_str):
                    logger.info("User input error from %s: %s", api_key.name, e)
                    raise UserInputError(str(e)) from e
                if isinstance(e, TimeoutError):
                    api_key.error_count += 1
                    if api_key.error_count >= 3:
                        api_key.mark_exhausted(self.cooldown_minutes)
                    logger.warning("Key %s request timed out after %.1fs", api_key.name, self.request_timeout)
                elif _is_rate_limit_error(error_str):
                    api_key.error_count += 1
                    api_key.mark_exhausted(self.cooldown_minutes)
                    logger.warning(f"Key {api_key.name} rate limited: {e}")
                else:
                    api_key.error_count += 1
                    if api_key.error_count >= 3:
                        api_key.mark_exhausted(self.cooldown_minutes)
                    logger.error(f"Key {api_key.name} error: {e}")
                
                last_error = e
                attempts += 1
        
        raise RuntimeError(f"All API keys exhausted. Last error: {last_error}")


# ============================================
# Global Instance
# ============================================

# Lazy initialization to avoid import-time errors
_manager: Optional[GeminiManager] = None


def get_gemini_manager() -> GeminiManager:
    """Get or create the global Gemini manager."""
    global _manager
    if _manager is None:
        _manager = GeminiManager()
    return _manager


# ============================================
# OpenRouter Integration (Uncensored Models)
# ============================================

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Available uncensored models
OPENROUTER_MODELS = {
    "venice": "venice-ai/venice-uncensored",
    "hermes": "nousresearch/hermes-3-llama-3.1-405b",
}


class OpenRouterManager:
    """
    OpenRouter API manager for uncensored AI models.
    
    Supports Venice Uncensored and Nous Hermes 3 405B.
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL", "venice")
        self.timeout = 60
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set - uncensored mode unavailable")
    
    def is_available(self) -> bool:
        """Check if OpenRouter is configured."""
        return bool(self.api_key)
    
    def get_model_id(self) -> str:
        """Get the full model ID for API calls."""
        return OPENROUTER_MODELS.get(self.model, OPENROUTER_MODELS["venice"])
    
    async def generate(self, prompt: str) -> tuple[str, str]:
        """
        Generate a response using OpenRouter API.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Tuple of (response_text, model_used)
        """
        if not self.api_key:
            raise RuntimeError("OpenRouter API key not configured")
        
        model_id = self.get_model_id()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/gecallidryas/femboi",
            "X-Title": "Femmy Discord Bot"
        }
        
        payload = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.8
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenRouter error {response.status}: {error_text}")
                        raise RuntimeError(f"OpenRouter API error: {response.status}")
                    
                    data = await response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"Generated response using OpenRouter ({model_id})")
                        return content, model_id
                    else:
                        raise RuntimeError("OpenRouter returned empty response")
                        
        except asyncio.TimeoutError:
            logger.error("OpenRouter request timed out")
            raise RuntimeError("OpenRouter request timed out")
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise


# Global OpenRouter instance
_openrouter_manager: Optional[OpenRouterManager] = None


def get_openrouter_manager() -> OpenRouterManager:
    """Get or create the global OpenRouter manager."""
    global _openrouter_manager
    if _openrouter_manager is None:
        _openrouter_manager = OpenRouterManager()
    return _openrouter_manager
