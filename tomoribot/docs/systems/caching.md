# 16. In-Memory Caching System

This document reflects current cache layers in `src/utils/cache/` and related modules.

## Why Caching Matters Here

TomoriBot reads server config, user state, memories, and tool capability metadata on almost every interaction.
Caching reduces repeated DB/API calls and helps meet Discord interaction timing constraints.

## Active Cache Layers

### 1) Tomori state cache (`tomoriStateCache.ts`)

- Key: `serverDiscId`
- Stores all personas for a server + main persona shortcut
- Default TTL: `TOMORI_STATE_CACHE_TTL_MINUTES` (default 10)
- Main APIs:
  - `getCachedAllPersonas(serverDiscId)`
  - `getCachedMainPersona(serverDiscId)`
  - `invalidateTomoriStateCache(serverDiscId)`
- Note: `getCachedTomoriState` is kept as a compatibility wrapper.

### 2) User cache (`userCache.ts`)

- Key: `userDiscId`
- Stores user row, privacy level, and per-server blacklist sub-cache
- Default TTL: `USER_CACHE_TTL_MINUTES` (default 30)
- APIs:
  - `getCachedUserRow`, `getCachedPrivacyLevel`, `getCachedBlacklistStatus`
  - `invalidateUserCache`, `invalidateUserBlacklistCache`

### 3) Emoji/sticker cache (`emojiStickerCache.ts`)

- Key: internal `server_id`
- Stores expression rows loaded from DB after lazy sync checks
- Default TTL: `EMOJI_STICKER_CACHE_TTL_MINUTES` (default 10)
- API: `loadEmojiStickerCache`, `invalidateEmojiStickerCache`

### 4) Channel whitelist cache (`channelWhitelistCache.ts`)

- Key: `serverDiscId:channelDiscId:parentChannelDiscId:roleSignature`
- Stores whitelist decision (channel + role) + optional channel cooldown overrides
- For thread triggers, the parent channel ID is part of the cache key so parent-whitelist inheritance does not collide with non-thread checks
- Default TTL: `CHANNEL_WHITELIST_CACHE_TTL_MINUTES` (default 5)
- API: `getCachedWhitelistStatus`, `invalidateWhitelistCache`

### 5) Short-term memory cache (`shortTermMemoryCache.ts`)

- Keys:
  - user-scoped: `shortterm:user:{userId}:{channelId}` (persona-scoped variant includes `:{tomoriId}`)
  - server-shared: `shortterm:server:{serverId}:{channelId}` (persona-scoped variant includes `:{tomoriId}`)
- Stores per-channel conversation snippets and optional summaries
- Guild behavior: the latest STM for a persona in a channel is shared across that server's other channels; user-scoped STM is retained for cross-server opt-in behavior
- When the triggering user message explicitly asks Tomori to remember something for future use, STM tool nudges are suppressed for that turn so long-term memory tools take priority; raw short-term conversation capture still continues after the reply
- TTL env vars:
  - `SHORT_TERM_MEMORY_TTL_HOURS`
  - `SHORT_TERM_MEMORY_SUMMARY_TTL_HOURS`
- Code fallback defaults are 12h/24h; deployers commonly override in `.env`.
- APIs:
  - `storeShortTermMemory`, `getShortTermMemoryForUserChannel`, `getShortTermMemoryForServerChannel`
  - `getShortTermMemoriesForUser`, `getShortTermMemoriesForServer`
  - `updateShortTermMemorySummary`
  - `clearShortTermMemoryForUser`, `clearShortTermMemoryForChannel`

### 6) LLM model cache (`llmCache.ts`)

- Key: `llm_id`
- Warmed at startup from `llms` table
- No runtime TTL/invalidation
- APIs: `initializeLLMCache`, `getCachedLLM`, `getCachedLLMsByProvider`, `getCachedDefaultLLM`

### 7) OpenRouter capability cache (`openrouterCapabilityCache.ts`)

- Key: `llm_codename`
- Warmed at startup from OpenRouter models API
- Stores tools/vision/structured-output capability + token limits
- No runtime TTL/invalidation

### 8) Gemini token-limit map (`geminiCapabilityCache.ts`)

- Static in-memory lookup map for known Gemini model token limits

### 9) NovelAI token-limit map (`novelaiCapabilityCache.ts`)

- Static in-memory lookup map for known NovelAI model token limits

### 10) Webhook cache (`utils/discord/webhookManager.ts`)

- Keys:
  - channel webhook cache (`channelId`)
  - persona webhook cache (`channelId:personaId`)
- No TTL; invalidated on delete/change conditions

### 11) Preset avatar cache (`utils/image/avatarHelper.ts`)

- Warmed at startup from preset rows
- No TTL; refresh via restart/re-init

## Cache Invalidation Rules (Critical)

Invalidate after successful DB writes that affect cached reads.

Common examples:

- server/persona/config changes -> `invalidateTomoriStateCache(serverDiscId)`
- user preference/memory changes -> `invalidateUserCache(userDiscId)`
- blacklist toggles -> `invalidateUserBlacklistCache(serverDiscId, userDiscId)`
- whitelist/inherited cooldown override changes -> `invalidateWhitelistCache(serverDiscId, channelDiscId?)`
- emoji/sticker update events -> `invalidateEmojiStickerCache(serverId)`
- persona webhook/avatar changes -> webhook invalidation helpers

## Anti-Patterns to Avoid

- Invalidating before write success
- Forgetting invalidation on alternate code paths
- Manually mutating cached objects instead of invalidating
- Clearing whole caches when only one key changed

## Recommended Env Knobs

```env
TOMORI_STATE_CACHE_TTL_MINUTES=10
USER_CACHE_TTL_MINUTES=30
EMOJI_STICKER_CACHE_TTL_MINUTES=10
CHANNEL_WHITELIST_CACHE_TTL_MINUTES=5
SHORT_TERM_MEMORY_TTL_HOURS=2
SHORT_TERM_MEMORY_SUMMARY_TTL_HOURS=4
SHORT_TERM_MEMORY_MAX_SUMMARY_LENGTH=500
SHORT_TERM_MEMORY_MIN_MESSAGES_FOR_SUMMARY=6
SHORT_TERM_MEMORY_MAX_MESSAGES_PER_CHANNEL=10
SHORT_TERM_MEMORY_MAX_OTHER_CHANNELS=3
```

## Practical Rule

If a code path writes DB state that a cache reads, keep the invalidation call in the same function directly after the write.
