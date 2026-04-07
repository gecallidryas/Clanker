# Natural-Language Admin Control Design

**Date:** 2026-04-07

**Goal:** Replace the current fragmented natural-language admin/config behavior with one unified control plane that can reliably manage adjacent existing server settings through conversational requests, including starboard, welcome messages, automod keyword rules, spam timeout settings, URL safety, modlog, autorole, staff-role management, and existing moderation/server-structure actions.

## Summary

The current bot has three overlapping admin-control paths:

- prompt-only `admin_action` instructions inside `discord_bot/cogs/ai_brain.py`
- special-case fast paths in `discord_bot/cogs/ai_brain.py` for starboard, channels, and roles
- standalone slash/panel/config handlers in `discord_bot/cogs/config.py`, `discord_bot/cogs/starboard.py`, `discord_bot/cogs/automod.py`, and `discord_bot/cogs/social.py`

That split causes brittle behavior. The bot can sometimes perform admin setup through natural language, but coverage is incomplete and the behavior is not governed by one intent parser, one follow-up mechanism, or one executor layer. The design should consolidate those paths so the bot can consistently recognize, clarify, execute, and explain admin actions without relying on the model to remember all of the capabilities from prompt text alone.

## Desired UX

Qualified users should be able to use:

- direct mentions
- replies to the bot
- plain messages that already trigger the bot by name or alias

Examples:

- "set up starboard in #highlights with any emoji at 4 reactions"
- "make the welcome message say welcome {member} to {guild}"
- "turn off DM welcomes"
- "timeout spammers after 6 messages in 10 seconds for 15 minutes"
- "make url safety delete blocked links"
- "set the mod log to this channel"
- "set the autorole to @Members"
- "make @Moderators bot staff level 1"
- "ban @user for raids"

Behavior rules:

- underspecified requests ask a short follow-up question instead of guessing
- channel/category deletion requires confirmation
- bans and other moderation actions do not require an explicit confirmation step
- requests should execute through the same permission and audit path regardless of whether they came from prompt parsing or a deterministic fallback

## Architecture

### One Admin Control Plane

Add a dedicated natural-language admin layer that owns:

- intent detection
- slot extraction
- pending follow-up state
- confirmation policy
- execution dispatch
- user-visible replies

This replaces the current pattern of adding feature-specific `_maybe_handle_*` paths to `AIBrain`.

### Typed Intents

Represent supported admin operations as typed intents instead of raw ad hoc prompt payloads. At minimum:

- `starboard.configure`
- `starboard.toggle`
- `starboard.ignore_channel`
- `starboard.unignore_channel`
- `welcome.configure`
- `welcome.toggle`
- `welcome.dm.configure`
- `welcome.dm.toggle`
- `automod.keyword.add`
- `automod.keyword.remove`
- `automod.spam.configure`
- `url_safety.configure`
- `modlog.set`
- `modlog.clear`
- `autorole.set`
- `autorole.clear`
- `staff.add`
- `staff.remove`
- `staff.clear`
- existing `manage_role`, `manage_channel`, and moderation actions

Each intent should declare:

- required slots
- optional slots
- follow-up question builders for missing required slots
- whether confirmation is required
- the executor to call

### Parsing Strategy

Use deterministic parsing first for adjacent existing settings instead of relying entirely on model-generated `admin_action` JSON. The parser should:

- recognize synonyms and natural phrasing
- resolve mentions, channel references, roles, and "this channel"/"here"
- support common numeric phrases like "at least 4", "more than 3", "6 messages in 10 seconds"
- normalize booleans such as enable/disable, on/off, clear/remove

Prompt-generated `admin_action` is non-authoritative for the supported surface and must not execute supported mutations. Supported admin mutations must come only from the typed parser and unified executor path.

### Pending Follow-Ups

Use a unified pending admin request store instead of feature-specific pending behavior. Each pending item should keep:

- intent name
- normalized slot values collected so far
- missing required slots
- whether confirmation is pending
- creation time / expiry

When the next qualifying message from the same user in the same channel arrives, the bot should try to complete the missing slots and either:

- ask the next follow-up question
- ask for confirmation if required
- execute immediately when ready

### Execution Layer

Expand `discord_bot/utils/admin_actions.py` into the main executor module for admin/config intents, or extract a dedicated executor module and keep `admin_actions.py` as a compatibility wrapper. The executor layer should own:

- permissions
- guild/channel/role resolution
- updates to `db_handler`
- audit logging
- consistent success and error messages

The executor layer should reuse existing storage APIs in `discord_bot/utils/db_handler.py` rather than duplicate write logic from panel code.

## Scope

The first unified version should cover adjacent existing server settings already present in the repo:

- starboard setup, toggle, ignore, unignore
- welcome channel/message and DM welcome settings
- automod keyword add/remove
- automod spam timeout configuration
- URL safety mode/allowlist/blocklist
- modlog set/clear
- autorole set/clear
- staff role add/remove/clear
- existing moderation and structure management actions

It should not broaden into unrelated new admin domains until this control plane is stable.

## Authoritative Supported Intent Surface

The supported admin mutation surface is authoritative only when it flows through the typed admin NLP pipeline:

- `interpret_admin_request`
- `resume_admin_request`
- `execute_admin_intent`

The supported mutation intents are:

- `channel.create_text`
- `channel.create_voice`
- `channel.create_category`
- `channel.delete`
- `role.create`
- `role.delete`
- `role.assign`
- `role.remove`
- `starboard.configure`
- `starboard.toggle`
- `starboard.ignore_channel`
- `starboard.unignore_channel`
- `welcome.configure`
- `welcome.toggle`
- `welcome.message.clear`
- `welcome.dm.configure`
- `welcome.dm.toggle`
- `welcome.dm.message.clear`
- `automod.keyword.add`
- `automod.keyword.remove`
- `automod.spam.configure`
- `url_safety.configure`
- `modlog.set`
- `modlog.clear`
- `autorole.set`
- `autorole.clear`
- `staff.add`
- `staff.remove`
- `staff.clear`
- `moderation.ban`
- `moderation.unban`
- `moderation.kick`
- `moderation.timeout`

Equivalent phrasings such as `set modlog`, `set mod log`, `create starboard`, and `send posts to starboard` must resolve to the same typed intent path.

## Not Supported As Mutation

Read-only/admin status questions are intentionally not mutation intents and must not create pending mutation state. Examples:

- `what is the welcome message in #logs?`
- `show me the modlog channel`
- `what is the url safety action?`
- `what channels can starboard use?`

These requests may be answered elsewhere, but not by starting a mutation workflow.

## Admin-Like But Fail Closed

Some messages are clearly admin/config requests but are unsupported or too underspecified for safe execution. These must produce a deterministic help or rephrase reply and must not fall through into the general AI mutation path. Examples:

- unsupported admin domains outside the list above
- supported domains with no actionable imperative, such as read-only/admin status questions
- supported domains missing required details beyond safe slot recovery
- admin-like phrasing that the typed parser cannot map to a supported intent

Prompt-driven `admin_action` JSON is non-authoritative for the supported surface and must not execute these supported mutations through alternate parsing rules.

## Safety Model

- Manage Guild or administrator remains the baseline for config actions unless a stricter check already exists
- bot staff roles continue to govern agentic moderation/structure permissions where that model already exists
- channel/category deletion requires explicit confirmation
- role creation, bans, kicks, timeouts, and non-destructive config updates execute immediately once required slots are present
- missing information triggers a short follow-up instead of filling aggressive defaults

## Testing Strategy

Add a dedicated natural-language admin test surface that covers:

- intent detection across all supported adjacent settings
- slot extraction for natural phrasing and Discord references
- missing-slot follow-up behavior
- delete confirmation behavior for channels/categories only
- unified executor success/failure behavior
- end-to-end `AIBrain` routing for trigger messages, follow-ups, and execution

The tests should prevent future regressions where a setting exists in slash/panel UI but is silently missing from the natural-language admin control plane.
