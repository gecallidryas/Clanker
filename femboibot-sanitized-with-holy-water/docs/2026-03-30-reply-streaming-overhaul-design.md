# FemboiBot Reply Streaming Overhaul Design

## Summary

This document defines a mature streaming reply pipeline for FemboiBot's mention/reply chat flow in `discord.py`.
The design keeps the existing non-streaming path as a fallback, adds a provider-agnostic streaming engine, and is structured so slash-command AI paths can adopt the same engine later.

Confirmed implementation decisions:

1. Mention/reply chat adopts streaming first.
2. Only one active AI stream is allowed per channel.
3. A dedicated debug/thought channel is preferred, with explicit opt-in reuse of the mod-log channel allowed.
4. Interrupted partials append a visible interruption hint if meaningful text was already sent; otherwise they use the normal failure/retry path.
5. Custom endpoints are treated as OpenAI-compatible only when config/capability flags explicitly say so.
6. The missing `docs/FEATURES.md` path is treated as a stale reference from the unsanitized repo.

## Current Pipeline Analysis

### Current reply flow

The current flow in `discord_bot/cogs/ai_brain.py` is:

1. `on_message(...)` decides whether the bot should answer.
2. The bot builds prompt/context and enters a single `message.channel.typing()` scope.
3. `generate_response(...)` chooses OpenRouter, custom endpoint, or Gemini and returns one final string.
4. Tool calls are extracted from the completed string with regex-based parsing.
5. Final visible text is cleaned and split with `split_message(...)`.
6. The first chunk is sent as `message.reply(...)`; later chunks are sent with `channel.send(...)`.

### Strengths worth preserving

- `ai_brain.py` already has a single high-level entry point for mention/reply chat.
- `guild_ai.py` already centralizes guild-specific provider and key selection.
- `config.py` and `db_handler.py` already provide a guild configuration surface that can host streaming controls.
- `output_cleaner.py` and `text_splitter.py` provide a starting point for output hygiene and Discord-safe chunking.

### Likely weak points

- Provider calls are one-shot only. There is no stream event surface for text deltas, tool boundaries, moderation stops, or reasoning.
- `generate_response(...)` collapses provider failures into plain strings, which makes transport failure and model output hard to distinguish.
- Tool calls are discovered only after the model finishes the whole turn, so the bot cannot flush safe text before tool execution.
- The Gemini path flattens structured chat messages into `ROLE: content` text, which is hostile to native tool and multimodal evolution.
- The custom endpoint path stores capability flags but does not actually use them for dispatch decisions.
- `split_message(...)` is only a final splitter. It is not sentence-aware, stall-aware, or flood-aware during generation.
- There is an incoming request rate limiter, but no outgoing streaming budget for per-turn Discord sends.
- Typing state exists only as one coarse `typing()` context around the initial generation call, not as a channel-scoped keepalive covering stream, tool work, and retries.
- There is no stream-specific telemetry, finish-reason logging, or optional thought/debug channel handling.

## Design Goals

- Stream visible assistant text without spamming tiny Discord messages.
- Flush on meaningful semantic boundaries when possible.
- Preserve Discord-safe chunking for long replies, code blocks, URLs, and emoji tags.
- Enforce one active AI stream per channel.
- Keep typing state active while the bot is still working.
- Flush safe partial output on provider interruption, moderation stop, or tool-call boundary.
- Support optional provider thought/reasoning logging in a privacy-aware, admin-controlled way.
- Keep existing non-streaming behavior available as a fallback.
- Be extensible enough for slash-command AI paths later.

## Architecture Options

### Option A: Inline streaming inside `ai_brain.py`

Add provider streaming directly into the existing cog and keep buffering and send policy inside `on_message(...)`.

Pros:

- Fastest to prototype.
- Lowest short-term file count.

Cons:

- Makes the existing cog even more complex.
- Hard to test buffering, typing, and send behavior independently.
- Couples provider parsing to Discord message policy.

### Option B: Dedicated stream orchestrator with provider adapters

Introduce a provider-agnostic `StreamOrchestrator` that consumes normalized provider events and owns buffering, flush policy, Discord sending, typing, and interruption behavior.

Pros:

- Best separation of concerns.
- Easy to test with fake provider streams.
- Cleanest way to support tools, partials, thought logging, and slash-command reuse later.

Cons:

- Requires a small new internal module set.
- Slightly more up-front refactor work.

### Option C: Channel-scoped session manager plus orchestrator

Build Option B, then wrap it with a channel-level session registry that handles cancellation, stop/supersede behavior, and exclusive ownership.

Pros:

- Best concurrency model for Discord channels.
- Simplifies stop/supersede logic.

Cons:

- Slightly more machinery than Option B alone.

### Recommendation

Use Option B as the core implementation and add the minimal channel-session layer from Option C.
That gives the design a stable streaming engine without overbuilding a job system.

## Recommended Pipeline

### Core request objects

Introduce internal request/result objects, for example:

- `TurnRequest`: guild, channel, user, source message, system prompt, chat messages, attachments/media context, enabled tools, provider preference, and guild config snapshot.
- `StreamEvent`: normalized provider events such as `text_delta`, `reasoning_delta`, `tool_call`, `provider_error`, `moderation_stop`, and `done`.
- `StreamResult`: visible text sent, finish reason, partial flag, provider/model metadata, tool-call payload, and optional thought log payload.

### Main flow

1. `ai_brain.py` continues deciding whether a message should get an AI reply.
2. `ai_brain.py` builds a `TurnRequest`.
3. A channel-scoped stream registry grants exclusive ownership for that channel.
4. A provider adapter in `guild_ai.py` or `api_manager.py` is selected.
5. The provider adapter emits normalized `StreamEvent` objects.
6. `StreamOrchestrator` processes events, maintains the semantic buffer, and sends Discord messages through a `DiscordReplySession`.
7. If a `tool_call` event is reached, the orchestrator flushes pending visible text first and returns control to `ai_brain.py`.
8. `ai_brain.py` executes the tool, appends tool results to chat state, and starts the next streamed model pass.
9. When the stream finishes, the orchestrator returns structured metadata for memory, stats, and optional thought logging.

### Non-streaming fallback

Keep the existing final-text path for:

- providers without stream support,
- guilds with streaming disabled,
- temporary rollback,
- provider-specific stream failures that occur before any visible text is sent.

The fallback path should reuse the same final chunking and output-cleaning rules where possible so behavior stays consistent.

## Provider Compatibility

### Gemini

- Add a Gemini stream adapter instead of only `generate_content(...)`.
- Stop flattening structured chat into plain `ROLE:` text when the underlying Gemini path can accept richer structured input.
- If Gemini streaming is unavailable for a particular model or configuration, use the one-shot fallback.

### OpenRouter

- Add an OpenRouter stream adapter via the OpenAI-compatible streaming interface.
- Normalize provider-native chunks into plain text deltas, finish reasons, and tool-call events where available.

### Custom endpoint

- Default assumption: text-only, best-effort, non-streaming.
- Only treat a custom endpoint as OpenAI-compatible for streaming or tool calls when capability/config flags explicitly say so.
- Capability flags should drive dispatch behavior, not just be stored.

### Multimodal context

- Current image/video description pre-processing can stay in place initially.
- The request shape should still allow structured multimodal parts later so the streaming engine is not tied to text-only prompts forever.

## Buffering and Flush Strategy

### Buffer model

Maintain separate buffers/state for:

- visible reply text,
- pending reasoning/thought text,
- provider tool-call assembly,
- stream metrics and timing,
- code-fence and semantic-marker state.

### Flush triggers

Use hard and soft flush triggers.

Hard flush triggers:

- tool-call boundary,
- provider `done`,
- provider error,
- moderation interruption,
- explicit stop/cancel,
- code-fence open/close when enough buffered text exists.

Soft flush triggers:

- paragraph break,
- newline boundary,
- sentence-ending punctuation followed by whitespace/newline,
- stall-based flush after buffered meaningful text sits too long without a better boundary.

### Semantic buffering rules

Defer soft flushes while the buffer appears to contain incomplete structures such as:

- unmatched code fences or inline backticks,
- incomplete markdown link syntax,
- incomplete URL prefixes,
- partial custom emoji tags or shortcodes,
- obviously unfinished quotes or parenthetical tails.

The goal is not perfect linguistic parsing; it is to avoid visibly broken Discord output.

### Max-size fallback

If no good boundary appears and the buffer becomes too large:

1. Prefer the nearest forward sentence/newline boundary.
2. Otherwise prefer the nearest backward sentence/newline boundary.
3. Otherwise fall back to whitespace.
4. Otherwise hard-cut at the configured target.

This fallback should loop so very large buffered text drains safely in multiple segments rather than one giant burst.

### Final flush behavior

On `done`, `tool_call`, moderation stop, timeout, or provider error:

- flush remaining safe visible text,
- auto-close formatting-critical markers such as code fences if needed to avoid broken Discord rendering,
- avoid inventing semantic content,
- append the configured interruption hint when a partial reply was already visible and the finish reason is an interruption class.

## Discord Send/Edit Behavior

### First reply

- Do not send a placeholder message by default.
- Start with typing only.
- Send the first visible Discord message only when the buffer reaches a meaningful flush point or a stall timeout forces a first flush.
- The first visible bot message should use `message.reply(..., mention_author=False)` so threading stays intact.

### Subsequent chunks

- Prefer discrete `channel.send(...)` follow-up messages after the first reply.
- Do not update the same message every few hundred milliseconds.

### Edit policy

Allow at most a very small edit window for the newest unsent/just-sent chunk to avoid tiny first messages.
Example policy:

- one optional warm-up edit within a short time window,
- no repeated token-by-token edits,
- once a message is considered sealed, future output becomes follow-ups only.

This keeps output readable and avoids Discord edit spam.

### Typing management

- Use a channel-scoped typing keepalive task instead of one coarse `typing()` context.
- Typing remains active while provider streaming, tool execution, or automatic continuation is still in progress.
- Typing stops immediately on final completion, cancellation, or unrecoverable failure.

## Flood Protection and Anti-Spam Controls

Enforce per-turn output budgets, not just per-user input limits.

Recommended controls:

- minimum flush interval,
- minimum flush size for non-final sends,
- maximum messages per turn,
- maximum total visible characters per turn,
- punctuation-only merge rules,
- coalescing of tiny fragments during stalls,
- per-channel single active stream ownership,
- graceful truncation with a final notice when the send budget is exhausted.

If the stream hits the message budget, it should stop cleanly and tell the user to ask for continuation rather than continuing to spray follow-up messages.

## Error Handling

### Provider timeout or stall

- If no visible text was sent, use the normal failure/retry path.
- If meaningful visible text was already sent, flush the safe tail and append a visible interruption hint such as "Interrupted, ask me to continue."

### Partial stream failure

- Preserve already-sent text.
- Flush any safe pending buffer.
- Mark the result as partial so metrics and optional debug logging can tell the difference between a completed answer and an interrupted one.

### Malformed chunks

- Skip isolated malformed provider events with warnings.
- Abort only after a small consecutive-malformed-event threshold.
- If aborting after partial visibility, append the visible interruption hint.

### Moderation interruption

- Flush already-approved visible text only.
- Never emit blocked raw content into normal chat or thought logs.
- End with a neutral stop notice if anything visible was already sent.

### Cancellation and supersede

- A newer stream request for the same channel should supersede the old session if policy allows.
- On supersede or stop, stop typing immediately.
- If visible text was already sent, append the interruption hint once.

## Thought and Reasoning Logging

### Principles

- Off by default.
- Admin-controlled only.
- Dedicated thought/debug channel preferred.
- Reusing mod-log is allowed only via explicit config.
- Reasoning logs are never posted back into the source conversation channel.
- Reasoning logs are never added to short-term conversation memory.

### Log levels

- `off`: no thought logging.
- `summary`: log only provider-exposed summary-level reasoning or orchestrator summaries.
- `raw_debug`: log raw provider reasoning chunks only when the provider explicitly exposes them and the guild enables it.

### Privacy rules

- Default to not including full user prompt content in thought logs.
- Sanitize mentions, URLs, and attachment references unless explicitly enabled.
- Never fabricate hidden chain-of-thought from internal model state that is not actually surfaced by the provider.
- If the configured channel is missing or inaccessible, skip thought posting without failing the main reply.

### Logged metadata

Thought/debug posts should include:

- guild and channel identifiers,
- source message link if available,
- provider and model,
- finish reason,
- partial/completed status,
- tool-loop count,
- latency summary,
- sanitized thought payload.

## Tool Calls in the Stream Loop

Tool support should move from post-hoc string parsing to stream-time boundaries.

Recommended behavior:

1. Provider adapter assembles tool-call data until it is complete enough to execute.
2. Orchestrator flushes pending visible text before yielding control.
3. `ai_brain.py` executes the tool with the existing tool registry/context system.
4. Tool result is appended to the conversation state.
5. A new streamed model pass starts with the updated message history.

Important rules:

- Visible text before a tool boundary should not be lost.
- Raw tool JSON should not leak into the user-visible reply.
- If a tool returns a user-facing short-circuit result, the orchestrator should finalize cleanly without starting another provider pass.
- Tool-call loop limits should remain explicit.

## File-by-File Refactor Plan

### Modify

- `discord_bot/cogs/ai_brain.py`
  - Extract mention/reply turn execution into a reusable turn runner.
  - Replace direct one-shot send flow with orchestrator invocation plus fallback handling.
  - Keep tool-loop ownership here.

- `discord_bot/utils/guild_ai.py`
  - Add provider capability resolution.
  - Route to streaming or fallback paths based on guild config and provider support.
  - Honor custom endpoint capability flags.

- `discord_bot/utils/api_manager.py`
  - Add stream adapters for Gemini/OpenRouter/custom endpoint where supported.
  - Normalize provider-native chunks into shared event types.
  - Return structured finish reasons instead of only raw strings.

- `discord_bot/utils/text_splitter.py`
  - Either evolve it into a semantic chunker or replace it with a shared stream/final chunking utility used by both streaming and fallback.

- `discord_bot/utils/rate_limiter.py`
  - Keep current inbound limiter.
  - Add a stream-session send budget helper or companion limiter for outbound flood protection.

- `discord_bot/utils/logger.py`
  - Add structured per-turn stream logging helpers and consistent stream event fields.

- `discord_bot/cogs/config.py`
  - Add admin commands/view fields for streaming mode, send-budget knobs, and thought-log config.

- `discord_bot/utils/db_handler.py`
  - Add schema fields, migrations, and audit support for new streaming/thought-log settings.

### Add

- `discord_bot/utils/streaming/types.py`
  - Shared request, event, state, and result dataclasses.

- `discord_bot/utils/streaming/orchestrator.py`
  - Main stream processing loop.

- `discord_bot/utils/streaming/buffer.py`
  - Semantic buffer and flush-index logic.

- `discord_bot/utils/streaming/chunker.py`
  - Discord-safe chunk splitting used after each flush.

- `discord_bot/utils/streaming/discord_sender.py`
  - Reply/follow-up/edit policy and send budget enforcement.

- `discord_bot/utils/streaming/typing_manager.py`
  - Channel-scoped typing keepalive.

- `discord_bot/utils/streaming/session_registry.py`
  - One active stream per channel, stop/supersede coordination.

- `discord_bot/utils/streaming/thought_logger.py`
  - Optional debug/thought channel posting and sanitization.

### Tests to add

- `tests/test_stream_buffer.py`
- `tests/test_stream_chunker.py`
- `tests/test_stream_orchestrator.py`
- `tests/test_stream_discord_sender.py`
- `tests/test_stream_provider_adapters.py`
- `tests/test_stream_thought_logging.py`

## Staged Rollout

### Phase 1: Shared send and chunk policy

- Extract chunk/send behavior behind a reusable interface.
- Keep all provider calls one-shot.
- Verify no user-visible regression in current fallback behavior.

### Phase 2: Orchestrator with pseudo-stream input

- Feed completed text through the orchestrator as a fake stream.
- Validate buffering, typing keepalive, and flood controls without provider stream risk.

### Phase 3: OpenRouter and explicit OpenAI-compatible custom endpoint streaming

- Add real provider streaming where the transport shape is easiest.
- Keep text-only fallback for custom endpoints without explicit compatibility flags.

### Phase 4: Gemini streaming

- Add Gemini event normalization and structured finish reasons.
- Remove unnecessary prompt flattening where streaming path supports richer input.

### Phase 5: Stream-time tool boundaries

- Flush visible text before tool execution.
- Preserve current tool-loop safety limits.

### Phase 6: Thought logging and guild rollout

- Add summary-level debug logging first.
- Keep raw debug reasoning behind explicit admin opt-in.
- Roll out per guild with a config flag before considering a broader default.

## Testing Strategy

### Unit tests

- sentence/newline flush boundaries,
- semantic holdback markers,
- code-fence and URL chunking,
- punctuation-only fragment merge,
- overflow fallback selection,
- interruption hint insertion rules,
- config/capability-based dispatch.

### Integration tests

Use fake async providers that emit:

- normal text deltas,
- delayed/stalled output,
- malformed chunks,
- moderation stops,
- tool-call boundaries,
- timeout/error after partial send,
- oversized outputs that hit send budgets.

### Discord behavior tests

Mock Discord channel/message objects to verify:

- first message uses reply,
- later messages use follow-ups,
- edit window is bounded,
- typing keepalive starts and stops correctly,
- interruption hints appear only when required,
- one active stream per channel is enforced.

### Canary rollout

- Enable streaming only in a debug guild first.
- Keep thought logging off at first.
- After send behavior is stable, enable summary-level thought logging in a dedicated debug channel.

## Open Questions for Later Implementation Planning

- Exact default values for flush thresholds, send budgets, and stall timers.
- Whether slash-command AI responses should share identical send/edit policy or a slightly different interaction-aware adapter.
- Whether to expose a user/admin stop command for active channel streams in the first implementation phase.
- Whether multimodal native streaming should be implemented immediately after text streaming or deferred behind the existing image/video description path.
