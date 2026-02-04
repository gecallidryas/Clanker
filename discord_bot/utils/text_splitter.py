from __future__ import annotations

from typing import List

DISCORD_MESSAGE_LIMIT = 2000
DEFAULT_CHUNK_LIMIT = 1900


def split_message(text: str, limit: int = DEFAULT_CHUNK_LIMIT) -> list[str]:
    """Split text into Discord-sized chunks, preserving code blocks when possible."""
    if text is None:
        return [""]
    text = str(text)
    if len(text) <= limit:
        return [text]

    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    current = ""
    in_code = False
    fence = ""

    def flush() -> None:
        nonlocal current
        if not current:
            return
        if in_code:
            if not current.endswith("\n"):
                current += "\n"
            current += "```"
        chunks.append(current.rstrip("\n"))
        current = ""
        if in_code:
            current = fence + "\n"

    for line in lines:
        # Handle very long lines by splitting them directly
        if len(line) > limit:
            if current:
                flush()
            if in_code:
                payload_limit = max(1, limit - (len(fence) + 5))
                start = 0
                while start < len(line):
                    payload = line[start : start + payload_limit]
                    chunk = f"{fence}\n{payload}"
                    if not chunk.endswith("\n"):
                        chunk += "\n"
                    chunk += "```"
                    chunks.append(chunk.rstrip("\n"))
                    start += payload_limit
            else:
                start = 0
                while start < len(line):
                    chunk = line[start : start + limit]
                    chunks.append(chunk.rstrip("\n"))
                    start += limit
            continue

        if len(current) + len(line) > limit:
            flush()

        current += line

        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                in_code = False
                fence = ""
            else:
                in_code = True
                fence = stripped

    if current:
        if in_code:
            if not current.endswith("\n"):
                current += "\n"
            current += "```"
        chunks.append(current.rstrip("\n"))

    return chunks
