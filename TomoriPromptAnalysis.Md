# Tomori Prompt Analysis

## Scope
This analysis is based on `tomoribot_reference` source code (TypeScript implementation), focused on:
- Prompt/context construction
- How incoming messages are judged as relevant enough to reply
- Exact API payload structure sent to providers
- Memory behavior (`/teach memory`, `remember_this_fact`, short/long memory)
- Emoji/sticker/GIF behavior
- `/tool refresh` behavior

---

## 1) How Tomori Handles Prompting

### High-level pipeline
1. `tomoriChat.ts` fetches recent channel history (`MESSAGE_FETCH_LIMIT`, default `80`) and builds a simplified message timeline.
2. It slices history from the latest reset marker (`/tool refresh` embed or compact-refresh embed behavior).
3. `buildContext(...)` in `contextBuilder.ts` builds structured context items.
4. Provider adapters convert those context items into provider-specific request format:
   - Google Gemini format (`systemInstruction` + `contents`)
   - OpenAI-style messages for OpenRouter/custom providers
5. Stream orchestrator sends incremental output, runs tool calls, and loops with tool results when needed.

### What goes into the context
`buildContext(...)` adds sections in a deliberate order:
- System/humanizer rules
- Persona/personality attributes
- Server (or DM) info
- Server long-term memories
- Server emoji knowledge (with semantic metadata)
- Server sticker knowledge (with semantic metadata)
- Optional server document chunks (RAG) from latest user query
- Users in conversation block (mention handles, user details, reminders, time/channel context)
- Short-term memory blocks (cross-channel and same-channel summaries/hints)
- Sample dialogues
- Conversation history (text + media placeholders/parts)
- Optional end-of-context prompts (short-term memory creation hint, uncensor injection)

### Important prompt quality behaviors
- It heavily structures prompt segments instead of using one giant plain text prompt.
- It keeps “stable” sections in system instruction area to improve cache stability and consistency.
- It enriches context with server-specific emoji/sticker metadata and optional document retrieval.
- It includes short-term memory hints so the model can self-maintain conversation summaries.

---

## 2) How Tomori Checks If a User Message Is Relevant

### Direct trigger/reply logic (no deep semantic classifier)
Tomori mostly decides reply relevance via trigger rules, not semantic intent classification:
- Reply to bot or persona message
- Bot mention
- Trigger word match (main persona + alter personas)
- Auto-message threshold hit in configured auto channels (`autoch_threshold`)

### Trigger matching details
- Mention-style triggers (`<@...>`) are supported.
- Japanese triggers use substring match.
- English triggers use “screaming-aware” regex, so elongated spellings still match.

### Additional gates
Even if trigger matches, there are extra filters:
- Full privacy users are silently ignored (unless manual trigger flows/reminders).
- Channel whitelist and cooldown checks are applied.
- Self-reply chain limits are enforced.

### Context relevance vs reply relevance
- Reply decision: trigger/cooldown/whitelist-based.
- Context inclusion: message-window + reset marker based.
- It does **not** run a semantic “is this message on-topic?” classifier for every message; it uses bounded history and reset boundaries.

---

## 3) What Tomori Sends to the API

## Google (Gemini)
Call pattern:
```ts
genAI.models.generateContentStream({
  model,
  contents: finalContents,
  config: requestConfig,
})
```

`requestConfig` may include:
- `systemInstruction`
- `safetySettings`
- generation config / thinking config
- `tools`

`finalContents` includes:
- Dialogue contents converted from structured context items
- Optional accumulated model parts (prefill/continuation)
- Function interaction history (tool call + tool response context)

## OpenRouter
Endpoint:
- `POST https://openrouter.ai/api/v1/chat/completions`

Body shape:
```json
{
  "model": "...",          // omitted if account-setting
  "messages": [...],
  "temperature": 0.x,
  "stream": true,
  "stream_options": { "include_usage": true },
  "max_tokens": 4096,
  "tools": [...],
  "top_p": 0.9,
  "top_k": 40,
  "frequency_penalty": 0.3,
  "presence_penalty": 0.2,
  "repetition_penalty": 1.1
}
```

Message assembly:
- System sections are merged into one system message.
- Dialogue history becomes user/assistant messages.
- Function history is appended as assistant `tool_calls` + tool result messages.

## Custom endpoint (OpenAI-compatible)
Endpoint:
- user-configured base URL normalized to `/chat/completions`

Body shape:
```json
{
  "model": "...",
  "messages": [...],
  "temperature": 0.x,
  "stream": true,
  "max_tokens": 4096,
  "tools": [...],
  "top_p": 0.9,
  "frequency_penalty": 0.3,
  "presence_penalty": 0.2
}
```

Same general message strategy as OpenRouter (system + dialogue + tool history).

---

## 4) Are `teach memory` and `remember` Basically the Same?

Note: In current Tomori TypeScript source there is no `/remember` slash command; the "remember" path is the `remember_this_fact` tool call.

Short answer: same goal, different mechanism and guardrails.

### `/teach memory` (user command)
- Explicit slash command flow (`/teach memory personal` or `/teach memory server`)
- User writes memory via modal
- Direct DB write
- Works even if model tool-calling is not involved

### `remember_this_fact` (LLM tool call)
- Called by the model itself during chat
- Requires self-teaching feature enabled
- Has stronger target-user validation (Discord ID + nickname consistency checks)
- Subject to tool call loop behavior and tool availability

### Notable privacy difference
- `/teach memory personal`: blocks FULL privacy.
- `remember_this_fact` for personal scope: blocks PARTIAL and FULL privacy.

So they overlap conceptually (store long-term memory), but they are not identical in execution path or restrictions.

---

## 5) Easy Explanation: Short-Term vs Long-Term Memory

### Short-term memory (easy terms)
- Think: “recent chat notes.”
- Stored in memory cache (temporary), per user+channel.
- Used to remember recent topic/story and cross-channel recent context.
- Expires by TTL and can be cleared quickly (`/tool refresh`, `/personal cache clear`).

### Long-term memory (easy terms)
- Think: “saved facts that stick around.”
- Stored in database (`server_memories`, personal memories in user records).
- Persists across sessions/restarts.
- Used for stable preferences/facts about server or user.

---

## 6) Emojis, Stickers, and GIFs

### Emojis
- Server emoji metadata is injected into context as knowledge.
- Output pipeline can convert `:name:` to real Discord custom emoji.
- Duplicate recent custom emoji usage is filtered from generated output.
- Additional emoji-penalty guidance is injected when recent bot messages overuse custom emojis.

### Stickers
- Model can call `select_sticker_for_response(sticker_name)`.
- Tool validates sticker name against guild cache (with refresh fallback).
- Sticker is selected during tool phase, then sent after final text stream completes.
- For alter/webhook persona flows, it may send sticker URL via webhook path first, then fallback to sticker send API.

### GIFs
- Tenor links are resolved to direct media URLs.
- In development mode, `process_gif` tool can extract keyframes and restart generation with enhanced context.
- In production mode, GIF processing is intentionally constrained (placeholder-style handling) to avoid memory pressure/OOM risk.

---

## 7) `/tool refresh` Command (What It Actually Does)

`/tool refresh` does two important things:

1. Clears short-term memory cache for the current channel
- Calls `clearShortTermMemoryForChannel(channelId)`.
- Removes temporary short-term entries for all users in that channel.

2. Inserts a reset marker message/embed
- Sends localized “conversation history cleared/refreshed” embed.
- Future context building scans backward for latest reset marker and slices history from there.
- Effect: messages above the marker are ignored in subsequent prompt context.

In practice, `/tool refresh` is both:
- A memory/cache reset for short-term channel data
- A hard context boundary for prompt history inclusion

---

## 8) Practical Takeaways For Improving Your Bot

If your bot responses are underperforming versus Tomori behavior, the biggest differences to replicate are:
- Structured context assembly (not just raw transcript)
- Trigger + channel-boundary logic (`/tool refresh` style hard reset markers)
- Server-specific emoji/sticker semantic conditioning
- Tool-loop support with function history re-fed into model
- Split short-term vs long-term memory responsibilities



