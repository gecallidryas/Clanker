# Conservative Auto-Reply Trigger Policy

## What Changed

- Added a dedicated reply-policy helper module for deterministic trigger signals, passive no-mention scoring, and ambiguous-case LLM judging.
- Extended `AIBrain` conversation context so recent-window judging can see structured recent messages instead of only the latest turn.
- Tracked bot-owned outbound messages, including persona webhook sends, so replies to persona webhooks count as direct replies to the bot.
- Wired `on_message()` so direct triggers remain deterministic while auto-channel messages only become passive candidates.
- Added a separate per-user privacy flag for passive no-mention auto-replies.
- Updated AI settings summaries and docs to explain the new conservative auto-channel semantics.

## Intentionally Conservative Behavior

- Direct mentions, direct replies to bot-owned messages, and persona trigger words still reply deterministically.
- Auto channels are candidate zones, not guaranteed response zones.
- `ai_auto_threshold = 0` means "always eligible for evaluation," not "reply to every message."
- Passive no-mention replies require positive recent-context scoring and, for ambiguous cases, a high-confidence LLM verdict.
- Parse failures, malformed judge responses, and low-confidence judge outputs all fail closed to silence.
- Foreign webhooks, whitelist mismatches, cooldown hits, privacy opt-outs, and self-reply limits still block passive replies.

## Residual Risks

- Heuristic weights may still need tuning after observing real channel behavior.
- The LLM tiebreaker adds latency to ambiguous passive candidates.
- Bot-owned webhook identity can still have edge cases across restarts or unusual webhook lifecycle changes.
