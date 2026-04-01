from __future__ import annotations

from typing import Any, Iterable, Sequence

from utils.api_manager import UserInputError, get_gemini_summarize_manager
from utils.logger import get_logger

logger = get_logger(__name__)

FACT_RECONCILE_PROMPT = """You are a database reconciler.
Reconcile these {scope_label} entries and keep only non-contradictory truths.
Rules:
- Remove duplicates.
- If two entries directly contradict, remove both and keep only a neutral replacement if possible.
- Keep output concise.
- Return ONLY a bulleted list, one entry per line.

Existing entries:
{existing_entries}

New entry:
{new_entry}
"""

ATTRIBUTE_RECONCILE_PROMPT = """You are a database reconciler for persona attributes.
Reconcile existing attributes with a new attribute update.
Rules:
- Remove duplicates and contradictions.
- Keep only stable current attributes.
- Return ONLY a bulleted list.
- Each bullet MUST use this exact format: attribute = value

Existing attributes:
{existing_entries}

New attribute:
{new_entry}
"""

DIALOGUE_RECONCILE_PROMPT = """You are a database reconciler for sample dialogue.
Reconcile existing sample dialogue with the new line.
Rules:
- Remove exact duplicates.
- Remove contradictory or low-signal lines.
- Keep a compact set of representative lines.
- Return ONLY a bulleted list.
- Each bullet MUST use this exact format: speaker || dialogue

Existing sample dialogue:
{existing_entries}

New sample dialogue:
{new_entry}
"""


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = (item or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item.strip())
    return output


class DatabaseSummarizer:
    def __init__(self, summarizer=None):
        if summarizer is not None:
            self.summarizer = summarizer
            return
        try:
            self.summarizer = get_gemini_summarize_manager()
        except ValueError:
            self.summarizer = None

    def _parse_bulleted_lines(self, summary_text: str) -> list[str]:
        if not summary_text:
            return []
        lines: list[str] = []
        for line in summary_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped[0] in ("-", "*"):
                stripped = stripped[1:].strip()
            if stripped:
                lines.append(stripped)
        return _dedupe_preserve_order(lines)

    async def _summarize_lines(self, prompt: str) -> list[str] | None:
        if not self.summarizer:
            return None
        try:
            summary_text, _ = await self.summarizer.generate(prompt)
        except UserInputError:
            return None
        except Exception as exc:
            logger.warning("Database summarizer failed: %s", exc)
            return None

        parsed = self._parse_bulleted_lines(summary_text)
        return parsed or None

    async def summarize_fact_entries(
        self,
        existing: Sequence[str],
        new_entry: str,
        scope_label: str = "memory",
    ) -> list[str] | None:
        prompt = FACT_RECONCILE_PROMPT.format(
            scope_label=scope_label,
            existing_entries="\n".join(f"- {item}" for item in existing) or "(none)",
            new_entry=new_entry,
        )
        return await self._summarize_lines(prompt)

    async def summarize_attributes(
        self,
        existing: Sequence[dict[str, Any]],
        attribute: str,
        value: str,
    ) -> list[tuple[str, str]] | None:
        existing_lines = [
            f"{str(item.get('attribute') or '').strip()} = {str(item.get('value') or '').strip()}"
            for item in existing
            if str(item.get("attribute") or "").strip() and str(item.get("value") or "").strip()
        ]
        prompt = ATTRIBUTE_RECONCILE_PROMPT.format(
            existing_entries="\n".join(f"- {line}" for line in existing_lines) or "(none)",
            new_entry=f"{attribute} = {value}",
        )
        parsed = await self._summarize_lines(prompt)
        if not parsed:
            return None

        output: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for line in parsed:
            if "=" not in line:
                continue
            raw_attribute, raw_value = line.split("=", 1)
            clean_attribute = raw_attribute.strip()
            clean_value = raw_value.strip()
            if not clean_attribute or not clean_value:
                continue
            key = (clean_attribute.lower(), clean_value.lower())
            if key in seen:
                continue
            seen.add(key)
            output.append((clean_attribute, clean_value))
        return output or None

    async def summarize_sample_dialogues(
        self,
        existing: Sequence[dict[str, Any]],
        speaker: str,
        dialogue: str,
    ) -> list[tuple[str, str]] | None:
        existing_lines = [
            f"{str(item.get('speaker') or '').strip()} || {str(item.get('dialogue') or '').strip()}"
            for item in existing
            if str(item.get("speaker") or "").strip() and str(item.get("dialogue") or "").strip()
        ]
        prompt = DIALOGUE_RECONCILE_PROMPT.format(
            existing_entries="\n".join(f"- {line}" for line in existing_lines) or "(none)",
            new_entry=f"{speaker} || {dialogue}",
        )
        parsed = await self._summarize_lines(prompt)
        if not parsed:
            return None

        output: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for line in parsed:
            if "||" not in line:
                continue
            raw_speaker, raw_dialogue = line.split("||", 1)
            clean_speaker = raw_speaker.strip()
            clean_dialogue = raw_dialogue.strip()
            if not clean_speaker or not clean_dialogue:
                continue
            key = (clean_speaker.lower(), clean_dialogue.lower())
            if key in seen:
                continue
            seen.add(key)
            output.append((clean_speaker, clean_dialogue))
        return output or None
