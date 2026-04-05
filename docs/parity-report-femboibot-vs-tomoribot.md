# FemboiBot vs TomoriBot Parity Report

Date: 2026-04-04

## Scope

This report compares the current `femboibot` workspace against the vendored `tomoribot/` reference subtree in the same repository. It is based on repository structure, runtime entry points, command surfaces, and project documentation present in this workspace.

## Executive Summary

FemboiBot has reached meaningful parity on the core Discord AI bot loop: message-triggered chat, streaming replies, custom personas, reminders, moderation/configuration, memory hooks, image understanding, and a real tool/MCP execution layer. It is no longer a minimal fork.

It is still materially behind TomoriBot as a product platform. The biggest gaps are provider breadth, command surface area, voice, cross-platform integrations, data portability, and deployment/documentation maturity. TomoriBot is still the wider system.

FemboiBot is ahead in one notable area: tool governance. Its Python-side tool system includes policy resolution, quarantine, admin approval, debug capture, and guild/global MCP control-plane workflows that are more operationally explicit than TomoriBot's current tool admin surface.

## Size and Surface Area Snapshot

- FemboiBot runtime is centered around `discord_bot/` with `18` cog files.
- TomoriBot exposes `150` command files under `tomoribot/src/commands/`.
- FemboiBot root README is intentionally sanitized and narrow.
- TomoriBot includes extensive architecture, provider, tool, integration, and deployment docs under `tomoribot/docs/`.

This does not automatically mean better quality, but it does show that TomoriBot still has a much broader shipped surface.

## Capability Matrix

| Area | FemboiBot | TomoriBot | Parity Verdict |
|---|---|---|---|
| Core Discord bot runtime | Dynamic cog loading, slash sync, guild init, runtime guard, streamed chat pipeline | Event-driven command/event runtime with provider abstraction | Partial parity |
| Core AI chat | Mention/reply/trigger-based chat, streaming, image/video analysis in main chat loop | Mature chat pipeline with provider-specific adapters | Partial parity |
| Provider ecosystem | Gemini, OpenRouter, custom OpenAI-compatible endpoint | Google, OpenRouter, NovelAI, custom, DeepSeek, NVIDIA, Z.ai, Z.ai Coding | Behind |
| Tool execution | Prompt-emulated tool calls plus native execution envelope path | Central built-in + MCP + REST tool registry | Partial parity |
| Tool governance | Category policy, per-tool policy, quarantine, debug capture, guild/global MCP registration and approval | Simpler centralized registry plus MCP config and runtime filtering | FemboiBot ahead operationally |
| MCP support | Guild/global registration, discovery, approval, trust, health, enablement | MCP servers and `/config mcp` management | Near parity, FemboiBot stronger in admin controls |
| Memory and RAG | Personal/server memory, recency summaries, document upload, optional local RAG with Postgres | Long-term memory, short-term memory, document memory, richer surrounding systems | Partial parity |
| Persona system | Built-in modes, custom persona create/edit/delete/list/preview/manage, multi-persona queueing, webhook identity helpers | Main + alter personas, import/export/generate/swap, multi-trigger orchestration, persona-specific workflows | Partial parity |
| Vision and image support | Image description, video description, image generation cog, GIF helpers | Full multimodal input/output and richer generation/provider coverage | Partial parity |
| Voice | No repo-grounded voice subsystem found | Full STT/TTS pipeline with ElevenLabs and native voice-message send path | Missing |
| Cross-platform bridge | No repo-grounded external chat bridge found | Built-in Matrix bridge | Missing |
| Admin/config UX | Large Discord-native config surface including auth, model, feature toggles, AI gating, staff/modlog/manage, welcome, tool admin | Very broad slash-command config surface spread across many categories | Partial parity, still smaller |
| Data portability | No comparable data import/export workflow found | Data export/import commands and migration scripts | Missing |
| Legal/help/support/product docs | Minimal root docs plus feature plans | Help, legal, support, donate, onboarding, contributor docs | Missing |
| Deployment and infra | `deploy/` exists, but repo docs are limited | Docker, monitoring, CI, Terraform, production docs | Behind |

## Areas Where FemboiBot Is Already Strong

### 1. Tool policy and MCP governance

FemboiBot's strongest differentiator is the new tool control plane:

- Tool contracts, descriptors, availability, validation, and execution flow live under `discord_bot/tools/`.
- Policy resolution exists in `discord_bot/tools/policy_engine.py`.
- Quarantine logic exists in `discord_bot/tools/quarantine.py`.
- MCP registration and discovery control plane exists in `discord_bot/tools/mcp/control_plane.py`.
- Discord admin workflows for status, inspection, policy, debug capture, quarantine, and MCP approval live in `discord_bot/cogs/tools_admin.py`.

TomoriBot has a solid centralized tool system, but its user-facing admin controls are narrower by comparison. On operational governance, FemboiBot is not behind.

### 2. Discord-native server management

FemboiBot already has substantial Discord admin coverage:

- `discord_bot/cogs/config.py`
- `discord_bot/cogs/admin.py`
- `discord_bot/cogs/automod.py`
- `discord_bot/cogs/starboard.py`
- `discord_bot/cogs/scheduler.py`

This is enough to cover many day-to-day server-operator needs without leaving Discord.

### 3. Core chat pipeline is no longer lightweight

`discord_bot/cogs/ai_brain.py` is large and featureful. Repo evidence shows:

- streaming orchestration
- prompt/tool transport layers
- memory injection
- reply cooldowns
- image/video attachment handling
- admin action handling
- persona queueing
- webhook identity support

That places FemboiBot well beyond "basic Gemini chatbot" territory.

## Major Gaps vs TomoriBot

### 1. Provider breadth and provider architecture

TomoriBot has a true provider ecosystem documented in `tomoribot/docs/ai/providers.md` and implemented under `tomoribot/src/providers/`.

FemboiBot currently routes through:

- Gemini
- OpenRouter
- custom OpenAI-compatible endpoint

Repo evidence: `discord_bot/utils/guild_ai.py`

Missing relative to TomoriBot:

- NovelAI
- DeepSeek
- NVIDIA
- Z.ai / Z.ai Coding
- provider-owned feature capability system
- wider model inventory and provider-specific command surface

This is the single largest architectural parity gap.

### 2. Voice system

TomoriBot has a full documented voice stack in `tomoribot/docs/integrations/voice-system.md`, with implementation under:

- `tomoribot/src/utils/audio/`
- `tomoribot/src/tools/functionCalls/generateVoiceMessageTool.ts`
- `tomoribot/src/commands/config/voice/elevenlabs.ts`

No comparable FemboiBot subsystem is present in the inspected Python tree. This is a clear missing feature area.

### 3. Matrix bridge and non-Discord reach

TomoriBot ships a Matrix bridge documented in `tomoribot/docs/integrations/matrix-bridge.md` and implemented under:

- `tomoribot/src/utils/matrix/`
- `tomoribot/src/utils/bridge/`
- `tomoribot/src/commands/server/matrix/`

No equivalent bridge layer appears in FemboiBot. Platform parity is therefore not close.

### 4. Persona workflow depth

FemboiBot has strong custom persona management in `discord_bot/cogs/persona.py`, plus multi-persona runtime hooks in `discord_bot/cogs/ai_brain.py`.

TomoriBot still leads on persona product depth because it includes:

- import/export
- persona generation
- swap/promote flows
- dedicated main-vs-alter model
- richer documented multi-persona lifecycle

Repo evidence:

- `tomoribot/src/commands/persona/`
- `tomoribot/docs/ai/multi-persona.md`

Verdict: FemboiBot is in the same category here, but not yet at reference depth.

### 5. Command breadth and product polish

TomoriBot's command tree spans:

- bot
- config
- data
- forget
- generate
- help
- legal
- novelai
- optionalkey
- persona
- personal
- reward
- server
- stpreset
- support
- teach
- tool

Repo evidence: `tomoribot/src/commands/`

FemboiBot covers many of the important server/admin features, but it does not yet match:

- help/legal/support flows
- data import/export
- dedicated personal settings surface
- quota/whitelist/rpchannel/matrix families
- NovelAI-specific configuration families
- polished product/support affordances

### 6. Deployment, ops, and documentation maturity

TomoriBot ships:

- Dockerfiles and Compose
- monitoring compose
- GitHub workflows
- Terraform
- detailed subsystem docs

Repo evidence:

- `tomoribot/Dockerfile`
- `tomoribot/docker-compose.yaml`
- `tomoribot/docker-compose.monitor.yaml`
- `tomoribot/.github/workflows/`
- `tomoribot/terraform/`
- `tomoribot/docs/`

FemboiBot has a `deploy/` directory, but the current repository does not present the same production-readiness surface or operator documentation depth.

## Feature-by-Feature Parity Assessment

### Near parity or close enough to build on

- Core Discord chat and streamed replies
- Server config/admin flows
- Reminders and scheduling
- Memory teaching and document upload
- Image understanding
- Tool/MCP foundation
- Custom persona CRUD

### Partial parity with meaningful remaining work

- Multi-persona orchestration
- RAG and memory retrieval
- Image generation ecosystem
- Model/provider configuration
- operator experience

### Clearly missing or materially behind

- voice
- Matrix bridge
- wide provider family support
- data portability
- legal/help/support product surface
- infra/documentation maturity

## Recommended Priority Order

### Priority 1: Close the architectural gaps that unlock other parity work

1. Expand provider abstraction beyond Gemini/OpenRouter/custom.
2. Normalize provider capability flags so features stop hardcoding provider assumptions.
3. Keep the existing tool/MCP control plane as a first-class differentiator.

### Priority 2: Finish product-depth parity on core Discord use cases

1. Extend persona workflows with import/export/generation/swap equivalents.
2. Close missing personal/data flows.
3. Consolidate command discoverability and user help inside Discord.

### Priority 3: Decide whether full TomoriBot parity is actually the goal

If the target is "TomoriBot but Python," then voice and Matrix are unavoidable roadmap items.

If the target is "best-in-class Discord-only fork," then the highest-value path is:

1. provider breadth
2. persona depth
3. admin/operator UX
4. tool governance polish

That path would still leave FemboiBot intentionally non-parity on cross-platform features, but stronger where it matters most for a Discord-native deployment.

## Bottom Line

FemboiBot is best described as a partial-parity fork with one standout subsystem of its own: tool governance.

It already matches TomoriBot in several core Discord bot capabilities and has enough architecture to keep converging. But TomoriBot still leads clearly in provider breadth, platform integrations, command/product surface, and operational maturity.

If parity work continues, the most leverage comes from closing the provider and persona-product gaps first, not from chasing Matrix or voice immediately unless cross-platform parity is an explicit requirement.
