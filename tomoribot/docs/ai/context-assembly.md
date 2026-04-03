# Context Assembly

> How TomoriBot builds the LLM prompt from server state, user data, conversation history, and optional ST presets.

## Overview

Context assembly is the process of transforming raw server/user/conversation state into a structured array of `StructuredContextItem[]` that providers send to the LLM. The entry point is `buildContext()` in `src/utils/text/contextBuilder.ts`.

The system has two modes:

1. **Native assembly** — Fixed 9-block structure, always available, no configuration needed
2. **Preset-driven assembly** — When a SillyTavern preset is active, native blocks are rearranged according to the preset's node order (see [ST Preset System](../integrations/sillytavern-preset-system.md))

If no preset is active (the default), the system behaves exactly as native assembly. The preset path is fully transparent to callers.

## Architecture

```text
buildContext(params)          ← routing wrapper (exported)
  │
  ├─ Active preset? ──yes──→ buildContextNative(params)
  │                            → reassembleWithPreset(nativeOutput, preset)
  │                            → return rearranged items
  │
  └─ No preset ──────────→ buildContextNative(params)
                             → return native items directly
```

### BuildContextParams

All callers pass a single `BuildContextParams` object (exported from `contextBuilder.ts`). Key fields:

| Field | Type | Purpose |
|-------|------|---------|
| `guildId` | `string` | Discord server ID |
| `simplifiedMessageHistory` | `SimplifiedMessageForContext[]` | Preprocessed conversation messages |
| `triggererName` | `string` | Display name of the user who triggered the response |
| `tomoriNickname` | `string` | Bot's display name (persona-aware) |
| `tomoriAttributes` | `string[]` | Personality attribute lines |
| `tomoriConfig` | `TomoriConfigRow` | Server-level bot configuration |
| `personaPrompt` | `string \| null` | Persona-specific system prompt |
| `snapshot` | `RequestSnapshot` | Pre-loaded caches (tomoriState, etc.) |
| `isUserImpersonation` | `boolean` | Whether this is a user impersonation request |

### BuildContextResult

```typescript
{
  contextItems: StructuredContextItem[];  // Ordered prompt segments
  tailDirectives: string[];               // End-of-prompt instructions
  uncensorDirective?: string;             // Optional uncensor instruction
}
```

## StructuredContextItem and MetadataTag

Each context item has:

```typescript
{
  role: "system" | "user" | "model";
  parts: ContextPart[];          // Text, image, or video segments
  metadataTag?: ContextItemTag;  // Semantic tag for identification
}
```

The `metadataTag` is a stable interface between the native builder and the preset builder. It identifies *what kind of content* each item carries, allowing the preset system to rearrange items without understanding their internal structure.

### Tag Reference

| Tag | Block # | Description | Configured via |
|-----|---------|-------------|---------------|
| `SYSTEM_HUMANIZER_RULES` | 1 | System prompt + persona prompt | `/sysprompt`, `/persona` |
| `SYSTEM_PERSONALITY` | 2 | Personality attributes | `/teach attribute`, `/forget attribute` |
| `KNOWLEDGE_SERVER_INFO` | 3 | Server name, description, channel info | Automatic (Discord metadata) |
| `KNOWLEDGE_SERVER_MEMORIES` | 4 | Server-level memories | `/teach memory server`, `/forget memory server` |
| `KNOWLEDGE_SERVER_EMOJIS` | 5 | Available custom emojis | `/server initialize expressions` |
| `KNOWLEDGE_SERVER_STICKERS` | 6 | Available stickers | `/server initialize expressions` |
| `KNOWLEDGE_USERS_IN_CONVERSATION` | 7 | User list + personal memories + status + reminders + time/channel info | `/teach memory personal`, `/forget memory personal` |
| `KNOWLEDGE_SHORT_TERM_MEMORY` | 8 | Recent conversation summaries from other channels (STM) | `/personal cache` |
| `KNOWLEDGE_SERVER_DOCUMENTS` | 9 | RAG document chunks | `/teach document`, `/teach history`, `/forget document` |
| `DIALOGUE_SAMPLE` | 10 | Sample dialogue pairs | `/teach sampledialogue`, `/forget sampledialogue` |
| `DIALOGUE_HISTORY` | 11 | Actual conversation history | `/config maxmsgfetch` |

## Native Assembly Order

When no preset is active, `buildContextNative()` assembles items in this fixed order.
All blocks marked with `*` are conditional (only included when enabled/available in server config).

```text
 1.  System prompt (/sysprompt)                          [SYSTEM_HUMANIZER_RULES]
 2.  Persona prompt (/persona)*                          [SYSTEM_HUMANIZER_RULES]
 3.  Personality attributes (/teach attribute)*           [SYSTEM_PERSONALITY]
 4.  Server info = server name + description              [KNOWLEDGE_SERVER_INFO]
 5.  Server memories (/teach memory server)*              [KNOWLEDGE_SERVER_MEMORIES]
 6.  Server emojis*                                       [KNOWLEDGE_SERVER_EMOJIS]
 7.  Server stickers*                                     [KNOWLEDGE_SERVER_STICKERS]
 8.  Users in conversation = user list + personal         [KNOWLEDGE_USERS_IN_CONVERSATION]
     memories + status + reminders + time/channel info
 9.  Short-term memory (STM) = other-channel summaries*   [KNOWLEDGE_SHORT_TERM_MEMORY]
10.  RAG documents*                                       [KNOWLEDGE_SERVER_DOCUMENTS]
11.  Sample dialogues*                                    [DIALOGUE_SAMPLE]
12.  Conversation history                                 [DIALOGUE_HISTORY]
     + Tail directives (appended to last history item)
```

**Design note:** Volatile content (RAG, conversation history) is placed at the bottom deliberately. LLM providers like Gemini cache context from the top, so keeping stable blocks higher maximizes cache hits across requests.

The system prompt is skipped entirely for user impersonation requests (bot-specific personality should not leak).

## Preset-Driven Assembly

When a SillyTavern preset is active, the system uses a **Build-Then-Rearrange** strategy:

1. Call native `buildContextNative()` to produce all blocks (tagged with `metadataTag`)
2. Group items by tag into consumable "buckets"
3. Walk the preset's node order, pulling from buckets at marker positions
4. Insert custom preset nodes at their declared positions
5. Merge depth-injected nodes into dialogue history items
6. Flush any remaining TomoriBot-only blocks at anchor points

This avoids refactoring the native builder while gaining full preset control over prompt ordering. The native blocks still contain the same content (system prompt from `/sysprompt`, personality from `/teach attribute`, etc.) — the preset only controls **where** each block appears and **what additional content** is injected around them.

If the preset is deactivated or deleted, context assembly immediately reverts to the native fixed order above. No data is lost — `/sysprompt`, personality attributes, memories, and all other settings are stored independently from the preset.

See [ST Preset System — Context Assembly Override](../integrations/sillytavern-preset-system.md#context-assembly-override-phase-3) for the full algorithm with a worked before/after example.

## Key Behaviors

### User Impersonation Bypass

When `isUserImpersonation` is true, the preset routing is skipped entirely. Presets are character-centric (they control how the bot's persona is presented), so they don't apply when the AI is impersonating a user.

### Tail Directives

Tail directives are short instructions appended to the very last dialogue history item (closest to the model's response). They include:
- Response format hints
- Tool usage guidance
- Uncensor directives (if applicable)

These pass through unchanged in both native and preset modes.

### convertMentions()

All text content passes through `convertMentions()` before being added to context items. This function:
- Resolves `{bot}` → bot's display name
- Resolves `{user}` → triggerer's display name
- Resolves Discord mention syntax (`<@id>`) → display names
- Uses a stable "User" placeholder in system-role content to avoid cache invalidation when different users trigger the same prompt

## File Map

| File | Purpose |
|------|---------|
| `src/utils/text/contextBuilder.ts` | Routing wrapper + native 9-block assembly (~2800 lines) |
| `src/utils/text/presetContextBuilder.ts` | Preset-driven rearrangement engine |
| `src/utils/text/stPresetEngine.ts` | ST macro template engine (two-pass resolution) |
| `src/utils/cache/stPresetCache.ts` | In-memory cache for active preset + nodes |
| `src/types/misc/context.ts` | `StructuredContextItem`, `ContextPart`, `ContextItemTag` definitions |
