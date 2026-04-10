from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import json
import re
from pathlib import Path
from typing import Optional, Sequence

import discord
from PIL import Image

from utils.db_handler import DATA_DIR, sanitize_persona_name

LOW_SIGNAL_MESSAGES = {
    "k",
    "kk",
    "ok",
    "okay",
    "lol",
    "lmao",
    "lmfao",
}

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL | re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


@dataclass(frozen=True)
class ImpersonationPayload:
    bio: str
    aliases: list[str]
    normal_prompt: str
    evil_prompt: Optional[str]
    sample_dialogues: list[str]


@dataclass(frozen=True)
class CollectedMemberMessages:
    raw_count: int
    usable_count: int
    raw_messages: list[str]
    usable_messages: list[str]


def _normalize_message(text: str) -> str:
    return WHITESPACE_RE.sub(" ", (text or "").strip())


def filter_impersonation_messages(raw_messages: list[str]) -> list[str]:
    filtered: list[str] = []
    seen_normalized: set[str] = set()

    for message in raw_messages:
        text = _normalize_message(message)
        if not text:
            continue
        if text.startswith("/") or text.startswith("!"):
            continue
        if len(text) < 3:
            continue

        normalized = text.casefold()
        if normalized in LOW_SIGNAL_MESSAGES:
            continue
        if re.fullmatch(r"[\W_]+", text):
            continue
        if normalized in seen_normalized:
            continue

        seen_normalized.add(normalized)
        filtered.append(text)

    return filtered


def choose_unique_persona_name(base_name: str, existing_names: set[str]) -> str:
    candidate = (base_name or "").strip()
    if not candidate:
        raise ValueError("Persona name is required.")
    if candidate not in existing_names:
        return candidate

    suffixed = f"{candidate} (impersonated)"
    if suffixed not in existing_names:
        return suffixed

    counter = 2
    while True:
        numbered = f"{candidate} (impersonated {counter})"
        if numbered not in existing_names:
            return numbered
        counter += 1


def _coerce_aliases(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    aliases: list[str] = []
    seen: set[str] = set()
    for item in value:
        alias = _normalize_message(str(item)).lower()
        if not alias or alias in seen:
            continue
        aliases.append(alias)
        seen.add(alias)
    return aliases


def _coerce_sample_dialogues(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("sample_dialogues must be a list.")

    sample_dialogues: list[str] = []
    for item in value:
        if isinstance(item, dict):
            speaker = _normalize_message(str(item.get("speaker") or ""))
            dialogue = _normalize_message(str(item.get("dialogue") or ""))
            if speaker and dialogue:
                sample_dialogues.append(f"{speaker}: {dialogue}")
                continue
            combined = _normalize_message(str(item.get("text") or ""))
            if combined:
                sample_dialogues.append(combined)
                continue
        else:
            text = _normalize_message(str(item))
            if text:
                sample_dialogues.append(text)

    if not sample_dialogues:
        raise ValueError("sample_dialogues must include at least one usable line.")
    return sample_dialogues


def parse_impersonation_payload(payload_text: str) -> ImpersonationPayload:
    if not payload_text or not payload_text.strip():
        raise ValueError("Gemini returned an empty impersonation payload.")

    match = JSON_BLOCK_RE.search(payload_text)
    raw_json = match.group(1) if match else payload_text.strip()

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned invalid impersonation JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("Impersonation payload must be a JSON object.")

    bio = _normalize_message(str(data.get("bio") or ""))
    normal_prompt = _normalize_message(str(data.get("normal_prompt") or ""))
    evil_prompt = _normalize_message(str(data.get("evil_prompt") or "")) or None
    sample_dialogues = _coerce_sample_dialogues(data.get("sample_dialogues"))

    if not normal_prompt:
        raise ValueError("Impersonation payload is missing normal_prompt.")

    return ImpersonationPayload(
        bio=bio,
        aliases=_coerce_aliases(data.get("aliases")),
        normal_prompt=normal_prompt,
        evil_prompt=evil_prompt,
        sample_dialogues=sample_dialogues,
    )


def _build_style_stats(messages: Sequence[str]) -> str:
    if not messages:
        return "- No usable messages collected."

    total_words = sum(len(message.split()) for message in messages)
    avg_words = total_words / len(messages)
    emoji_count = sum(len(EMOJI_RE.findall(message)) for message in messages)
    question_count = sum(message.count("?") for message in messages)
    exclamation_count = sum(message.count("!") for message in messages)

    return "\n".join(
        [
            f"- usable_messages: {len(messages)}",
            f"- average_words_per_message: {avg_words:.1f}",
            f"- emoji_count: {emoji_count}",
            f"- total_questions: {question_count}",
            f"- total_exclamations: {exclamation_count}",
        ]
    )


def build_impersonation_prompt(
    *,
    member_display_name: str,
    filtered_messages: Sequence[str],
    raw_count: int,
    usable_count: int,
) -> str:
    corpus = "\n".join(f"- {message}" for message in filtered_messages[:250])
    style_stats = _build_style_stats(filtered_messages)
    return (
        "You are generating a Discord bot persona that mirrors a member's public chat style.\n"
        "Capture tone and habits closely, but do not claim to literally be the real user.\n\n"
        f"Target display name: {member_display_name}\n"
        f"Raw messages scanned: {raw_count}\n"
        f"Usable filtered messages: {usable_count}\n\n"
        "Required output: compact JSON object with keys bio, aliases, normal_prompt, evil_prompt, sample_dialogues.\n"
        "Forbid identity claims, private-fact invention, hidden reasoning disclosure, moderation bypasses, or tool-rule violations.\n"
        "Capture sentence length, punctuation, emoji/slang habits, warmth/bluntness/teasing balance, and response patterns for casual chat, jokes, affection, disagreement, and acknowledgements.\n\n"
        "Style statistics:\n"
        f"{style_stats}\n\n"
        "Message corpus:\n"
        f"{corpus}"
    )


async def collect_member_messages(
    member: discord.Member,
    channels: Sequence[discord.abc.GuildChannel],
    *,
    viewer: Optional[discord.Member] = None,
    limit: int = 1000,
) -> CollectedMemberMessages:
    raw_messages: list[str] = []
    raw_count = 0

    for channel in channels:
        if raw_count >= limit:
            break

        permissions = channel.permissions_for(viewer) if viewer is not None else None
        if permissions is not None and (
            not getattr(permissions, "view_channel", False)
            or not getattr(permissions, "read_message_history", False)
        ):
            continue

        history_limit = min(limit - raw_count, 1000)
        try:
            async for message in channel.history(limit=history_limit):
                if raw_count >= limit:
                    break
                if getattr(message.author, "bot", False):
                    continue
                if message.author.id != member.id:
                    continue
                raw_count += 1
                raw_messages.append(message.content or "")
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            continue

    usable_messages = filter_impersonation_messages(raw_messages)
    return CollectedMemberMessages(
        raw_count=raw_count,
        usable_count=len(usable_messages),
        raw_messages=raw_messages,
        usable_messages=usable_messages,
    )


async def copy_member_avatar(
    member: discord.Member,
    *,
    guild_id: int,
    persona_name: str,
) -> tuple[Optional[str], Optional[str]]:
    slug = sanitize_persona_name(persona_name)
    if not slug:
        return None, "Persona name does not produce a valid avatar slug."

    save_path = DATA_DIR / "avatars" / "custom" / f"guild_{guild_id}_{slug}_avatar.webp"

    try:
        avatar_bytes = await member.display_avatar.read()
        image = Image.open(BytesIO(avatar_bytes))
        image.load()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        output = BytesIO()
        image.save(output, format="WEBP", quality=80, method=6)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(output.getvalue())
        return str(save_path), None
    except Exception as exc:
        return None, str(exc)


def build_generated_bio(base_bio: str, *, member_display_name: str, generated_at: Optional[datetime] = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    provenance = (
        f"Generated from @{member_display_name} message history on "
        f"{generated_at.astimezone(timezone.utc).date().isoformat()}."
    )
    clean_bio = (base_bio or "").strip()
    if clean_bio:
        return f"{clean_bio}\n\n{provenance}"
    return provenance
