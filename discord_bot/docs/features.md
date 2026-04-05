# Features

This file is a code-referenced map of the bot's major user-facing features and where each area lives in the codebase.

## Configuration And Admin UX

- Config panel and compact `/config` command tree: `discord_bot/cogs/config.py`
- Shared config/admin panel widgets: `discord_bot/utils/config_panel_ui.py`
- Native panel implementation helpers: `discord_bot/utils/native_config_panel.py`
- Auth/session checks for high-risk config actions: `discord_bot/utils/auth.py`
- Audit logging and persisted guild config state: `discord_bot/utils/db_handler.py`

## AI Replies And Persona Runtime

- Main AI orchestration and admin-action flows: `discord_bot/cogs/ai_brain.py`
- Guild-scoped AI key/model loading: `discord_bot/utils/guild_ai.py`
- Persona queue and response sequencing helpers: `discord_bot/utils/persona_queue.py`
- Streaming contracts and types: `discord_bot/utils/streaming/types.py`
- Persona management panel: `discord_bot/utils/persona_panel_ui.py`

## Tooling And Capability Flags

- Tool management slash surface: `discord_bot/cogs/tools_admin.py`
- Tool registry and filtering: `discord_bot/utils/tool_registry.py`
- Tool flag mapping: `discord_bot/utils/tool_flags.py`
- Tool availability gating: `discord_bot/tools/availability.py`
- Tool contracts: `discord_bot/tools/contracts.py`

## Search, Retrieval, And External Intelligence

- Web search behavior: `discord_bot/utils/web_search.py`
- Retrieval store and embeddings: `discord_bot/utils/rag_store.py`, `discord_bot/utils/rag_embeddings.py`
- Review capability synthesis: `discord_bot/utils/review_capabilities.py`

## Media And Vision

- Image generation flows: `discord_bot/cogs/imagegen.py`, `discord_bot/utils/image_generation.py`
- Vision/profile analysis: `discord_bot/cogs/vision.py`, `discord_bot/utils/profile_peek.py`
- GIF and reaction-style utility behavior: `discord_bot/cogs/utilities.py`

## Welcome, Autorole, And Social Flows

- Welcome and autorole runtime behavior: `discord_bot/cogs/social.py`
- Config panel entrypoints for welcome/autorole: `discord_bot/cogs/config.py`
- Persisted welcome/autorole settings: `discord_bot/utils/db_handler.py`

## Moderation And Safety

- URL safety configuration and panel flows: `discord_bot/cogs/config.py`
- Stored URL safety settings: `discord_bot/utils/db_handler.py`
- Mod-log routing and staff-role admin flows: `discord_bot/cogs/config.py`
- Automod and moderation-adjacent commands: `discord_bot/cogs/scheduler.py`, `discord_bot/cogs/utilities.py`

## Memory, Teaching, And Knowledge

- Teaching and knowledge storage flows: `discord_bot/cogs/teach.py`
- Memories and recall surfaces: `discord_bot/cogs/memories.py`
- Self-teaching config wiring: `discord_bot/cogs/config.py`, `discord_bot/utils/db_handler.py`

## Community Features

- Starboard: `discord_bot/cogs/starboard.py`
- Bump reminders and bump state: `discord_bot/cogs/scheduler.py`
- Avatar administration and server identity helpers: `discord_bot/cogs/admin.py`

## Operational And Support Docs

- Slash command inventory: `discord_bot/docs/slash-commands.md`
- Config usage guide: `discord_bot/docs/guide/config-panel.md`
- Settings reference: `discord_bot/docs/guide/settings-reference.md`
- Design and implementation plans: `docs/plans/`
