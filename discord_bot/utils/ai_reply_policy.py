from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Iterable, Mapping, Optional

AMBIGUOUS_MIN_SCORE = 3
NO_MENTION_JUDGE_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class AutoChannelSignal:
    counter_hit: bool = False
    always_eligible: bool = False


@dataclass(frozen=True)
class ReplyTriggerSignals:
    mentioned: bool = False
    replied_to_bot: bool = False
    has_selected_trigger: bool = False
    auto_counter_hit: bool = False
    auto_always_eligible: bool = False
    is_foreign_webhook: bool = False

    @property
    def explicit_trigger(self) -> bool:
        return self.mentioned or self.replied_to_bot or self.has_selected_trigger

    @property
    def passive_candidate(self) -> bool:
        return self.auto_counter_hit or self.auto_always_eligible


@dataclass(frozen=True)
class SelfReplyChainState:
    depth: int = 0
    last_was_self: bool = False
    last_responded_persona_mode: Optional[str] = None


@dataclass(frozen=True)
class NoMentionScore:
    total: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    reject_immediately: bool = False
    needs_llm_tiebreak: bool = False


@dataclass(frozen=True)
class NoMentionJudgeVerdict:
    reply: bool = False
    confidence: float = 0.0
    reason: str = "parse_failure"


def evaluate_auto_channel_signal(
    *,
    channel_id: int,
    auto_channel_ids: Iterable[int],
    auto_threshold: int,
    counter_value: int,
    next_target: int,
) -> AutoChannelSignal:
    configured_channels = {int(item) for item in auto_channel_ids}
    if int(channel_id) not in configured_channels:
        return AutoChannelSignal()

    if int(auto_threshold) <= 0:
        return AutoChannelSignal(counter_hit=False, always_eligible=True)

    next_target_value = int(next_target)
    effective_target = next_target_value if next_target_value > 0 else int(auto_threshold)
    counter_hit = int(counter_value) >= effective_target
    return AutoChannelSignal(counter_hit=counter_hit, always_eligible=False)


def build_reply_trigger_signals(
    *,
    mentioned: bool,
    replied_to_bot: bool,
    has_selected_trigger: bool,
    auto_channel_signal: AutoChannelSignal,
    is_foreign_webhook: bool,
) -> ReplyTriggerSignals:
    return ReplyTriggerSignals(
        mentioned=bool(mentioned),
        replied_to_bot=bool(replied_to_bot),
        has_selected_trigger=bool(has_selected_trigger),
        auto_counter_hit=bool(auto_channel_signal.counter_hit),
        auto_always_eligible=bool(auto_channel_signal.always_eligible),
        is_foreign_webhook=bool(is_foreign_webhook),
    )


def is_bot_owned_webhook(
    *,
    message_id: int,
    passport_store: Mapping[int, Mapping[str, object]],
) -> bool:
    return int(message_id) in passport_store


def self_reply_limit_reached(state: SelfReplyChainState, limit: int) -> bool:
    normalized_limit = max(0, int(limit))
    return int(state.depth) >= normalized_limit


def score_no_mention_candidate(window: Iterable[Mapping[str, object]]) -> NoMentionScore:
    total = 0
    reasons: list[str] = []
    reject_immediately = False
    bot_owned_count = 0

    items = list(window)

    for item in items:
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        if bool(item.get("is_bot_owned")):
            bot_owned_count += 1

        if _looks_like_closed_acknowledgment(content):
            reject_immediately = True
            reasons.append("closed_acknowledgment")

        if _looks_like_open_question(content):
            total += 3
            reasons.append("open_question")
            continue

        if _looks_like_invitation(content):
            total += 2
            reasons.append("invitation")

    if bot_owned_count >= 2:
        total -= 3
        reasons.append("recent_bot_saturation")

    total = max(total, 0)
    needs_llm_tiebreak = total >= AMBIGUOUS_MIN_SCORE and not reject_immediately
    return NoMentionScore(
        total=total,
        reasons=tuple(reasons),
        reject_immediately=reject_immediately,
        needs_llm_tiebreak=needs_llm_tiebreak,
    )


def build_no_mention_judge_prompt(
    window: Iterable[Mapping[str, object]],
    *,
    channel_name: str,
) -> str:
    items = list(window)[-6:]
    transcript_lines: list[str] = []
    for item in items:
        speaker = str(item.get("username") or "Unknown")
        content = str(item.get("content") or "").strip() or "[no text]"
        ownership = "bot" if bool(item.get("is_bot_owned")) else "human"
        transcript_lines.append(f"- {speaker} ({ownership}): {content}")
    transcript = "\n".join(transcript_lines) if transcript_lines else "- [empty window]"
    return (
        "You are deciding whether a Discord bot should join a conversation without being directly mentioned.\n"
        "Be conservative and human-like. Prefer silence unless the recent context clearly invites the bot.\n"
        f"Channel: {channel_name}\n"
        "Recent conversation window:\n"
        f"{transcript}\n"
        "Return strict JSON only with this schema:\n"
        '{"reply": false, "confidence": 0.0, "reason": "short_snake_case_reason"}\n'
        "Rules:\n"
        "- reply=true only if the recent window clearly invites or benefits from the bot joining\n"
        "- confidence must be between 0 and 1\n"
        "- if the conversation looks resolved, closed, or bot-saturated, choose reply=false\n"
        "- no markdown, no prose, no code fences\n"
    )


def parse_no_mention_judge_response(raw_text: str) -> NoMentionJudgeVerdict:
    try:
        payload = json.loads((raw_text or "").strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return NoMentionJudgeVerdict(reply=False, confidence=0.0, reason="parse_failure")

    if not isinstance(payload, dict):
        return NoMentionJudgeVerdict(reply=False, confidence=0.0, reason="parse_failure")

    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        return NoMentionJudgeVerdict(reply=False, confidence=0.0, reason="parse_failure")

    reason = str(payload.get("reason") or "missing_reason").strip() or "missing_reason"
    wants_reply = bool(payload.get("reply"))
    if confidence < NO_MENTION_JUDGE_CONFIDENCE_THRESHOLD:
        return NoMentionJudgeVerdict(reply=False, confidence=confidence, reason="low_confidence")
    return NoMentionJudgeVerdict(reply=wants_reply, confidence=confidence, reason=reason)


def _looks_like_open_question(content: str) -> bool:
    lowered = content.lower()
    if "?" in lowered:
        return True
    question_starters = (
        "any idea",
        "what do you think",
        "can you",
        "could you",
        "should we",
        "why did",
        "how do we",
        "is it",
        "does anyone",
        "anyone know",
    )
    return any(lowered.startswith(prefix) or prefix in lowered for prefix in question_starters)


def _looks_like_invitation(content: str) -> bool:
    lowered = content.lower()
    invitation_markers = (
        "what do you think",
        "thoughts?",
        "any idea",
        "opinions?",
        "help?",
    )
    return any(marker in lowered for marker in invitation_markers)


def _looks_like_closed_acknowledgment(content: str) -> bool:
    lowered = content.lower().strip()
    closure_markers = {
        "ok",
        "okay",
        "thanks",
        "thank you",
        "ty",
        "np",
        "nvm",
        "never mind",
        "solved",
        "all good",
    }
    return lowered in closure_markers
