# Feature Parity Report: femboibot vs femboibot-sanitized-with-holy-water vs TomoriBot

Updated: 2026-04-02

This report compares the current root `femboibot` repository against:

- `femboibot-sanitized-with-holy-water`, the stripped deployment snapshot in this workspace
- `tomoribot`, the TypeScript reference bot bundled alongside this repo

The goal is to separate three different questions:

1. How close is the sanitized copy to the current root runtime?
2. How close is the current root runtime to TomoriBot's feature set?
3. Which product still leads in each area?

## Executive Summary

- The current root `femboibot` has moved far beyond the older parity report. It now includes web search, image generation, YouTube tooling, pinning, profile peek, RAG, i18n, richer tool gating, and a broader admin/config surface.
- `femboibot-sanitized-with-holy-water` is not a feature-equivalent twin anymore. A source-only comparison found 66 root-side files missing from the sanitized snapshot and no sanitized-only runtime files in return. The missing areas are concentrated in the newer tool runtime, streaming stack, native admin/persona panels, and related tests.
- Against TomoriBot, the current root bot has reached parity on many practical AI-assistant features, but TomoriBot still leads in provider breadth, voice, Matrix bridging, SillyTavern-oriented persona workflows, and production infrastructure.
- The current root bot still leads TomoriBot in community-management features such as affection/mood, automod, starboard, birthdays, aliases, guild auth, and AI-assisted welcome/autorole flows.

## Source Basis

- Root inventory: `docs/FEATURES.md`
- Sanitized intent and scope: `femboibot-sanitized-with-holy-water/README.md`
- TomoriBot capability references:
  - `tomoribot/README.md`
  - `tomoribot/docs/systems/tool-system.md`
  - `tomoribot/docs/ai/providers.md`
  - `tomoribot/docs/ai/rag.md`
  - `tomoribot/docs/ai/multi-persona.md`
  - `tomoribot/docs/integrations/voice-system.md`
  - `tomoribot/docs/integrations/matrix-bridge.md`

## High-Level Scorecard

| Area | femboibot (root) | femboibot-sanitized-with-holy-water | TomoriBot | Current leader |
| --- | --- | --- | --- | --- |
| Core AI chat | Full | Full | Full | Tie |
| Tool calling and web intelligence | Full | Partial | Full | Root/Tomori tie, Tomori broader |
| Memory and RAG | Full | Full | Full | Tie, different strengths |
| Persona system | Full | Full | Full | Tie, Tomori broader multi-persona orchestration |
| Multimodal input | Full | Full | Full | Tie |
| Multimodal output | Partial | Partial | Full | TomoriBot |
| Provider breadth | Partial | Partial | Full | TomoriBot |
| Moderation and community management | Full | Full | Partial | femboibot |
| Native admin UX | Full | Partial | Full | Root/Tomori tie, different focus |
| Deployment and ops | Partial | Partial | Full | TomoriBot |

## Root vs Sanitized Snapshot

The sanitized project is still a useful runnable package, but it is now a lagging subset of the root repo rather than a parity clone.

### What still matches

- Core Discord runtime under `discord_bot/`
- Existing cogs for AI chat, memories, persona, reminders, automod, starboard, image generation, teach, utilities, and vision
- Tests, deploy scripts, prompts, locales, and assets required for a basic deployment
- The older tooling path in `discord_bot/utils/` for web search, image generation, pinning, profile peek, RAG helpers, and i18n

### What is missing from the sanitized copy

The root repo has 66 source files that are not present in the sanitized snapshot. The gaps are concentrated in four areas:

| Missing area in sanitized copy | Root evidence |
| --- | --- |
| Tool runtime v2 and MCP control plane | `discord_bot/tools/*` |
| Streaming response pipeline | `discord_bot/utils/streaming/*` |
| Discord-native admin/config/persona panels | `discord_bot/utils/admin_panel_*`, `config_panel_ui.py`, `persona_panel_ui.py`, `native_config_panel.py`, `admin_views.py` |
| Newer coverage for tools, streaming, panels, and memory redesign | `tests/test_tool_*`, `tests/test_stream_*`, `tests/test_admin_panel_*`, `tests/test_memory_redesign.py`, `tests/test_persona_panel.py` |

### Practical interpretation

- If the sanitized folder is meant to be a clean deployment artifact, it still works as a compact runtime package.
- If it is meant to represent the current product at feature parity, it no longer does.
- The root repo should be treated as the canonical feature surface.

## Root femboibot vs TomoriBot

### Areas where parity is now effectively reached

| Capability | femboibot (root) | TomoriBot | Notes |
| --- | --- | --- | --- |
| Mention and trigger-based AI chat | Yes | Yes | Both support configurable conversational triggers |
| Tool calling | Yes | Yes | Root now has a gated tool pipeline; Tomori has a more mature class-based registry plus MCP and REST tooling |
| Web search and URL fetch | Yes | Yes | Root exposes DuckDuckGo, Brave, and URL fetch; Tomori exposes Brave, DuckDuckGo, and fetch through unified tooling |
| Image analysis | Yes | Yes | Both support multimodal vision flows |
| Image generation | Yes | Yes | Root supports Replicate/OpenRouter image generation; Tomori also supports provider-native image generation |
| Reminders/tasks | Yes | Yes | Both provide AI or command-driven reminder workflows |
| YouTube processing | Yes | Yes | Present in both stacks |
| Message pinning | Yes | Yes | Present in both stacks |
| Profile/avatar peek | Yes | Yes | Present in both stacks |
| RAG document memory | Yes | Yes | Both support document upload plus vector retrieval when configured |
| Localization | Yes | Yes | Root ships English/Japanese JSON locales; Tomori has a broader typed locale system |

### Areas where femboibot still leads

| Capability | femboibot (root) | TomoriBot | Why root leads |
| --- | --- | --- | --- |
| Affection and mood | Full | None | Root has explicit relationship state, decay, sentiment hooks, and mode-specific traits |
| Starboard | Full | None | Root has configurable emoji triggers, thresholds, ignores, and delete handling |
| Automod and spam protection | Full | Partial | Root has keyword actions, timeout/kick/ban flows, spam thresholds, mod log integration |
| Birthday and alias memory | Full | None | Root tracks birthdays, aliases, and nickname resolution |
| Guild auth and high-risk config gating | Full | Partial | Root has password/auth-session based admin flows plus audit-focused config surfaces |
| Welcome and autorole | Full | Partial | Root has AI welcome flows, DM welcome support, and autorole configuration |

### Areas where TomoriBot still leads

| Capability | femboibot (root) | TomoriBot | Why Tomori leads |
| --- | --- | --- | --- |
| Provider breadth | Partial | Full | Tomori supports Google, OpenRouter, NovelAI, DeepSeek, Nvidia, Z.ai, Z.ai Coding, and custom OpenAI-compatible families |
| Voice pipeline | None | Full | Tomori documents end-to-end ElevenLabs STT/TTS plus native Discord voice message output |
| Matrix bridge | None | Full | Tomori ships a built-in Matrix appservice bridge |
| Persona orchestration depth | Partial | Full | Root has built-in modes plus custom personas; Tomori supports one main persona plus multiple alters with shared orchestration |
| SillyTavern-style workflows | Partial | Full | Tomori supports character-card import and preset-driven persona workflows |
| Infrastructure maturity | Partial | Full | Tomori ships Docker Compose, Terraform, and Grafana-oriented deployment support |

### Nuanced areas

| Area | femboibot (root) | TomoriBot | Assessment |
| --- | --- | --- | --- |
| Memory model | User facts, aliases, birthdays, server memories, teach flows, optional RAG | Short-term memory, long-term memory, teach flows, optional/production RAG | Tie overall; root is more social/personal, Tomori is more agent-memory oriented |
| Admin UX | Rich slash config, tool status, quick toggle UI, newer native admin panel work | Large slash-command surface with interactive configuration | Different strengths rather than a clear winner |
| Tooling architecture | Newer Python tool runtime plus legacy utils path | More mature unified registry and provider adapter model | Tomori still cleaner architecturally |

## Recommended Conclusions

### If the goal is sanitized parity

- Sync the missing 66 source files from the root repo into `femboibot-sanitized-with-holy-water`.
- At minimum, bring over:
  - `discord_bot/tools/`
  - `discord_bot/utils/streaming/`
  - native admin/persona/config panel helpers
  - the newer tests that cover those systems

### If the goal is TomoriBot parity

The highest-value remaining gaps are:

1. Provider expansion beyond Gemini/OpenRouter/custom endpoint.
2. Voice input/output support.
3. Bridge/integration features such as Matrix.
4. Persona orchestration features closer to Tomori's main-plus-alters model.
5. More production-ready container and infrastructure support.

### If the goal is product differentiation

Keep leaning into the areas where femboibot is already stronger:

- affection and mood
- moderation and starboard
- guild-admin safety/auth controls
- social memory such as birthdays, aliases, and relationship context

## Bottom Line

The old parity report understated the current root `femboibot`. The root repo is now much closer to TomoriBot on day-to-day assistant features than the previous report suggested. The bigger immediate parity problem is no longer `femboibot` versus TomoriBot; it is the feature drift between the current root repo and `femboibot-sanitized-with-holy-water`.
