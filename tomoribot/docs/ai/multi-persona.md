# 17. Multi-Persona System

This document describes TomoriBot's multi-persona system: how main and alter personas are stored, triggered, and rendered (webhooks, embeds, stickers, reminders), plus operational details and limitations.

## Overview

TomoriBot supports **one main persona** plus **multiple alter personas** per server.

- **Main persona**: the default identity; responds to mentions, direct replies, and auto-message triggers.
- **Alter personas**: optional additional identities with their own trigger words and (optional) custom avatars.
- **Shared context**: all personas share the same conversation history and server memories.
- **Shared config**: all personas in a server share the same `tomori_configs` row.
- **Sequential responses**: if multiple personas match a trigger, they respond one-by-one via the channel queue.

## Data Model

### `tomoris`

Each persona is a row in `tomoris`.

Key columns:
- `is_alter`: `false` for main, `true` for alters.
- `alter_triggers`: trigger words for alters (main uses `tomori_configs.trigger_words`).
- `webhook_avatar_url`: stored alter avatar reference.
  - Production: stable public URL (S3 / CloudFront).
  - Non-production: stable local path under `data/avatars/...`, or a legacy HTTP URL until lazy migration runs.

### `tomori_configs`

Server-scoped config (shared by all personas):
- `server_id` is the primary linkage.
- `trigger_words` is used by **main persona only**.

### `reminders`

Reminders are tied to a persona to preserve the identity that set them:
- `persona_id` (nullable): the `tomori_id` that created the reminder.
- When missing or invalid, reminders **fall back to the main persona**.

## Triggering and Routing

### Direct replies and mentions

- **Reply to bot** (main persona messages) → main persona responds.
- **Reply to alter webhook message** → the matching alter responds.
  - Matching is done by webhook `author.username` → persona nickname (case-insensitive).
  - Ensure persona nicknames are unique.
- **Bot mention** → main persona responds.
- **Auto-message threshold** → main persona responds.

### Trigger words

Each persona checks its own trigger list:
- **Main**: `tomori_configs.trigger_words`.
- **Alter**: `tomoris.alter_triggers`.

If multiple personas match, they respond in deterministic order based on where their trigger first appears in the message. The per-message count is capped by `/config multitrigger`.

### Manual triggers

Manual triggers can specify `selectedPersonaId`. In that case, **only that persona responds** (fallbacks apply if missing).

Configured join welcomes also use the manual-trigger path:
- `/server welcomechannel` stores a selected persona or `Random`.
- On `guildMemberAdd`, the welcome event resolves that persona and calls `tomoriChat(..., isManuallyTriggered = true, selectedPersonaId = ...)`.
- If `welcome_persona_id` is `NULL`, one persona is chosen uniformly from the server's available personas for that join.

## Response Pipeline (Multi-Persona)

High-level flow (per incoming message):

1. Identify matching personas.
2. Queue additional personas to ensure sequential replies.
3. For each persona:
   - Build context from shared history.
   - Use isolated function-call history per persona.
   - Stream response with persona-specific webhook settings if applicable.

**Important limitation**: later personas **do not** see earlier persona responses in their context (deferred for future refactor).

## Self-Reply Chain System

To prevent infinite loops where personas continuously trigger each other, TomoriBot implements a **self-reply chain limit**.

### Overview

- **Default limit**: 3 (configurable via `/config selfreply`, max 10)
- **Scope**: Per-channel (shared across all personas)
- **Purpose**: Limit cascading persona-to-persona triggers, not user-triggered responses

### Mental Model: Nested Array

Think of the self-reply chain as a nested array with size `limit + 1`:

```javascript
// With selfReplyLimit = 3
const selfReplyChain = [
  [User/Manual],     // Index 0: Bypass phase (up to /config multitrigger per message)
  [Level 1],         // Index 1: depth = 1
  [Level 2],         // Index 2: depth = 2
  [Level 3],         // Index 3: depth = 3 (limit reached!)
  [BLOCKED]          // Index 4+: Exceeds limit, all triggers blocked
];
```

**Key concepts:**
- Each **level** = one generation of persona responses
- Each trigger message can enqueue up to the configured multi-trigger cap
- **Depth** = how many generations deep the chain has gone
- **Limit** = maximum allowed depth (not counting the user/manual trigger)

### How It Works

#### **Bypass Phase (No Limit Applied)**

These triggers do NOT increment depth and can still trigger multiple personas (up to `/config multitrigger`):

✅ **User messages** → `isSelfMessage = false`
✅ **Slash commands** (`/respond`, `/impersonate`) → `isManuallyTriggered = true`
✅ **Queued multi-persona responses** → `isManuallyTriggered = true`
✅ **Reminders** → Special flags

**Example:**
```
User: "@A, @B, @C, @D"
└─ depth = 0 (bypass phase)
└─ All 4 personas respond ✅
```

#### **Chain Phase (Limit Applied)**

Once personas respond, their messages are processed and can trigger the chain:

⚠️ **Persona message triggers another persona** → `depth += 1`

**Example with limit = 3:**
```
User: "@A"                          → depth 0 (bypass)
  A: "@B, @C"                       → depth 1 (B, C respond)
  B: "@D"                           → depth 2 (D responds)
  C: "@E"                           → depth 3 (E responds, limit reached!)
  D: "@F"                           → depth 4 (BLOCKED ❌)
  E: "@G"                           → depth 4 (BLOCKED ❌)
```

#### **Important: Depth Increments Per Trigger Message**

If one persona mentions multiple personas, depth only increments **once**:

```
A: "@B, @C, @D, @E"  → depth +1
└─ B, C, D, E all respond (one trigger message = 1 depth)
```

**NOT** per responding persona:
```
❌ WRONG: B responds → depth +1, C responds → depth +1, etc.
✅ RIGHT: One message triggers B, C, D, E → depth +1 total
```

### Chain Reset

The chain resets (depth → 0) when:

1. **User sends a message** → Immediate reset
2. **30 minutes of inactivity** → Automatic reset (`SELF_REPLY_CHAIN_TTL_MS`)

### Configuration

**Database:** `tomori_configs.self_reply_limit`
- Default: 3
- Range: 0 (disabled) to 10 (max)
- 0 = Only user/manual triggers allowed, all persona chains blocked

**Command:** `/config selfreply`

**Database:** `tomori_configs.triggered_persona_limit`
- Default: 3
- Range: 1 to 10
- Caps how many personas one message can trigger

**Command:** `/config multitrigger`

### Example Flow

**Setup:** Limit = 3, Personas A, B, C, D, E

```
Level 0: User: "@A, @B"
         └─ depth = 0, bypass phase
         └─ A, B queued to respond

Level 1: A: "Ask @C!"
         B: "Yeah, ask @C and @D!"
         └─ depth = 1 (two messages, both increment depth)
         └─ C, D respond

Level 2: C: "Hmm, ask @E!"
         └─ depth = 2
         └─ E responds

Level 3: D: "I agree with @E!"
         └─ depth = 3 (limit reached!)
         └─ E responds (last allowed)

Level 4: E: "Thanks! Ask @A!"
         └─ depth would be 4 → BLOCKED ❌
         └─ A does NOT respond

User: "Thanks everyone!"
      └─ depth = 0 (chain reset)
```

### Visual Tree Representation

```
Level 0 (User)              [User]
                               │
                    ┌──────────┴──────────┐
Level 1 (depth=1)  [A]                   [B]
                    │                     │
              ┌─────┴─────┐          ┌────┴────┐
Level 2 (d=2) [C]        [D]        [E]       [F]
               │          │          │         │
Level 3 (d=3) [G]        [H]        [I]       [J] ← LIMIT!
               │          │          │         │
Level 4       ❌         ❌         ❌        ❌  BLOCKED
```

### Key Insights

1. **User always bypasses depth** - User/manual triggers don’t consume chain depth (but still respect `/config multitrigger`)
2. **One message = one depth** - Mentioning 10 personas in one message = 1 depth increment
3. **Shared counter** - All personas share the same depth counter per channel
4. **Fair multi-triggers** - Multiple personas responding to the same message don't each add depth

### Troubleshooting

**Personas not responding after several triggers?**
- Check if self-reply limit is reached
- Look for log: `Self-reply chain limit reached (X)`
- Have a user send a message to reset the chain
- Increase limit with `/config selfreply` (max 10)

**Want to disable cascading entirely?**
- Set limit to 0: `/config selfreply limit:0`
- Only user/manual triggers will work, no persona-to-persona chains

## Webhook Strategy

Webhook usage differs by environment:

### Production

- Uses a **single channel webhook** (`TomoriBot Multi-Persona`).
- Alters send messages through that webhook with:
  - `username` = persona nickname
  - `avatarURL` = `webhook_avatar_url` (S3 URL, never expires)
- **Avatar storage**: Uploaded to S3 during import
- **Robustness**: High (S3 URLs are permanent and centralized)

### Non-production (Local Development)

- Uses the same **shared channel webhook** (`TomoriBot Multi-Persona`) as production.
- Alters send messages through that webhook with:
  - `username` = persona nickname
  - `avatarURL` = public URL built from `AVATAR_PUBLIC_BASE_URL` when configured
  - otherwise TomoriBot mutates the shared webhook avatar from the local file immediately before sending
- **Avatar storage**: Alter avatars are stored locally under `data/avatars/servers/{guildId}/personas/{personaId}/...`
- **Legacy persona webhooks** (`TomoriBot Persona {id}`) are no longer part of steady-state sending. They remain recovery sources for lazy migration and may be cleaned up manually later.

#### **Avatar URL Lifecycle (Local)**

1. **Import/default/server avatar update:** avatar is normalized to PNG and stored locally.
2. **DB write:** `webhook_avatar_url` is updated to the local stored path.
3. **Optional URL mode:** if `AVATAR_PUBLIC_BASE_URL` is configured, TomoriBot builds a public URL by stripping the `data/avatars/` prefix and appending the remainder to that base URL.
4. **Fallback mode:** if no public base URL is configured, TomoriBot loads the local file and mutates the shared webhook avatar for the send.

**Result:** Local installs no longer depend on per-persona webhooks just to persist avatar media.

#### **Lazy Migration for Existing Local Installs**

If an older local install still has an HTTP(S) avatar reference in `webhook_avatar_url`:

1. TomoriBot tries to download that avatar on first alter send.
2. The avatar is normalized to PNG, stored locally, and the DB is updated to the new local path.
3. If the HTTP(S) download fails, TomoriBot scans surviving legacy `TomoriBot Persona {id}` webhooks in the guild, recovers one avatar, stores it locally, and updates the DB.

Legacy persona webhooks are intentionally left in place by this migration. They are recovery sources, not part of the normal send path.

#### **Robustness Features (Local)**

##### **1. Auto-Recovery from Legacy Persona Webhooks**

**What:** When webhook avatar download fails (404), automatically scans guild for surviving webhooks with the same persona.

**Why:** Existing local installs may still only have webhook-backed avatar media. Recovery finds a surviving legacy webhook and migrates that avatar into local storage.

**Behavior:**
- Triggered on download failure during lazy migration
- Scans all text channels in guild for webhooks matching `TomoriBot Persona {id}`
- Downloads avatar from first surviving webhook found
- Stores avatar locally
- Updates database with the new local path
- Returns recovered avatar for immediate use

**Fallback:** If no surviving webhooks found, the send falls back to the owner name without a custom avatar (or to the original HTTP URL if it is still usable).

**Code location:** `src/utils/discord/webhookManager.ts` (`attemptWebhookAvatarRecovery`)

#### **Edge Cases (Local)**

**✅ Solved:**
1. **Webhook slot pressure** → local alters no longer create per-persona send webhooks
2. **Legacy URL expired** → lazy migration recovers from a surviving legacy webhook
3. **No public avatar host configured** → shared webhook avatar mutation fallback still preserves alter identity

**⚠️ Rare (Terminal):**
- **All legacy recovery sources gone and stored file missing** → manual re-import required
- **Operator configures `AVATAR_PUBLIC_BASE_URL` but does not actually serve `data/avatars/`** → avatar URLs will be broken until the host is fixed

**Mitigation:** Existing legacy webhooks are left untouched so old installs retain a recovery source. New installs do not need them for normal operation.

### Supported channels

Webhooks are supported in:
- `GuildText`
- `PublicThread`
- `PrivateThread`
- `AnnouncementThread`

DMs do not support webhooks.

### Failure behavior

If webhook creation or sending fails:
- A localized warning embed is shown (rate-limited).
- The bot falls back to normal messages.

## Tool Calls, Embeds, and Stickers

### Tool-call embeds

Tools can send embeds via `sendStandardEmbed`. The tool execution context includes persona webhook info:

- If a webhook is available, embeds are sent through that webhook with persona name/avatar.
- Otherwise, embeds are sent as normal bot messages.

The same shared webhook identity path is used for streamed chunks, tool embeds, generated images, sticker URL sends, reminder fallback pings, and manual alter impersonation.

### Persona IDs in context

When alter persona webhook messages are part of recent chat context, TomoriBot
surfaces those participants in "users in conversation" using the persona's
database `tomori_id` (short numeric). This avoids production/local webhook ID
differences and gives tools a stable ID for avatar targeting.

Non-persona webhook participants (if any) are still surfaced by webhook ID.
Both are rendered as regular conversation users in context (no explicit webhook/persona
identity label).
Responding alter personas are injected into that list each turn, so they can
always self-target avatar tools with their own `tomori_id` even when no previous
webhook message is present in the fetched history window.
When alter personas are active, TomoriBot suppresses the extra bot-account user
entry to avoid duplicate/confusing IDs in that list.

### Stickers (alter personas)

Discord webhooks cannot send actual stickers. For alters:
- After streaming, TomoriBot sends the **sticker CDN URL** via webhook.
- If webhook send fails, it falls back to sending the actual sticker as the bot.

Main persona uses normal sticker sends.

## Reminders (Persona-Specific)

Reminder tool now stores the creating persona:

- `create_task` saves `persona_id` in the `reminders` table.
- Reminder timer passes `selectedPersonaId` into `tomoriChat`.

Behavior:
- If the persona still exists, that persona responds.
- If the persona is missing, **fallback to main**.
- Mention verification includes webhook messages, and sends a fallback ping if the response did not mention the target.

## Commands and Workflows

### `/persona import`

- `type: main` replaces main persona.
- `type: alter` creates a new alter persona:
  - Unique triggers enforced (no overlaps).
  - Avatar reference stored in `webhook_avatar_url` (production URL or non-production local path).

### `/persona remove`

- Removes a selected alter persona.
- Deletes the stored avatar file/reference when present.
- Does **not** automatically delete legacy persona webhooks.

### `/persona swap`

- Promotes an alter to main.
- Transfers triggers between `alter_triggers` and `tomori_configs.trigger_words`.
- Updates guild avatar and nickname.
- Stores the previous main avatar in `webhook_avatar_url`.
- Local alter avatars are loaded from the stored file path when present.

## Caching and Invalidation

### Persona cache

`getCachedAllPersonas()` loads and caches all personas for a server.

Invalidate cache after:
- Importing/removing/swapping personas.
- Updating triggers or avatars.

### Webhook cache

In-memory caches:
- `webhookCache` (shared channel webhook)
- `personaWebhookCache` (legacy per-persona webhook cache; retained for recovery / compatibility helpers)

**Cache behavior:**
- No TTL (persist until bot restart or manual invalidation)
- Token validation on cache hit (recreates if webhook was deleted)
- Auto-invalidation on webhook errors (codes 10015, 50027)
- Avatar mutation sends also use a per-target-channel mutation lock so concurrent sends cannot cross-contaminate webhook avatars.

## Limitations and Edge Cases

### General

- **Context refresh**: later personas do not see earlier persona replies (deferred).
- **Webhook username collision**: reply routing relies on unique persona nicknames.
- **DMs**: no webhook support; alters are not available in DMs.
- **Sticker rendering**: alter personas send sticker **URL previews** instead of actual stickers.

### Self-Reply Chains

- **Shared limit**: All personas share one depth counter per channel (not per-persona).
- **Chain blocks all**: When limit reached, ALL persona triggers are blocked (user can reset by sending a message).
- **Cascading triggers**: If A triggers B, C, D in one message, that's 1 depth increment (not 3).

### Webhooks (Local Development)

- **Legacy URL expiration (mitigated)**: lazy migration copies old HTTP(S) avatar references into local storage on first use.
- **Legacy webhook deletion (mitigated)**: auto-recovery scans guild for surviving legacy persona webhooks during migration.
- **Terminal case**: if all legacy recovery sources are gone and no local file exists, avatar is unrecoverable without re-import.
- **Webhook limit**: steady-state local mode now uses one shared webhook per channel, so normal alter traffic no longer burns one webhook slot per persona.

## Troubleshooting

### Alter doesn't respond

1. **Check trigger words:**
   - Confirm trigger words are unique and present in `alter_triggers`
   - Check if message contained the trigger or was a reply to alter webhook

2. **Check self-reply limit:**
   - Look for log: `Self-reply chain limit reached (X)`
   - Have a user send a message to reset the chain
   - Increase limit with `/config selfreply` if needed

3. **Check webhook permissions:**
   - Verify bot has `MANAGE_WEBHOOKS` permission in channel
   - Check if channel supports webhooks (not DM)

### Alter has wrong avatar or name

1. **Webhooks failing:**
   - Check permissions (`MANAGE_WEBHOOKS`)
   - Look for warning embed in channel (rate-limited)
   - Check logs for webhook errors

2. **Local development avatar issues:**
   - Check whether `webhook_avatar_url` now points to a local `data/avatars/...` path
   - If legacy HTTP(S) value is still present, next use should trigger lazy migration
   - If migration fails:
     - Look for log: `Attempting legacy webhook recovery for persona X`
     - Confirm at least one legacy `TomoriBot Persona {id}` webhook still exists somewhere in the guild
   - If no recovery source exists, re-import the persona avatar

3. **DM limitations:**
   - Webhooks not supported in DMs
   - Alters will use main persona appearance

### Self-reply chain issues

**Personas stop responding after several triggers:**
- Chain limit reached (default: 3)
- User message resets chain
- Check current limit: `/config selfreply`
- Increase limit (max 10) or disable (0)

**Personas triggering infinite loops:**
- Limit is too high or disabled (0)
- Reduce limit with `/config selfreply`
- Check persona personalities (may be too eager to mention each other)

## Test Checklist (Recommended)

### Basic Functionality

1. **Reply routing:** Reply to an alter's webhook message → same alter responds.
2. **Multi-trigger:** Trigger multiple alter keywords → all matching personas respond.
3. **Tool embeds:** Tool call as alter → embeds use alter webhook name/avatar.
4. **Stickers:** Sticker tool as alter → CDN URL sent via webhook.
5. **Reminders:** Reminder created by alter → alter delivers reminder; fallback to main if persona removed.

### Self-Reply Chains

6. **User bypass:** User triggers 4+ personas → all respond (bypasses limit).
7. **Chain depth:** Persona A → B → C → limit reached → D blocked.
8. **Multi-mention depth:** Persona A mentions B, C, D in one message → all respond, depth +1 only.
9. **Chain reset:** After chain limit reached, user message → chain resets, personas respond again.
10. **Limit configuration:** `/config selfreply limit:5` → new limit applies immediately.

### Webhook Robustness (Local Development)

11. **Local storage:** Import alter or set alter avatar → verify `webhook_avatar_url` stores a `data/avatars/...` path in non-production.
12. **Lazy migration:** Existing local persona with HTTP(S) `webhook_avatar_url` → first alter send migrates to a local path.
13. **Recovery path:** Break the legacy HTTP(S) URL but keep one legacy `TomoriBot Persona {id}` webhook → next send recovers avatar and stores a local path.
14. **Shared webhook identity:** Use the same alter in multiple channels/threads → messages still show the correct persona sender without creating new persona webhooks.
