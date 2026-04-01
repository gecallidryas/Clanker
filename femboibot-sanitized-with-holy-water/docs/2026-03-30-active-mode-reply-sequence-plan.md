# Active-Mode Reply Sequence Plan

## Executive Summary

This design replaces the earlier multi-persona idea with a much smaller and cleaner feature:

- one active persona only
- one bot identity only
- controlled continuation across a reply thread
- the active AI model decides whether the conversation should continue and what the next payload type should be

The important correction is that the reply sequence is **not** a fixed ladder such as `text -> emoji -> text -> sticker/gif`. That order is only an example of the kinds of outputs the system should support. The configured model should decide the sequence length and progression, while the bot enforces hard caps so the model cannot create spam loops.

## Scope

### In scope

- Continue a conversation as the currently set mode only
- Allow the model to choose whether to stop or continue
- Allow the model to choose among:
  - text
  - emoji-only text reply
  - sticker
  - GIF
- Keep the sequence tied to a single user replying in the same channel/thread
- Reuse current emoji, sticker, and GIF plumbing

### Out of scope

- Multiple personas talking at once
- Persona switching inside a reply sequence
- Webhooks
- Alter-account illusion
- Automatic continuation triggered by the bot's own messages

## Current-State Audit

### Relevant code already present

- Active guild mode is single-value state in `server_config.persona_mode`.
- Custom personas are still compatible because they already resolve to a single `mode_key`.
- The AI layer already tracks active conversations by `(channel_id, user_id)`.
- The AI layer already supports:
  - normal text replies
  - emoji normalization and emoji injection
  - sticker selection and sending
  - GIF lookup/sending through Tenor

Primary files inspected:

- `discord_bot/cogs/ai_brain.py`
- `discord_bot/cogs/persona.py`
- `discord_bot/cogs/social.py`
- `discord_bot/utils/db_handler.py`
- `discord_bot/utils/emoji_manager.py`
- `discord_bot/utils/expression_tools.py`
- `discord_bot/utils/expression_picker.py`
- `discord_bot/utils/gif_reply.py`

### Architectural fit

The current architecture is already centered on a single active speaker. That means the cleanest solution is to extend the existing active-conversation flow, not to add a new persona orchestration layer.

The existing `ai_self_reply_limit` is not a true persona-chain feature. It is only a reply-depth guard around user-to-bot reply chains. That should remain a safety guard, not become the primary continuation design.

## Product Behavior

### Core rule

When a user triggers the bot and the active mode replies, the model may optionally declare that this conversation should remain "open" for a few more direct replies from that same user.

Each next user reply in that thread gives the same active mode another chance to respond. On each turn, the model may choose:

- stop
- send text
- send emoji-only text
- send a sticker
- send a GIF

The number of follow-up replies is model-directed but system-bounded.

### User-facing behavior

Example progression:

1. User mentions or replies to the bot
2. Active mode sends a normal text response
3. User replies again
4. Active mode sends only an emoji
5. User replies again
6. Active mode sends a short text follow-up
7. User replies again
8. Active mode sends a sticker or GIF
9. Sequence ends

The bot may also choose to stop after step 2, or after any later turn, if the model judges that the exchange should not continue.

## Recommended Runtime Model

Keep an in-memory reply-sequence session keyed by `(channel_id, user_id)`.

Suggested session shape:

```python
{
    "mode_key": "mode_femboy",
    "guild_id": 123,
    "channel_id": 456,
    "user_id": 789,
    "root_user_message_id": 111,
    "last_bot_message_id": 222,
    "stage_index": 1,
    "model_requested_max_stages": 3,
    "hard_max_stages": 5,
    "allowed_payloads": ["text", "emoji_only", "sticker", "gif"],
    "expires_at": "...",
    "ended": False,
}
```

### Advancement rules

- Advance only when the same user replies to the latest bot message in the active sequence.
- Ignore bot-authored messages as triggers.
- Cancel the sequence on timeout.
- Cancel the sequence when the guild mode changes.
- Cancel the sequence when a different user meaningfully interrupts the thread, unless a future policy explicitly allows group continuation.

### Hard limits

- Short timeout, recommended `300-600` seconds
- Hard stage cap, recommended `4-6`
- Same channel/thread only
- Same user only
- One active sequence per `(channel_id, user_id)`

## Recommended Prompt Contract

The current prompt flow should be extended with a reply-sequence control contract. The model should continue to produce in-character content, but also emit a small machine-readable control block that tells the bot whether the conversation should remain open.

The key design choice is:

- the model decides pacing and expression style
- the system enforces safety, stage caps, and valid payload types

### System prompt addition

Add a dedicated section to the active-mode prompt:

```text
=== REPLY SEQUENCE RULES ===
- You are only the currently active mode/persona.
- Never switch personas.
- You may decide whether this conversation should continue across future direct user replies.
- Allowed next payload types are:
  - text
  - emoji_only
  - sticker
  - gif
  - stop
- Use continuation only when it improves the interaction.
- Keep continuation short and intentional.
- Do not create long loops.
- Do not assume you will get another turn.
- If the conversation should end, choose `stop`.
- If you choose `emoji_only`, the visible reply should be only emoji or a very short expressive token.
- If you choose `sticker` or `gif`, prefer them only when they fit the tone naturally.
- The system may override your continuation request if limits are reached.
```

### Control block contract

Use a small fenced block similar to the repo's existing prompt-emulated control patterns:

````text
```reply_sequence
{
  "continue": true,
  "next_payload": "emoji_only",
  "remaining_desired_turns": 2,
  "tone_shift": "lighter",
  "caption": ""
}
```
````

Suggested semantics:

- `continue`: whether the thread should remain open after this turn
- `next_payload`: preferred payload kind for the next bot turn
- `remaining_desired_turns`: how many more future user replies the model wants to support
- `tone_shift`: optional hint such as `lighter`, `warmer`, `playful`, `cooldown`
- `caption`: optional caption to pair with `gif` or `sticker`

### Valid payload kinds

- `text`
- `emoji_only`
- `sticker`
- `gif`
- `stop`

### First-turn model behavior

On the first reply, the model should:

- send the first visible reply normally
- decide whether the thread should remain open
- choose the preferred payload type for the next turn
- choose a desired remaining budget

The desired remaining budget is advisory, not authoritative. The runtime should clamp it to the configured hard maximum.

### Follow-up-turn model behavior

On each later user reply, the prompt should include:

- current active mode
- current stage index
- remaining hard budget
- last payload type used
- conversation text so far
- the last `reply_sequence` control state

The model should then decide again:

- send the next payload
- continue or stop
- optionally change the preferred next payload

This lets the model adapt mid-conversation instead of rigidly following a predetermined ladder.

## Prompt Input Additions

Add a compact context section before the current message:

```text
=== REPLY SEQUENCE STATE ===
- Active sequence: yes
- Stage index: 2
- Remaining hard budget: 2
- Last payload type: emoji_only
- Model requested continuation: yes
- Allowed payloads: text, emoji_only, sticker, gif, stop
- Timeout behavior: this is the same user replying in the active thread
```

If there is no active sequence:

```text
=== REPLY SEQUENCE STATE ===
- Active sequence: no
- You may either stop after this turn or open a short continuation
```

## Output Execution Rules

### `text`

- Send normal text reply

### `emoji_only`

- Send a reply containing only emoji or a minimal expressive fragment
- Do not add a full sentence unless forced by fallback

### `sticker`

- Use existing sticker-selection path
- If no suitable sticker exists, downgrade to `gif`, then `text`

### `gif`

- Use existing Tenor-backed GIF path
- If Tenor is unavailable or no relevant GIF exists, downgrade to `sticker`, then `text`

### `stop`

- Do not create or refresh sequence state after this turn

## Recommended Config Surface

Add a dedicated reply-sequence config group instead of overloading unrelated AI settings.

Suggested guild config fields:

- `reply_sequence_enabled INTEGER DEFAULT 0`
- `reply_sequence_timeout_seconds INTEGER DEFAULT 300`
- `reply_sequence_hard_max_stages INTEGER DEFAULT 4`
- `reply_sequence_allow_gif INTEGER DEFAULT 1`
- `reply_sequence_allow_sticker INTEGER DEFAULT 1`
- `reply_sequence_allow_emoji_only INTEGER DEFAULT 1`

Optional later fields:

- `reply_sequence_interrupt_on_other_user INTEGER DEFAULT 1`
- `reply_sequence_require_direct_reply INTEGER DEFAULT 1`

## Why This Is Better Than A Fixed Ladder

A fixed ladder is too rigid:

- some conversations should end after one reply
- some should stay text-only
- some should escalate into a sticker or GIF naturally
- some modes may prefer different pacing

Letting the model choose the sequence makes the interaction feel more alive, while hard caps preserve safety and readability.

## Failure Handling

- If the control block is missing, default to `stop`.
- If the control block is malformed, default to `stop`.
- If a requested payload type is unavailable, downgrade in a fixed order.
- If the user replies after expiry, start a new normal interaction instead of reviving the old sequence.
- If the mode changed since the sequence started, discard the old sequence and use the new mode normally.

## Testing Scenarios

### Core flow

- First reply opens no sequence and ends immediately
- First reply opens a sequence with one extra turn
- First reply opens a sequence with multiple extra turns
- Follow-up turns switch payload kinds dynamically

### Payload execution

- Emoji-only output stays minimal
- Sticker turn works when stickers exist
- Sticker turn downgrades correctly when stickers do not exist
- GIF turn works when Tenor is configured
- GIF turn downgrades correctly when Tenor is unavailable

### State safety

- Same user replying to the latest bot message advances the sequence
- Reply to an older bot message does not advance the sequence
- Different user interrupt cancels or blocks continuation
- Timeout resets the sequence
- Mode switch resets the sequence

## Final Recommendation

Implement this as a **single-persona, model-directed reply sequence** feature.

Do not hardcode a fixed four-step pattern.
Do not add multiple personas.
Do not let bot messages self-trigger.

The model should decide whether the active mode wants to keep the interaction alive, but the bot should remain firmly in control of:

- who can continue it
- how long it can last
- which payload types are allowed
- how failures downgrade
