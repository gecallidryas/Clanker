from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class ContextSection:
    title: str
    body: str


def _clean_lines(lines: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        text = (line or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def section_from_lines(title: str, lines: Iterable[str]) -> ContextSection | None:
    items = _clean_lines(lines)
    if not items:
        return None
    return ContextSection(title=title, body="\n".join(f"- {item}" for item in items))


def section_from_text(title: str, text: str) -> ContextSection | None:
    content = (text or "").strip()
    if not content:
        return None
    return ContextSection(title=title, body=content)


def render_structured_context(sections: Iterable[ContextSection]) -> str:
    blocks: List[str] = []
    for section in sections:
        title = section.title.strip()
        body = section.body.strip()
        if not title or not body:
            continue
        blocks.append(f"=== {title} ===\n{body}")
    return "\n\n".join(blocks)


def build_structured_prompt(
    persona: str,
    sections: Iterable[ContextSection],
    current_message: str,
    final_instruction: str,
) -> str:
    persona_block = (persona or "").strip()
    context_block = render_structured_context(sections)
    message_block = (current_message or "").strip()
    instruction_block = (final_instruction or "").strip()

    parts: list[str] = []
    if persona_block:
        parts.append(persona_block)
    if context_block:
        parts.append(context_block)
    if instruction_block:
        parts.append("=== RESPONSE STYLE ===")
        parts.append(instruction_block)
    parts.append("=== CURRENT MESSAGE ===")
    parts.append(message_block or "(empty)")
    return "\n\n".join(parts).strip()
