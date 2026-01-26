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
import random
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

GEMINI_MODELS = {
    "flash": "gemini-2.5-flash",
    "flash-lite": "gemini-2.5-flash-lite",
}


class GeminiSingleKeyManager:
    """
    Gemini API manager for a single, dedicated API key.
    """

    def __init__(self, key_env: str, request_timeout: Optional[float] = None):
        self.key_env = key_env
        self.api_key = os.getenv(key_env)
        if not self.api_key:
            raise ValueError(f"Missing required environment variable: {key_env}")

        self.text_model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
        self.vision_model_name = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
        if request_timeout is None:
            request_timeout = 30.0
        self.request_timeout = _parse_timeout(
            os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"),
            request_timeout,
        )

    async def generate(self, prompt: str) -> tuple[str, str]:
        """Generate content using the dedicated key."""
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    _generate_content_sync,
                    self.api_key,
                    self.text_model_name,
                    prompt,
                    None,
                ),
                timeout=self.request_timeout,
            )
        except Exception as e:
            error_str = str(e).lower()
            if _is_user_input_error(error_str):
                raise UserInputError(str(e)) from e
            raise

        return response.text, self.key_env


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


def _parse_int_env(
    value: Optional[str],
    fallback: int,
    name: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> int:
    if value is None:
        return fallback
    try:
        parsed = int(value)
    except ValueError:
        logger.warning("Invalid %s=%s; using %d", name, value, fallback)
        return fallback
    if min_value is not None and parsed < min_value:
        logger.warning("%s=%s below minimum %d; using %d", name, parsed, min_value, fallback)
        return fallback
    if max_value is not None and parsed > max_value:
        logger.warning("%s=%s above maximum %d; using %d", name, parsed, max_value, fallback)
        return fallback
    return parsed


def _parse_float_env(
    value: Optional[str],
    fallback: float,
    name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> float:
    if value is None:
        return fallback
    try:
        parsed = float(value)
    except ValueError:
        logger.warning("Invalid %s=%s; using %.2f", name, value, fallback)
        return fallback
    if min_value is not None and parsed < min_value:
        logger.warning("%s=%.2f below minimum %.2f; using %.2f", name, parsed, min_value, fallback)
        return fallback
    if max_value is not None and parsed > max_value:
        logger.warning("%s=%.2f above maximum %.2f; using %.2f", name, parsed, max_value, fallback)
        return fallback
    return parsed


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

    def set_text_model(self, model_name: str) -> None:
        """Override the text model name at runtime."""
        self.text_model_name = model_name

    def set_vision_model(self, model_name: str) -> None:
        """Override the vision model name at runtime."""
        self.vision_model_name = model_name
        
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

from openai import (
    AsyncOpenAI,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Available uncensored models
# venice/hermes/mistral = free tier (rate limited), deepseek = paid (no limits)
OPENROUTER_MODELS = {
    # Aliases
    "venice": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "hermes": "nousresearch/hermes-3-llama-3.1-405b:free",
    "dolphin": "cognitivecomputations/dolphin-mixtral-8x7b",
    "deephermes": "nousresearch/deephermes-3-mistral-24b-preview",
    "mistral": "mistralai/mistral-small-3.1-24b-instruct:free",
    "deepseek": "deepseek/deepseek-chat",

    # Full IDs (for direct use or fallback lists)
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "nousresearch/hermes-3-llama-3.1-405b:free": "nousresearch/hermes-3-llama-3.1-405b:free",
    "cognitivecomputations/dolphin-mixtral-8x7b": "cognitivecomputations/dolphin-mixtral-8x7b",
    "nousresearch/deephermes-3-mistral-24b-preview": "nousresearch/deephermes-3-mistral-24b-preview",
    "mistralai/mistral-small-3.1-24b-instruct:free": "mistralai/mistral-small-3.1-24b-instruct:free",
    "deepseek/deepseek-chat": "deepseek/deepseek-chat",
}


_OPENROUTER_MODEL_ERROR_HINTS = (
    "model",
    "not found",
    "unknown model",
    "no such model",
    "not available",
)


@dataclass
class OpenRouterModelState:
    """Track per-model cooldowns and error streaks."""
    model_id: str
    cooldown_until: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0

    def is_available(self) -> bool:
        if self.cooldown_until is None:
            return True
        if datetime.now() >= self.cooldown_until:
            self.cooldown_until = None
            return True
        return False

    def mark_success(self) -> None:
        self.success_count += 1
        self.error_count = 0

    def mark_cooldown(self, seconds: float) -> None:
        self.cooldown_until = datetime.now() + timedelta(seconds=seconds)


class OpenRouterManager:
    """
    OpenRouter API manager using OpenAI SDK for compatibility.
    
    Supports Venice Uncensored, Nous Hermes 3 405B, and DeepSeek.
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        raw_model = os.getenv("OPENROUTER_MODEL")
        if raw_model and raw_model.strip():
            self.model = raw_model.strip()
        else:
            self.model = "venice"
        self.request_timeout = _parse_timeout(
            os.getenv("OPENROUTER_REQUEST_TIMEOUT_SECONDS"),
            45.0
        )
        self.max_retries = _parse_int_env(
            os.getenv("OPENROUTER_MAX_RETRIES"),
            4,
            "OPENROUTER_MAX_RETRIES",
            min_value=1,
            max_value=10
        )
        self.retry_base_seconds = _parse_float_env(
            os.getenv("OPENROUTER_RETRY_BASE_SECONDS"),
            0.6,
            "OPENROUTER_RETRY_BASE_SECONDS",
            min_value=0.1,
            max_value=10.0
        )
        self.retry_max_seconds = _parse_float_env(
            os.getenv("OPENROUTER_RETRY_MAX_SECONDS"),
            6.0,
            "OPENROUTER_RETRY_MAX_SECONDS",
            min_value=1.0,
            max_value=30.0
        )
        self.model_cooldown_seconds = _parse_float_env(
            os.getenv("OPENROUTER_MODEL_COOLDOWN_SECONDS"),
            30.0,
            "OPENROUTER_MODEL_COOLDOWN_SECONDS",
            min_value=1.0,
            max_value=300.0
        )
        self.max_tokens = _parse_int_env(
            os.getenv("OPENROUTER_MAX_TOKENS"),
            2048,
            "OPENROUTER_MAX_TOKENS",
            min_value=64,
            max_value=8192
        )
        self.temperature = _parse_float_env(
            os.getenv("OPENROUTER_TEMPERATURE"),
            0.8,
            "OPENROUTER_TEMPERATURE",
            min_value=0.0,
            max_value=2.0
        )
        self.fallback_models = self._parse_model_list(
            os.getenv("OPENROUTER_FALLBACK_MODELS")
        )
        self._model_states: dict[str, OpenRouterModelState] = {}
        self._model_index = 0

        app_url = os.getenv("OPENROUTER_APP_URL", "https://github.com/gecallidryas/femboi")
        app_title = os.getenv("OPENROUTER_APP_TITLE", "Femmy Discord Bot")

        if self.api_key:
            self.client = AsyncOpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key,
                timeout=self.request_timeout,
                max_retries=0,
                default_headers={
                    "HTTP-Referer": app_url,
                    "X-Title": app_title
                }
            )
            logger.info("OpenRouter initialized with model: %s", self.model)
        else:
            self.client = None
            logger.warning("OPENROUTER_API_KEY not set - uncensored mode unavailable")
    
    def is_available(self) -> bool:
        """Check if OpenRouter is configured."""
        return self.client is not None
    
    def get_model_id(self) -> str:
        """Get the full model ID for API calls."""
        model_id = self._resolve_model_id(self.model)
        if not model_id:
            raise RuntimeError(f"Unknown OpenRouter model: {self.model}")
        return model_id

    def set_model(self, model_key: str) -> None:
        """Set the active OpenRouter model key."""
        if model_key not in OPENROUTER_MODELS and "/" not in model_key:
            raise ValueError(f"Unknown OpenRouter model: {model_key}")
        self.model = model_key

    def _parse_model_list(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _resolve_model_id(self, model_key_or_id: str) -> Optional[str]:
        if model_key_or_id in OPENROUTER_MODELS:
            return OPENROUTER_MODELS[model_key_or_id]
        if "/" in model_key_or_id:
            return model_key_or_id
        return None

    def _get_model_candidates(self) -> List[str]:
        if self.fallback_models:
            candidates = [self.model, *self.fallback_models]
        else:
            candidates = [self.model]

        resolved: List[str] = []
        unknown: List[str] = []
        for model_key in candidates:
            model_id = self._resolve_model_id(model_key)
            if not model_id:
                unknown.append(model_key)
                continue
            if model_id not in resolved:
                resolved.append(model_id)
            if model_id not in self._model_states:
                self._model_states[model_id] = OpenRouterModelState(model_id=model_id)

        if unknown:
            logger.warning("Ignoring unknown OpenRouter model keys: %s", ", ".join(unknown))

        if not resolved:
            raise RuntimeError(
                "No valid OpenRouter models configured. "
                "Check OPENROUTER_MODEL/OPENROUTER_FALLBACK_MODELS."
            )
        return resolved

    def _pick_model(self, candidates: List[str]) -> str:
        available = [model_id for model_id in candidates if self._model_states[model_id].is_available()]
        pool = available if available else candidates
        model_id = pool[self._model_index % len(pool)]
        self._model_index += 1
        return model_id

    def _get_status_code(self, error: Exception) -> Optional[int]:
        status = getattr(error, "status_code", None)
        if status is not None:
            return status
        response = getattr(error, "response", None)
        return getattr(response, "status_code", None)

    def _get_retry_after_seconds(self, error: Exception) -> Optional[float]:
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", None)
        if not headers:
            return None
        retry_after = headers.get("retry-after")
        if not retry_after:
            return None
        try:
            seconds = float(retry_after)
        except ValueError:
            return None
        if seconds < 0:
            return None
        return seconds

    def _get_backoff_delay(self, attempt: int, retry_after: Optional[float]) -> float:
        delay = min(self.retry_max_seconds, self.retry_base_seconds * (2 ** attempt))
        jitter = random.uniform(0, delay * 0.25)
        delay += jitter
        if retry_after is not None and retry_after > delay:
            delay = retry_after
        return delay

    def _classify_error(self, error: Exception) -> str:
        error_str = str(error).lower()
        if _is_user_input_error(error_str):
            return "user_input"
        if isinstance(error, (AuthenticationError, PermissionDeniedError)):
            return "fatal"
        if isinstance(error, (BadRequestError, UnprocessableEntityError)):
            if any(hint in error_str for hint in _OPENROUTER_MODEL_ERROR_HINTS):
                return "model_skip"
            return "fatal"
        if isinstance(error, NotFoundError):
            return "model_skip"
        if isinstance(error, RateLimitError):
            return "retry"
        if isinstance(error, (APITimeoutError, APIConnectionError, ConflictError)):
            return "retry"
        if isinstance(error, APIStatusError):
            status = self._get_status_code(error)
            if status in (408, 409, 425, 429) or (status is not None and status >= 500):
                return "retry"
            return "fatal"
        if _is_rate_limit_error(error_str):
            return "retry"
        return "retry"

    def _mark_model_error(
        self,
        model_id: str,
        cooldown: bool,
        retry_after: Optional[float] = None
    ) -> None:
        state = self._model_states.get(model_id)
        if not state:
            return
        state.error_count += 1
        if cooldown:
            cooldown_seconds = self.model_cooldown_seconds
            if retry_after is not None:
                cooldown_seconds = max(cooldown_seconds, retry_after)
            state.mark_cooldown(cooldown_seconds)

    async def _create_completion(self, model_id: str, prompt: str, fallbacks: List[str] = None):
        """Create completion with optional server-side fallback."""
        extra_body = {}
        if fallbacks:
            # OpenRouter server-side fallback - more reliable than client-side
            extra_body["models"] = [model_id, *fallbacks]
        
        return await self.client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            timeout=self.request_timeout,
            extra_body=extra_body if extra_body else None
        )

    def _extract_content(self, response) -> str:
        """Extract content with improved error detection."""
        if not response or not getattr(response, "choices", None):
            raise RuntimeError("OpenRouter returned no choices")

        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        
        # Check for error finish reason (OpenRouter can embed errors in responses)
        if finish_reason == "error":
            raise RuntimeError(f"OpenRouter finish_reason=error: {choice}")
        
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None) if message else None
        if not content:
            raise RuntimeError(f"OpenRouter returned empty content (finish_reason={finish_reason})")
        return content
    
    async def generate(self, prompt: str) -> tuple[str, str]:
        """
        Generate a response using OpenRouter API.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Tuple of (response_text, model_used)
        """
        if not self.client:
            raise RuntimeError("OpenRouter API key not configured")

        candidates = self._get_model_candidates()
        max_attempts = max(self.max_retries, len(candidates))
        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            model_id = self._pick_model(candidates)
            fallbacks = [m for m in candidates if m != model_id]
            try:
                response = await self._create_completion(model_id, prompt, fallbacks)
                content = self._extract_content(response)
                self._model_states[model_id].mark_success()
                logger.info("Generated response using OpenRouter (%s)", model_id)
                return content, model_id
            except UserInputError:
                raise
            except Exception as e:
                last_error = e
                classification = self._classify_error(e)
                if classification == "user_input":
                    raise UserInputError(str(e)) from e
                if classification == "fatal":
                    logger.error("OpenRouter fatal error: %s", e)
                    raise RuntimeError(f"OpenRouter API error: {e}") from e
                if classification == "model_skip":
                    self._mark_model_error(model_id, cooldown=False)
                    logger.warning("OpenRouter model failed (%s), trying fallback: %s", model_id, e)
                    continue

                retry_after = self._get_retry_after_seconds(e)
                self._mark_model_error(model_id, cooldown=True, retry_after=retry_after)
                delay = self._get_backoff_delay(attempt, retry_after)
                logger.warning("OpenRouter retry in %.2fs after error: %s", delay, e)
                await asyncio.sleep(delay)

        error_msg = f"OpenRouter failed after {max_attempts} attempts"
        if last_error:
            error_msg += f". Last error: {last_error}"
        raise RuntimeError(error_msg)


# Global OpenRouter instance
_openrouter_manager: Optional[OpenRouterManager] = None


def get_openrouter_manager() -> OpenRouterManager:
    """Get or create the global OpenRouter manager."""
    global _openrouter_manager
    if _openrouter_manager is None:
        _openrouter_manager = OpenRouterManager()
    return _openrouter_manager


def set_openrouter_model(model_key: str) -> bool:
    """Set the OpenRouter model by key."""
    manager = get_openrouter_manager()
    if not manager.is_available():
        return False
    if model_key not in OPENROUTER_MODELS and "/" not in model_key:
        return False
    manager.set_model(model_key)
    return True


def set_gemini_model(model_key: str) -> bool:
    """Set the Gemini model by key."""
    manager = get_gemini_manager()
    model_name = GEMINI_MODELS.get(model_key)
    if model_name is None:
        if model_key in GEMINI_MODELS.values():
            model_name = model_key
        else:
            return False
    manager.set_text_model(model_name)
    manager.set_vision_model(model_name)
    return True


# ============================================
# Dedicated Gemini Managers (Translate/Summarize)
# ============================================

_translate_manager: Optional[GeminiSingleKeyManager] = None
_summarize_manager: Optional[GeminiSingleKeyManager] = None


def get_gemini_translate_manager() -> GeminiSingleKeyManager:
    """Get or create the Gemini manager for translation."""
    global _translate_manager
    if _translate_manager is None:
        _translate_manager = GeminiSingleKeyManager("GEMINI_TRANSLATE_KEY")
    return _translate_manager


def get_gemini_summarize_manager() -> GeminiSingleKeyManager:
    """Get or create the Gemini manager for summarization."""
    global _summarize_manager
    if _summarize_manager is None:
        _summarize_manager = GeminiSingleKeyManager("GEMINI_SUMMARIZE_KEY")
    return _summarize_manager


_profile_manager: Optional[GeminiSingleKeyManager] = None


def get_gemini_profile_manager() -> GeminiSingleKeyManager:
    """Get or create the Gemini manager for user profile analysis."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = GeminiSingleKeyManager("GEMINI_PROFILE_KEY")
    return _profile_manager
