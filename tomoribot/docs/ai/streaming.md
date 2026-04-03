# 10. Streaming & Response System

This document explains the current streaming architecture for TomoriBot and how model output is transformed into Discord messages.

> This file is the high-level guide.  
> For low-level flush/chunk edge cases and exact boundary rules, see [`text-flushing-and-chunking.md`](./text-flushing-and-chunking.md).

## Overview

TomoriBot uses a modular streaming pipeline:

1. Provider stream adapters normalize raw provider chunks.
2. `StreamOrchestrator` manages buffering, boundaries, tool-call interruption, and Discord sending.
3. Text utilities clean, chunk, and optionally humanize content before sending.

Important: TomoriBot now sends **discrete messages**, not "edit the same message every 500ms".

## Main Components

| Component | File | Responsibility |
|---|---|---|
| Universal orchestrator | `src/utils/discord/streamOrchestrator.ts` | Buffering, flush decisions, send pipeline, timeout/stop handling |
| Stream interfaces | `src/types/stream/interfaces.ts` | Provider/orchestrator contracts and stream context |
| Stream constants/types | `src/types/stream/types.ts` | Message length, flush thresholds, typing settings |
| Provider stream adapters | `src/providers/*/*StreamAdapter.ts` | Convert provider-native events into normalized chunks |
| Text processing | `src/utils/text/stringHelper.ts` | `cleanLLMOutput`, `chunkMessage`, `humanizeString` |
| Emoji dedup controls | `src/utils/text/emojiPenalty.ts` | Duplicate custom-emoji filtering with safety guards |

## Runtime Flow

### 1) Provider entry

`tomoriChat` calls provider `streamToDiscord(...)`.  
Before heavy response work starts, `tomoriChat` also starts a lock-scoped Discord typing keepalive.  
Provider builds `StreamConfig` and delegates to `StreamOrchestrator.streamToDiscord(...)`.

### 2) Stream initialization

`tomoriChat`:
- refreshes Discord typing for the active channel lock until the lock is released

`StreamOrchestrator`:
- creates stream state/metrics
- builds `TextProcessingConfig`
- builds typing config from `humanizerDegree`
- prepares optional output prefill

### 3) Per-chunk loop

For each provider raw chunk:
- stop-request check
- inactivity timeout check
- reset inactivity timer
- provider `processChunk(...)` to normalized type
- handle normalized chunk (`text`, `function_call`, `error`, `done`)

### 4) Text chunk handling

For `text` chunks:
- append to buffer
- run boundary detection
- flush eligible segment(s)
- apply regular overflow fallback when needed

### 5) Segment pipeline before send

Each flushed segment goes through:
1. `filterDuplicateCustomEmojis(...)`
2. `cleanLLMOutput(...)`
3. mention resolution
4. prefix strip/prefill handling
5. registered-speaker guard truncation (`Name:` lines for known non-active speakers, plus reserved `Assistant:` lines)
6. `sendSegment(...)`

### 6) Message chunking and sending

`sendSegment(...)`:
- splits text with `chunkMessage(...)` (Discord-safe lengths)
- applies `humanizeString(...)` only for degree 3 (`HEAVY`)
- sends chunks with typing simulation (`>= MEDIUM`) or immediate mode

### 7) Completion

When stream ends:
- final buffer flush
- metrics finalization
- accumulated output returned for short-term memory storage

## Reasoning / Thought Logging

Providers may emit displayable reasoning separately from visible reply text.

- Stream adapters attach reasoning to normalized chunks via `ProcessedChunk.thoughts`
- reasoning is classified as either `summary` or `raw`
- `StreamOrchestrator` accumulates those thought segments separately from the visible reply buffer
- thought text is not appended to `currentTurnModelParts`
- thought text is not flushed to Discord as part of the normal reply
- thought text is not stored in short-term memory

On successful streamed turns, `StreamOrchestrator` returns the merged reasoning payload in `StreamResult.thoughtLog`, along with the first visible reply URL when one exists.

`tomoriChat` merges thought logs across successful tool-call iterations and posts one final embed to the configured `tomori_configs.thought_log_channel_disc_id` channel after the full turn completes. If the configured channel is missing, inaccessible, or deleted, the main reply still succeeds and the thought-log post is skipped with a warning.

Normal message triggers are disabled inside the configured thought-log channel so provider reasoning echoes cannot recursively trigger new chats there. Slash commands still work because they do not use `messageCreate`.

Thought-log sender identity is explicit:
- main persona turns post as the normal bot sender
- alter persona turns post through the shared webhook using the alter nickname/avatar
- user-impersonation turns post through the shared webhook using the impersonated user's display name/avatar

The merged thought log is still one logical turn. In normal multi-persona auto-trigger flows, only one persona owns a given invocation because additional personas are re-queued into separate follow-up jobs.

## Buffering and Flush Boundaries

Primary flush triggers:
- code block open/close boundaries
- newline boundaries
- period-based sentence boundaries when humanizer degree is `HEAVY` (3)

Safety guards:
- newline/period flush blocked when semantic markers are incomplete
- newline at end-of-buffer waits for more input
- punctuation carry after newline keeps sentence punctuation attached
- colon (`:`) is intentionally excluded from newline punctuation carry to avoid splitting `:emoji:` tokens

Overflow fallback:
- if regular buffer becomes too large, orchestrator flushes at a **safe breakpoint**
- prefers nearby sentence/newline boundaries, then whitespace, then hard fallback
- loops until oversized buffer is drained

## Message Sending Behavior

### Main persona
- first send may reply to the source message
- subsequent sends use `channel.send(...)`

### Alter persona
- sends via webhook with persona username/avatar
- attempts webhook recovery on invalid webhook errors
- in non-production, avatar identity comes from either a public URL built from local storage or a webhook-avatar mutation fallback guarded by a per-target-channel lock
- falls back to regular bot message if webhook path fails

### User impersonation
- sends through a temporary webhook created with the impersonated user's display name/avatar
- if the impersonated user has set `/personal impersonate prompt`, that prompt is injected as a user-owned persona prompt before the final imitation directive
- if webhook creation, webhook sending, or stream completion fails, the impersonation attempt fails closed
- TomoriBot does not fall back to a normal bot-authored channel message for user impersonation replies or timeout/error notices

### Flood protection
- `STREAMING_LIMITS.MAX_FLUSH_COUNT` caps messages per stream session in production
- if limit is reached, stream requests a graceful stop and warns user

## Humanizer Behavior

Humanizer degree controls both pacing and text treatment:

| Degree | Behavior |
|---|---|
| `0` (`NONE`) | No humanization |
| `1` (`LIGHT`) | Light processing |
| `2` (`MEDIUM`) | Typing simulation enabled |
| `3` (`HEAVY`) | Period flush boundary + post-chunk humanization |

Key order for degree 3:
1. Flush boundary decision
2. Segment cleanup
3. `chunkMessage(...)`
4. `humanizeString(...)` on each chunk

## Tool Call Integration

When model emits `function_call`:
- orchestrator flushes pending buffer first
- returns status `function_call`
- caller executes tool and continues next stream iteration with updated context

Provider adapter safeguards:
- Google/OpenRouter/Custom adapters split mixed chunks (`text` + tool-call signal) into two raw chunks so text is processed first, then `function_call`.
- Speaker-boundary holdback tails are force-flushed before non-text chunks (tool call/error/finish) to prevent truncated text when a stream exits early on tool execution.
- Adapter-level speaker fallback only stops on registered speaker labels already present in context, plus reserved `Assistant:` labels. It intentionally ignores arbitrary capitalized headings such as `Budget Breakdown:`.

Stream-level safeguard:
- Right before Discord send, `StreamOrchestrator` truncates any flushed segment at the first line that starts with a registered non-active speaker label (`Name:`) or reserved `Assistant:` label, then stops the stream. This applies to every provider, including providers that already have adapter-level speaker guards.

Loop control and max iterations are managed by `tomoriChat` (function-call safety loop).

## Error, Timeout, and Stop Handling

### Provider errors
- pending text is flushed first (when available)
- provider-specific error messaging is used when possible
- fallback embed path handles generic errors

### Inactivity timeout
- inactivity timer resets on each chunk
- timeout threshold defaults from stream constants
- timeout state is tracked explicitly, so cleanup at normal stream end no longer looks like a timeout

### Stop requests
- stop requests are tracked by channel
- checked before processing/sending to avoid duplicate or late sends
- special handling avoids duplicate flush-limit embeds
- internal speaker-boundary stops that send no visible text are promoted into the empty-response retry path instead of silently ending as a normal user stop

### Final flush auto-close
- if final buffer still has incomplete semantic markers, orchestrator auto-closes markers before sending to avoid text loss

## Key Tuning Knobs

| Setting | Location | Current Role |
|---|---|---|
| `MAX_SINGLE_MESSAGE_LENGTH` | `src/types/stream/types.ts` | Per-message chunk cap (below Discord hard limit) |
| `FLUSH_BUFFER_SIZE_REGULAR` | `src/types/stream/types.ts` | Regular overflow threshold |
| `FLUSH_BUFFER_SIZE_CODE_BLOCK` | `src/types/stream/types.ts` | Code-block overflow threshold |
| `INACTIVITY_TIMEOUT_MS` | `src/types/stream/types.ts` | Stream inactivity timeout |
| `MAX_FLUSH_COUNT` | `src/utils/security/rateLimiter.ts` | Max messages sent per stream session |
| `DISCORD_TYPING_KEEPALIVE_INTERVAL_MS` | `.env` | Channel-lock typing refresh cadence while work is still active |
| `humanizer_degree` | `tomori_configs` | Controls pacing and degree-dependent flush/humanization |

## Debugging Checklist

Useful logs when diagnosing output shape:
- `Stream API: Raw chunk received: ...`
- `Stream Seg: Flushing oversized regular buffer at safe breakpoint ...`
- `Stream Send: Humanized (D3) from ... to ...`
- `Stream Send: Sent message (N): ...`
- `[Unique Emoji] ...` lines from emoji dedup

If output looks wrong:
1. Confirm where the split happened (buffer flush vs `chunkMessage`).
2. Check emoji dedup logs for removals.
3. Verify active humanizer degree.
4. Check for incomplete semantic markers delaying flush.

## Related Docs

- `docs/ai/text-flushing-and-chunking.md` (low-level flush/chunk internals)
- `docs/ai/expression-handling.md` (emoji/sticker conversion and metadata)
- `docs/ai/providers.md` (provider architecture)
