"""
Encryption helpers for guild-specific API keys.
"""

from __future__ import annotations

import os
from typing import Optional

from cryptography.fernet import Fernet

from utils.logger import get_logger

logger = get_logger(__name__)

_encryption: Optional["KeyEncryption"] = None


class KeyEncryption:
    """Fernet-based encryption for API keys."""

    def __init__(self) -> None:
        master_key = os.getenv("ENCRYPTION_KEY")
        if not master_key:
            raise RuntimeError(
                "ENCRYPTION_KEY not set! Required for guild API key storage. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        try:
            self._fernet = Fernet(master_key.encode())
        except Exception as exc:
            raise RuntimeError(f"Invalid ENCRYPTION_KEY format: {exc}") from exc

    def encrypt(self, plaintext: str) -> str:
        """Encrypt and return base64 ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64 ciphertext."""
        return self._fernet.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def mask_key(key: str) -> str:
        """Mask API key for display."""
        if not key:
            return "****"
        if len(key) <= 8:
            return "****"
        return f"****...****{key[-4:]}"


def get_encryption() -> KeyEncryption:
    """Get a singleton KeyEncryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = KeyEncryption()
    return _encryption
