# Contextual Emoji Selection Design

## Goal

Replace the current emoji rule engine with a single bot-controlled selection stage that appends a validated Discord emoji only when the reply context strongly supports it.

## Problem

The current pipeline mixes four different responsibilities:

1. Prompting the model with custom emoji knowledge and output rules
2. Rule-based trigger insertion after generation
3. Custom emoji shortcode replacement
4. Malformed custom-tag repair

That layering makes the bot brittle. The model can still emit malformed fragments, the trigger engine can append mismatched emojis, and downstream repair code tries to rescue bad output instead of preventing it.

## Approved Direction

Use a bot-side contextual scorer. The model should generate plain text. The bot should be the only component that decides whether a Discord custom emoji is appropriate and which validated emoji token to append.

## Architecture

### 1. One emoji decision point

Emoji selection happens once, after the reply text has been cleaned and before the message is sent.

### 2. Candidate pool

The bot uses only validated guild/application emojis already available in runtime caches. Candidates come from:

- configured custom emojis with usage descriptions
- validated general emojis

Each candidate is represented as:

- token
- normalized name
- source usage text
- inferred semantic signals

### 3. Conversation signals

The bot converts the user message and final bot reply into a small signal vector:

- `celebratory`
- `positive`
- `affectionate`
- `playful`
- `teasing`
- `annoyed`
- `confused`
- `shocked`
- `flirty`
- `sad`
- `supportive`
- `serious`

Signals come from lightweight text heuristics, punctuation, emphasis, and sentiment cues across both the incoming user message and outgoing reply. Reply cues are weighted more heavily than user cues because the emoji should match the bot’s final tone.

### 4. Emoji semantics

Each emoji gets signal weights inferred from:

- config `usage` text for configured emojis
- normalized emoji name for configured and general emojis

This keeps emoji meaning data-driven without relying on a hardcoded “if keyword X then emoji Y” trigger map.

### 5. Selection policy

- default to no emoji
- append at most one emoji
- require a minimum confidence threshold
- require a margin over the next-best candidate
- suppress emojis for serious, administrative, or neutral replies

### 6. Output ownership

The outgoing pipeline should not convert model-produced shortcodes into real Discord custom emoji tags. If the model emits known custom emoji shortcodes, the bot strips them before selection so custom emoji ownership stays with the bot.

## Code Changes

- `discord_bot/utils/emoji_manager.py`
  - replace trigger-based selection with contextual scoring
  - add known-shortcode stripping for model output
  - keep validation/cache responsibilities

- `discord_bot/cogs/ai_brain.py`
  - remove prompt-time custom emoji guidance
  - remove trigger-based append step
  - remove custom shortcode replacement from the response path
  - call the new contextual selection step once before send

- `discord_bot/main.py`
  - update startup logging to reflect validated contextual emoji inventory rather than “rules”

- `tests/test_emoji_manager.py`
  - replace trigger-rule tests with contextual scoring tests

## Non-Goals

- no second LLM pass for emoji selection
- no expansion into sticker or GIF selection in this change
- no attempt to infer emoji meaning from image assets

## Verification

- targeted unit tests for contextual selection and shortcode stripping
- targeted unit tests for the updated response pipeline behavior
- focused regression check that malformed model fragments are no longer required for emoji output
