# Conservative Auto-Reply Trigger Policy Design

**Problem:** `discord_bot` already has the config knobs for whitelist channels, auto channels, cooldowns, and self-reply limits, but the runtime still behaves mostly like a mention/reply bot. The current no-mention path is shallow and a single-message LLM judge would still be brittle because "should I speak now?" depends on recent conversational context, not just the newest line.

**Decision:** Port Tomori's explicit trigger policy into `discord_bot` for direct replies, persona triggers, webhook-owned reply detection, cooldowns, whitelist enforcement, and self-reply chain guards. For no-mention auto-replies, do not use a raw "always reply" policy. Instead, use a conservative hybrid gate: deterministic blockers first, a recent-window heuristic score second, and a strict JSON LLM classifier only for ambiguous candidate messages.

## Approaches Considered

### 1. Exact Tomori Clone

Copy Tomori's trigger policy and auto-chat semantics literally:
- reply to bot/persona
- persona trigger words
- auto-chat counter hit
- threshold `0` means always reply in configured auto channels

**Pros:** highest parity, simplest mental model, easiest to verify against Tomori.

**Cons:** too chatty for the stated goal. It solves "reply without mention" but not "reply like a human." In an active channel it will still interject at moments that feel robotic or socially off.

### 2. Pure LLM Judge

Let an LLM decide every no-mention candidate from the last 5-6 messages.

**Pros:** flexible and potentially nuanced.

**Cons:** expensive, harder to debug, easy to overfit prompt wording, and unreliable when the model is forced to act as both policy engine and conversational model. It also makes safety and cooldown enforcement harder to reason about.

### 3. Hybrid Conservative Gate

Use deterministic policy for hard rules and guaranteed triggers, then add a conservative candidate gate for unsolicited replies:
- hard blockers
- candidate generation from Tomori-style auto-chat signals
- heuristic scoring over the last 5-6 messages
- LLM judge only for borderline cases

**Pros:** best balance of parity, debuggability, and human-like restraint.

**Cons:** more implementation work and more moving parts than a literal clone.

**Recommendation:** Approach 3.

## Scope

- Port Tomori-style guaranteed triggers into `discord_bot`:
  - direct reply-to-bot
  - reply-to-bot-owned persona webhook messages
  - persona trigger-word routing
  - shared auto-channel counter semantics
  - channel whitelist and cooldown enforcement
  - self-reply chain guards
- Add a conservative no-mention decision pipeline using the recent conversation window instead of a single message.
- Keep the existing `discord_bot` guild config surface as the primary admin UX.
- Add focused tests around decision logic and regression-prone edges.

## Out Of Scope

- Reproducing Tomori's full Matrix bridge behavior.
- Replacing the existing response-generation stack.
- Exposing every internal heuristic threshold as an admin-facing setting in v1.
- Reworking unrelated persona, memory, or provider systems.

## Target Behavior

### Guaranteed Reply Paths

The bot should always reply when policy allows and one of these is true:
- the user directly replies to the main bot message
- the user directly replies to a bot-owned persona webhook message
- the message contains a selected persona trigger
- a pending admin/agentic confirmation flow is active

These paths stay deterministic and do not require the auto-reply judge.

### Conservative No-Mention Auto-Reply

Configured auto channels become "candidate zones," not unconditional speaking zones.

- If `ai_auto_threshold > 0`, the shared auto-channel counter creates a no-mention candidate only when the shared target is hit.
- If `ai_auto_threshold == 0`, configured auto channels become always-eligible channels, but each message still goes through the conservative gate before the bot speaks.
- The bot should stay quiet when the conversation looks closed, bot-saturated, hostile, or already well served by humans.
- The bot should prefer replying when the recent window contains invitation cues, unresolved questions, lightweight pauses, or explicit persona references.

## Architecture

### 1. New Policy Module

Create a dedicated policy module, for example `discord_bot/utils/ai_reply_policy.py`, that owns:
- decision dataclasses such as `ReplyTriggerSignals`, `AutoReplyContextWindow`, and `AutoReplyDecision`
- hard-blocker evaluation
- trigger-signal extraction
- auto-channel shared counter logic
- self-reply chain state helpers
- heuristic scoring for no-mention replies
- prompt building and response parsing for the conservative LLM tiebreaker

This keeps `AIBrain.on_message()` from turning into a monolith.

### 2. Structured Recent-Message Window

Extend `ConversationContext` so it can return the last `N` structured messages, not only a flattened prompt string. The judge needs:
- username
- user id
- content
- reply target
- timestamp recency
- whether the author is bot-owned

The conservative gate should use a 5-6 message window by default.

### 3. Bot-Owned Outbound Passport Tracking

`discord_bot` currently tracks outbound messages by `sent.author.id`. That is not enough for persona webhooks because a reply to a webhook-authored message is not reliably treated as a reply to the bot.

Add a bot-owned outbound passport map, for example:
- `message_id -> owner_kind`
- `message_id -> persona mode`
- `message_id -> is_bot_owned_webhook`

Any message sent by the bot directly or by a bot-owned persona webhook should be recognized as a bot reply target.

### 4. Self-Reply Chain State

Add Tomori-style self-reply chain state per channel:
- current depth
- whether the last authored visible message was bot-owned
- last bot-owned persona mode that replied
- expiration timeout

This protects against ping-pong loops, especially in multi-persona and webhook identity mode.

### 5. Config Compatibility

Keep the current guild config surface and reinterpret it conservatively:
- `ai_channel_whitelist`: hard channel allowlist for non-manual AI replies
- `ai_reply_cooldown_seconds` and `ai_reply_cooldown_type`: hard cooldown policy
- `ai_self_reply_limit`: max self-reply chain depth
- `ai_auto_channels`: channels eligible for passive no-mention candidacy
- `ai_auto_threshold`:
  - `> 0`: shared counter target
  - `0`: always-eligible auto-reply channel, still gated by conservative decision logic

If user-trigger privacy parity is required, add a separate per-user reply-visibility flag rather than overloading personal-memory opt-out.

## Decision Pipeline

1. Collect explicit trigger signals:
- bot mention
- reply to main bot
- reply to bot-owned persona webhook
- selected persona trigger words
- auto-channel candidate hit
- pending confirmation state

2. Apply hard blockers:
- author is a non-exempt bot/webhook
- user-level reply visibility opt-out
- whitelist rejects this channel
- cooldown active
- self-reply chain limit reached

3. Decide reply class:
- explicit trigger: guaranteed reply
- no explicit trigger but auto-channel candidate: evaluate conservative no-mention gate
- none: no reply

4. Conservative no-mention gate:
- heuristic score from recent 5-6 messages
- immediate reject signals:
  - bot spoke very recently
  - two consecutive bot-owned messages already happened
  - recent message looks like a closed acknowledgment
  - channel is fast-moving and humans are already answering
- strong positive signals:
  - open question remains unanswered
  - users explicitly invite opinion
  - persona name is referenced informally
  - brief lull after several human messages
  - channel topic historically expects bot banter
- ambiguous scores only: call a strict JSON mini-judge over the recent window
- parse failure or low confidence: do not reply

## LLM Judge Design

The LLM should not decide from a single message. It should receive:
- the last 5-6 structured messages
- channel metadata such as `is_auto_channel`, `counter_hit`, `always_eligible`
- whether the bot has spoken recently
- whether any explicit trigger already exists

Required output:

```json
{"reply": false, "confidence": 0.31, "reason": "conversation already resolved by humans"}
```

Policy:
- temperature near zero
- strict parser
- conservative default on parse failure
- only run when heuristics classify the turn as borderline

## Testing Strategy

- Pure helper tests for trigger extraction, outbound-passport detection, self-reply depth, auto-channel counter evaluation, and heuristic scoring.
- Focused async tests around `AIBrain.on_message()` using fake messages and mocked dependencies.
- Regression tests for:
  - replying to persona webhook messages
  - ignoring foreign webhooks/bots
  - whitelist blocking even when a trigger exists
  - cooldown blocking for passive triggers
  - auto-channel threshold `0` producing eligibility but not mandatory replies
  - LLM judge using the recent structured window, not only the newest message

## Success Criteria

- Directly addressed messages behave like Tomori.
- No-mention auto-replies feel rarer, cleaner, and more human than Tomori's literal always-reply behavior.
- Persona webhooks are treated as bot-owned for reply detection and loop prevention.
- Auto channels and thresholds finally affect runtime behavior in `discord_bot`.
- The policy is explainable from tests and logs instead of hidden inside one giant prompt.
