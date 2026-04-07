# TomoriBot vs Current Bot Feature Parity Report

Date: 2026-04-07

## Scope

This compares the current Python Discord bot in `discord_bot/` against the TypeScript TomoriBot worktree in `/mnt/c/Users/Hp/.codex/superpowers/worktrees/femboibot/codex/bot-time-awareness-tool/tomoribot/`.

The comparison focuses on user-facing behavior and admin/operator capabilities, not deployment/infra differences.

Primary references:

- Current bot: `discord_bot/docs/slash-commands.md`, `discord_bot/docs/features.md`, `discord_bot/cogs/*.py`, `discord_bot/utils/*.py`
- TomoriBot: `tomoribot/README.md`, `tomoribot/docs/systems/command-system.md`, `tomoribot/src/commands/**`, `tomoribot/docs/integrations/**`, `tomoribot/docs/ai/**`

## Executive Summary

- Core assistant parity is solid. We already cover the shared foundation: multi-persona chat, long-term memory, document/RAG teaching, tool calling, MCP-backed tools, image generation, image understanding, reminders, and welcome flows.
- TomoriBot is still ahead on "power-user platform" depth. The biggest missing areas are persona portability/generation, richer provider and model routing, SillyTavern preset support, voice I/O, Matrix bridging, quotas, and more granular server automation controls.
- Our bot is already ahead in Discord-native guild administration. We have stronger in-server management UX around config panels, tool governance, MCP approval/trust/quarantine, URL safety, automod, starboard, bump reminders, and community-focused profile/social commands.

## Parity Matrix

| Area | TomoriBot | Us | Notes |
| --- | --- | --- | --- |
| Core AI chat, mention/reply runtime, tool calling | Yes | Yes | Shared baseline exists in `tomoribot/README.md`, `tomoribot/src/events/messageCreate/tomoriChat.ts`, `discord_bot/cogs/ai_brain.py`, `discord_bot/tools/` |
| Multi-persona runtime | Strong | Moderate | We support persona manage/edit/delete; Tomori also has create/default/swap/import/export/generate in `tomoribot/src/commands/persona/` |
| Memory and teaching | Strong | Strong | Both support server/personal memory and document teaching; Tomori adds `teach/history`, `teach/personaprompt`, `forget/*`, and `data/import/export` |
| Tool and MCP support | Strong | Strong | Both have MCP/tool registries; our admin surface is much deeper via `/tools ...` in `discord_bot/cogs/tools_admin.py` |
| Provider and model configuration | Very strong | Moderate | We support Gemini, OpenRouter, custom endpoints, and image provider config; Tomori adds provider switching, embedding/vision/fallback model config, parameter tuning, API key rotation, and optional provider keys |
| Image generation and vision | Very strong | Strong | Both support image generation and image understanding; Tomori also documents NovelAI-specific flows and broader multimodal generation |
| Video understanding | Yes | Yes | Tomori supports multimodal chat and cost estimation for videos; we support auto video analysis in `discord_bot/cogs/ai_brain.py` |
| Voice features | Yes | No | Tomori has ElevenLabs STT/TTS and native Discord voice-message support in `docs/integrations/voice-system.md` |
| Matrix bridge | Yes | No | Tomori has `server/matrix/*` commands and relay runtime |
| Server routing and automation | Very strong | Moderate | Tomori adds trigger word management, autotrigger thresholds/channels, RP channels, quotas, whitelist role/channel commands, member permissions, thought logs |
| Guild admin/community UX | Moderate | Very strong | We lead on config panel UX, modlog, staff roles, autorole management, URL safety, automod, starboard, bump reminders, and admin auth/password flows |

## Shared Strengths

These are areas where the current bot is already in the same product family as TomoriBot, not a lightweight subset:

- Multi-persona AI chat and persona presentation
  - Current: `discord_bot/cogs/ai_brain.py`, `discord_bot/cogs/persona.py`, `discord_bot/utils/persona_panel_ui.py`
  - Tomori: `tomoribot/src/events/messageCreate/tomoriChat.ts`, `tomoribot/docs/ai/multi-persona.md`
- Long-term memory and document-backed knowledge
  - Current: `discord_bot/cogs/memories.py`, `discord_bot/cogs/teach.py`, `discord_bot/utils/rag_store.py`
  - Tomori: `tomoribot/src/commands/teach/memory/*`, `tomoribot/src/commands/teach/document.ts`, `tomoribot/docs/ai/rag.md`
- Tool calling, web search, and MCP integration
  - Current: `discord_bot/cogs/tools_admin.py`, `discord_bot/utils/tool_registry.py`, `discord_bot/tools/mcp/`
  - Tomori: `tomoribot/src/tools/toolRegistry.ts`, `tomoribot/src/commands/config/mcp/*`, `tomoribot/src/tools/mcpServers/`
- Image generation and image understanding
  - Current: `discord_bot/cogs/imagegen.py`, `discord_bot/cogs/vision.py`
  - Tomori: `tomoribot/src/commands/generate`, `tomoribot/src/utils/image/*`
- Welcome flows
  - Current: `/welcome manage` in `discord_bot/cogs/config.py`
  - Tomori: `/server welcomechannel` in `tomoribot/src/commands/server/welcomechannel.ts`

## TomoriBot Features We Do Not Yet Match

### 1. Persona Portability and Advanced Persona Ops

Tomori has a much larger persona lifecycle:

- `persona/create`
- `persona/default`
- `persona/swap`
- `persona/import`
- `persona/export`
- `persona/generate`

Evidence: `tomoribot/src/commands/persona/*.ts`

Current coverage is narrower:

- `persona manage`
- `persona edit`
- `persona delete`

Evidence: `discord_bot/cogs/persona.py`, `discord_bot/docs/slash-commands.md`

This is one of the biggest parity gaps because Tomori treats personas as portable/shareable assets, while we currently treat them as in-server managed entries.

### 2. SillyTavern Preset and Card Ecosystem

Tomori has explicit SillyTavern integration:

- preset import/upload and node toggling
- preset-driven context assembly
- persona card import/generation flows

Evidence:

- `tomoribot/docs/integrations/sillytavern-preset-system.md`
- `tomoribot/docs/integrations/sillytavern-card-support.md`
- `tomoribot/src/utils/text/stPresetEngine.ts`
- `tomoribot/src/utils/text/presetContextBuilder.ts`

We do not appear to have an equivalent preset/card system in `discord_bot/`.

### 3. Voice Input/Output

Tomori supports:

- user audio transcription
- AI-generated voice messages
- per-persona ElevenLabs voice assignment
- native Discord voice-message metadata handling

Evidence:

- `tomoribot/docs/integrations/voice-system.md`
- `tomoribot/src/commands/config/voice/elevenlabs.ts`
- `tomoribot/src/utils/audio/*`

We do not currently expose voice-message features or voice provider config.

### 4. Matrix Bridge

Tomori supports Matrix relay and bridge-aware behavior:

- `server/matrix/link`
- `server/matrix/unlink`
- bridge runtime in `src/events/messageCreate/matrixRelay.ts`

We do not currently expose Matrix bridging.

### 5. Richer Provider and Model Routing

Our provider story is functional but simpler:

- Gemini
- OpenRouter
- custom endpoint
- image provider/model fields

Evidence:

- `discord_bot/guild.env.example`
- `discord_bot/cogs/config.py`
- `discord_bot/utils/guild_ai.py`

Tomori goes materially further:

- provider switching/removal
- text, image, vision, embedding, and fallback model commands
- direct parameter tuning (`temperature`, `top_p`, `top_k`, `presence_penalty`, etc.)
- API key set/delete/rotation flows
- model compatibility validation and "other-model" flows
- optional provider keys for NovelAI, Google, ElevenLabs

Evidence:

- `tomoribot/src/commands/config/model/*`
- `tomoribot/src/commands/config/apikey/*`
- `tomoribot/src/commands/config/params/*`
- `tomoribot/src/commands/config/provider/*`
- `tomoribot/src/commands/optionalkey/*`

### 6. Server Automation and Policy Breadth

Tomori has more granular server runtime controls:

- trigger word add/delete
- autotrigger channel and threshold control
- RP channels
- channel/role whitelist commands
- member permission controls
- text/image quota controls
- thought log controls

Evidence: `tomoribot/src/commands/server/*`

We do have AI whitelist/auto-channel routing in the config panel, but not the same breadth of dedicated slash-command control.

### 7. Data Lifecycle Commands

Tomori has explicit import/export/delete flows for stored bot data:

- `data/export`
- `data/import`
- `data/delete`
- extensive `forget/*` commands for memory, dialogue, history, reminders, and documents

Evidence:

- `tomoribot/src/commands/data/*`
- `tomoribot/src/commands/forget/*`

Our bot supports selected memory deletion and reset flows, but not the same full data portability and cleanup surface.

### 8. Tool Utility Commands for Power Users

Tomori has several operator/user utility commands we do not currently mirror:

- `tool/comment`
- `tool/compact`
- `tool/delete/turn`
- `tool/estimate/cost`

Evidence: `tomoribot/src/commands/tool/*`

Our tooling emphasis is more on governance and MCP management than on chat/session utility helpers.

## Areas Where We Are Ahead

### 1. Discord-Native Tool Governance

Our `/tools` surface is significantly richer for managed deployments:

- policy by category/tool
- quarantine status/clear
- raw capture debug toggles
- MCP register/discover/list/approve/trust/enable/health flows
- context refresh and recency clearing

Evidence:

- `discord_bot/cogs/tools_admin.py`
- `discord_bot/tests/test_tools_admin_surface_consolidation.py`

Tomori has MCP support, but its exposed command/admin surface is leaner.

### 2. Guild Admin UX and Safer Self-Serve Config

We have stronger in-Discord administration UX around:

- native config panel
- auth-gated sensitive actions
- config password set/change/reset
- env example upload flow
- URL safety management
- modlog management
- staff-role management
- consolidated welcome and autorole management

Evidence:

- `discord_bot/cogs/config.py`
- `discord_bot/utils/native_config_panel.py`
- `discord_bot/utils/auth.py`
- `discord_bot/docs/guide/config-panel.md`

Tomori exposes more knobs overall, but our configuration experience is currently more cohesive for guild admins.

### 3. Community and Moderation Features

We have several community features that do not show up as first-class Tomori capabilities:

- automod rules
- starboard
- bump reminders
- affection system
- profile/alias/birthday memory helpers

Evidence:

- `discord_bot/cogs/automod.py`
- `discord_bot/cogs/starboard.py`
- `discord_bot/cogs/scheduler.py`
- `discord_bot/cogs/affection.py`
- `discord_bot/cogs/memories.py`

Tomori includes reward commands and welcome support, but it is less focused on this "server utility/community bot" layer.

## Recommended Backlog Order

If the goal is to close the most visible Tomori gaps first, the highest-value order is:

1. Persona portability
   - Add create/default/swap/import/export/generate parity before smaller admin gaps.
2. Provider and model depth
   - Add richer provider switching, vision/embedding model selection, parameter tuning, and optional provider-key flows.
3. SillyTavern compatibility
   - Import/export and preset-driven context would unlock one of Tomori's clearest differentiators.
4. Voice pipeline
   - STT/TTS is a major visible gap if we want "Tomori-class" multimodality.
5. Server routing controls
   - Trigger/autotrigger/RP/quota/member-permission surfaces would close the admin/runtime gap.
6. Data portability
   - Import/export/delete and more complete forget flows improve trust and operability.

## Bottom Line

We are already in the same product category as TomoriBot on the core assistant experience.

We are not yet at feature parity on Tomori's advanced persona ecosystem, provider/model stack, preset/card compatibility, voice features, Matrix bridge, and server runtime controls.

At the same time, we are already ahead on Discord-native guild administration, tool governance, and community-management features.
