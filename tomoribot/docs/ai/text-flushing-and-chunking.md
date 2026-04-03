# 20. Text Flushing and Chunking (Current Behavior)

This document explains the *current* message flushing/chunking pipeline used by TomoriBot when streaming model output to Discord.

It focuses on:
- Buffer flush timing and boundaries
- Chunk splitting before Discord sends
- Humanizer Degree 3 behavior and execution order
- Emoji conversion/dedup interactions
- New overflow-safe flushing behavior

Primary implementation files:
- `src/utils/discord/streamOrchestrator.ts`
- `src/utils/text/stringHelper.ts`
- `src/utils/text/emojiPenalty.ts`
- `src/types/stream/types.ts`

## Why This Exists

`docs/ai/streaming.md` explains streaming at a high level. This doc covers the low-level implementation details and edge-case handling that affect real Discord output shape.

## End-to-End Pipeline

For each incoming provider text chunk:

1. Raw text is appended to stream buffer.
2. `processBufferContent(...)` decides whether to flush part of buffer now.
3. If a segment is flushed, `sendBufferSegment(...)` runs text preprocessing.
4. Registered-speaker guard truncates any known non-active `Name:` line before send, and also blocks reserved `Assistant:` lines.
5. `sendSegment(...)` chunks the segment into Discord-sized messages.
6. Chunks are optionally humanized (D3) and sent.

Execution order for a flushed segment:

1. `filterDuplicateCustomEmojis(...)` (pre-conversion, `:name:` form)
2. `cleanLLMOutput(...)` (emoji normalization/conversion + text cleanup)
3. `resolveGuildMentions(...)`
4. Prefix stripping / output prefill handling
5. Registered-speaker guard truncation for known non-active `Name:` lines plus reserved `Assistant:` lines
6. `chunkMessage(...)`
7. `humanizeString(...)` only when degree is `HEAVY` (3)
8. Send each final chunk to Discord

## Buffer Flush Triggers

Core logic: `processBufferContent(...)` in `streamOrchestrator.ts`.

Flush candidates (priority by earliest index in buffer):

1. Code block boundaries (` ``` ` open/close)
2. Newline boundaries (`\n`)
3. Sentence period boundaries (`.` / `。`) when Humanizer Degree = 3

Additional guards:
- No newline/period flush when semantic markers are incomplete.
- No flush on newline if newline is the current last buffered char (wait for more text).
- If sentence punctuation immediately follows newline, punctuation is carried into same flush.
  - Carried punctuation excludes `:` intentionally to avoid splitting `:emoji:` tokens.
- Immediately before send, the orchestrator truncates at any registered non-active speaker line (`Name:`) or reserved `Assistant:` line and requests a graceful stop so later flushes cannot leak that turn.

## Semantic Marker Protection

Before newline/period flush, buffer is checked for incomplete structures:
- Unbalanced parentheses
- Unbalanced quotes (`"` and Japanese `「」`)
- Incomplete markdown link forms
- Incomplete URL protocol endings (`http:`, `https:/`, `https://`)

If incomplete markers are detected, flush is deferred to avoid broken output.

At final flush/function-call flush, incomplete markers can be auto-closed to avoid text loss.

## Oversized Regular Buffer Flush (Fallback)

When no normal breakpoint is reached and buffer grows too large:

- Threshold: `DISCORD_STREAMING_CONSTANTS.FLUSH_BUFFER_SIZE_REGULAR`
- Current value: `1000` in `src/types/stream/types.ts`

Condition:
- Not inside a code block
- No incomplete semantic markers
- Buffer length >= threshold

Behavior:
- Uses `findRegularOverflowFlushIndex(...)` to flush at a natural boundary.
- Not a hard cut at exact 1000 unless no better boundary exists.

Boundary selection strategy:
1. Prefer nearby **forward** sentence/newline boundary
2. Else nearby **backward** sentence/newline boundary
3. Else whitespace boundary (backward, then forward)
4. Else hard fallback at target length

This is looped (`while`) so a very large buffer chunk can be drained in multiple safe slices.

## Chunking After Flush

Core logic: `chunkMessage(...)` in `stringHelper.ts`.

Key behavior:
- Treats code blocks, URLs, and custom Discord emoji tags as atomic blocks.
- Attempts semantic-aware splitting for quoted/parenthesized/markdown segments.
- For text blocks:
  - Degree `< HEAVY` (0/1/2): split by newlines (`\n+`)
  - Degree `HEAVY` (3): split by newlines + sentence boundaries
- Consecutive emoji blocks are grouped into one emoji run.
- Final normalization merges punctuation-only chunks into adjacent chunks when possible.
  - Prevents standalone sends like `"."` or `","`.

Chunk length:
- `maxMessageLength` is provider-configured using `MAX_SINGLE_MESSAGE_LENGTH` (`1950`).
- This stays below Discord’s 2000-char hard limit.

## Humanizer Degree 3 Ordering

Important sequencing:

1. Buffer flush boundary is decided first.
2. Segment cleanup/conversion runs.
3. Segment is split by `chunkMessage(...)`.
4. Then each chunk is passed through `humanizeString(...)`.

So for Degree 3:
- Period-based flush in the buffer stage is active.
- `humanizeString(...)` is still *post-chunking*, not pre-flush.

## Emoji Dedup Interaction

Duplicate custom emoji filtering runs before `cleanLLMOutput(...)`.

Safety guard in `filterDuplicateCustomEmojis(...)`:
- If removing duplicate emojis would collapse output to punctuation-only/whitespace-only (or empty), filtering is skipped and original segment is kept.
- This prevents weird outputs like lone `","` and avoids dropping emoji-only lines entirely.

## Typing and Send Mode

Typing simulation is enabled for degree `>= MEDIUM`:
- Config built by `createTypingSimulationConfig(...)`
- Sends first chunk immediately, then simulates typing for subsequent chunks.

Immediate send mode is used when typing simulation is disabled.

## Message Flood Guard

`STREAMING_LIMITS.MAX_FLUSH_COUNT` (from `rateLimiter.ts`) caps total sent messages per stream session in production.

If limit is hit:
- Stream requests graceful stop
- Warning embed is sent
- Extra flushes are suppressed to avoid duplicate limit embeds

## Debugging Checklist

Useful log lines:
- `Stream API: Raw chunk received: ...`
- `Stream Seg: Flushing oversized regular buffer at safe breakpoint (...)`
- `Stream Send: Humanized (D3) from ... to ...`
- `Stream Send: Sent message (N): ...`
- `[Unique Emoji] ...` logs from emoji dedup layer

When output looks odd:
1. Check whether weird split happened at buffer flush or chunking stage.
2. Check if `filterDuplicateCustomEmojis(...)` removed an emoji.
3. Check degree (`humanizer_degree`) because D3 enables period flush and post-chunk humanization.
4. Check whether output contained incomplete semantic markers delaying flush.

## Practical Test Prompts

Use exact-output prompts to isolate formatter behavior:

1. Newline punctuation case:
```text
Reply with EXACTLY this text. Preserve line breaks:
hello there
.
```

2. Emoji + punctuation line case:
```text
Reply with EXACTLY this text. Preserve line breaks:
:poggers:
,
:xdd:
,
```

3. Long overflow case (forces fallback flush):
```text
Write one paragraph over 1500 characters without code blocks. Keep punctuation natural.
```

4. Degree 3 boundary case:
```text
Write 6-8 short sentences, each ending with a period, with one newline in the middle.
```

Expected:
- No standalone punctuation-only Discord messages.
- No broken `:emoji:` token splitting due to newline carry.
- Large buffers split near natural boundaries, not abrupt hard cuts.
