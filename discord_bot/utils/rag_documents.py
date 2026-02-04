from __future__ import annotations

import hashlib
from io import BytesIO
from typing import List, Optional

from pypdf import PdfReader


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def extract_text_from_bytes(data: bytes, filename: str) -> Optional[str]:
    name = filename.lower()
    if name.endswith(".txt") or name.endswith(".md"):
        return _normalize_text(data.decode(errors="ignore"))
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text:
                    pages.append(text)
            return _normalize_text(" ".join(pages))
        except Exception:
            return None
    return None


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    text = _normalize_text(text or "")
    if not text:
        return []
    words = text.split()
    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks
