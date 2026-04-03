# 8. AI Provider System

TomoriBot uses a provider abstraction so chat logic stays provider-agnostic.

For the step-by-step contributor workflow, see
`docs/guides/adding-new-provider.md`.

## Provider Interface

Interface source: `src/types/provider/interfaces.ts`

All providers implement `LLMProvider`, including:

- `getInfo()`
- `validateApiKey()`
- `formatErrorDescription()`
- `getTools()`
- `createConfig()`
- `streamToDiscord()`
- `getDefaultModel()`

## Current Providers

Provider folders under `src/providers/`:

- `google` (`GoogleProvider`)
- `openrouter` (`OpenrouterProvider`)
- `novelai` (`NovelaiProvider`)
- `custom` (`CustomProvider`)
- `deepseek` (`DeepseekProvider`)
- `nvidia` (`NvidiaProvider`)
- `zai` (`ZaiProvider`)
- `zaicoding` (`ZaicodingProvider`)

## Provider Factory

Factory: `src/utils/provider/providerFactory.ts`

Important behavior:

- Providers are auto-discovered by scanning `src/providers/*`.
- Loading is lazy (constructor class loaded on first use).
- Aliases are supported from provider metadata.
  - examples: `gemini` -> `google`, `or` -> `openrouter`, `nai` -> `novelai`
- `ProviderFactory.getProviderByName()` can resolve a provider directly when a full `TomoriState` is not available.

## Provider Metadata

Static provider metadata is defined in each provider folder:

- `src/providers/google/providerInfo.ts`
- `src/providers/openrouter/providerInfo.ts`
- `src/providers/novelai/providerInfo.ts`
- `src/providers/custom/providerInfo.ts`
- `src/providers/deepseek/providerInfo.ts`
- `src/providers/nvidia/providerInfo.ts`
- `src/providers/zai/providerInfo.ts`
- `src/providers/zaicoding/providerInfo.ts`

OpenAI-compatible family internals shared by `custom`, `deepseek`, `nvidia`, `zai`, and `zaicoding` live in:

- `src/providers/openaiCompatible/`

Registry helpers live in `src/utils/provider/providerInfoRegistry.ts`.

Use these helpers instead of hardcoding provider names in commands/tools:

- `normalizeProviderName()`
- `getStaticProviderInfo()`
- `providerSupportsFeature()`
- `resolveProviderFeatureImplementation()` (legacy runtime routing for untouched paths)

Runtime capability resolution lives in:

- `src/types/provider/featureInterfaces.ts`
- `src/utils/provider/providerCapabilityResolver.ts`

`ProviderInfo.featureSupport` is the source of truth for app-level feature gating such as:

- native image generation
- embeddings
- structured output
- preset generation
- expression initialization
- live token counting
- conversation compaction
- history extraction

Rule:

- If a command only needs to know whether a provider supports a feature, use `providerSupportsFeature()`.
- If a command needs to execute a provider-owned runtime feature, resolve the optional capability from the provider instance instead of checking `provider === "google"` inline.

## Model Source of Truth

- Text models are stored in table `llms`.
- Provider code intentionally uses DB/cache-backed defaults, not hardcoded static model lists.
- Use `src/db/seed.sql` for maintained model inventory.

## Capability Resolution

### OpenRouter

- Startup cache fetch from `https://openrouter.ai/api/v1/models`
- cache module: `src/utils/cache/openrouterCapabilityCache.ts`
- OpenRouter provider can override stale DB capability flags with API capabilities at runtime.
- `supported_parameters` from the OpenRouter cache is also used to gate optional request params such as `logit_bias`.
- `/config logitbias` now stores raw text as the source of truth and caches tokenizer-specific token IDs per model family.
- Model changes refresh those cached tokenizations instead of forcing users to re-enter the same words.
- Runtime still only sends `logit_bias` when the active OpenRouter model reports support for it.
- See `docs/ai/logit-bias.md` for the storage format, refresh triggers, and tokenizer-family design.

### Gemini and NovelAI token limits

- static lookup maps:
  - `src/utils/cache/geminiCapabilityCache.ts`
  - `src/utils/cache/novelaiCapabilityCache.ts`
- used for context/token budgeting behavior.

## Multimodal Context Throttles

- `MEDIA_CONTEXT_WINDOW` limits how many recent messages can carry full media parts in context.
- `MEDIA_IMAGE_MESSAGE_LIMIT` further limits how many of those recent messages may include non-emoji, non-sticker image payloads.
- Messages outside those limits still keep text and system hints, so the model knows media exists without loading every image into provider payloads.

## Custom Provider Notes

`custom` provider is for self-hosted OpenAI-compatible endpoints (Ollama, KoboldCPP, vLLM, LocalAI, etc.).

- endpoint URL stored in `tomori_configs.custom_endpoint_url`
- optional model override in `tomori_configs.custom_model_name`
- model capabilities are user-declared and stored in `llms`
- the server-scoped custom `llms` row is preserved across normal provider switches so saved custom configs can be restored later; explicit saved-config removal still cleans it up
- designed for non-production usage
- text chat streaming is supported
- structured output, history extraction, and `/server initialize expressions` work when the configured custom model is marked with the required capabilities
- conversation compaction and roleplay compaction work through the custom endpoint using the effective configured model name
- persona preset generation works through the custom endpoint when the configured model supports structured output, and optional web search works when the model supports tools
- `/config logitbias` entries are stored in config snapshots, but Tomori does not currently auto-tokenize plain text for custom endpoints

## DeepSeek Provider Notes

`deepseek` uses the shared OpenAI-compatible family layer for bounded text/chat support.

- text chat streaming is supported
- tool calling is only enabled for models explicitly seeded with `has_tools = true`
- JSON structured output is supported on seeded DeepSeek text models through DeepSeek JSON Output plus local Zod validation
- `deepseek-reasoner` tool continuation preserves DeepSeek `reasoning_content` within the same turn
- manual `/bot respond` prefills use DeepSeek beta prefix completion when the request ends with an assistant prefill
- history extraction is enabled through the provider-owned structured output capability
- `/tool estimate cost` supports DeepSeek using conservative cache-miss input pricing by default
- no native image generation rows are seeded
- no embedding rows are seeded
- provider-level feature flags remain disabled for native image generation, embeddings, and expression initialization
- preset generation is enabled: `json_object` mode with schema injected into the system prompt + Zod validation; `deepseek-reasoner` omits the `temperature` param
- conversation and roleplay compaction are enabled through the provider-owned structured output capability

## Z.ai Provider Notes

`zai` uses the shared OpenAI-compatible family layer for the GLM model family via `https://api.z.ai/api/paas/v4`.

- **Chat models**: `zai/glm-5` (default, reasoning), `zai/glm-4.7` (reasoning), `zai/glm-4.7-flash` (free), `zai/glm-4.6v` (vision), `zai/glm-4.6v-flash` (free vision)
- **Image generation**: `zai/glm-image` via dedicated images/generations endpoint; aspect ratio mapped to pixel sizes
- Reasoning models (`glm-5`, `glm-4.7`) emit `reasoning_content` — thinking is enabled with `budget_tokens: 8192` and temperature/sampling params are deleted
- Tool streaming uses `tool_stream: true` flag when tools are present
- JSON structured output uses `response_format: { type: "json_object" }` with prompt-steered schema injection and Zod validation (same pattern as DeepSeek)
- Vision structured output supported on `glm-4.6v` and `glm-4.6v-flash`
- Output prefill uses `prefix: true` on the last assistant message (single endpoint, no beta URL)
- Model codenames stored with `zai/` prefix in DB (e.g., `zai/glm-5`), stripped to `glm-5` for API calls
- No img2img support — reference images are ignored with a user warning
- MCP vision: users can add `@z_ai/mcp-server` via `/config mcp add` for image/video analysis on non-vision models
- Conversation and roleplay compaction are enabled through the provider-owned structured output capability
- Preset generation is enabled: `json_object` mode with schema injected into the system prompt + Zod validation; reasoning models omit `temperature`

## Z.ai (Coding) Provider Notes

`zaicoding` uses the shared OpenAI-compatible family layer for the GLM family via `https://api.z.ai/api/coding/paas/v4`.

- **Chat models**: `glm-5`, `glm-4.7`, `glm-4.7-flash`, `glm-4.6v`, `glm-4.6v-flash`
- **Image generation**: `glm-image` via the coding-endpoint image generation route
- Uses the same streaming, tool-calling, and structured-output pipeline as the general `zai` provider
- Intended for dedicated coding-endpoint access such as GLM Coding Plan workflows
- Conversation compaction and roleplay compaction delegate to the shared ZAI generators with the coding endpoint URL
- Preset generation delegates to the shared ZAI generator with the coding endpoint URL and the Zaicoding tool adapter

## NVIDIA NIM Provider Notes

`nvidia` uses the shared OpenAI-compatible family layer for chat/tool/vision on `https://integrate.api.nvidia.com/v1`.

- **Chat models**: curated NVIDIA-hosted catalog rows only, seeded in `llms`
- **Embeddings**: `nv-embed-v1` via NVIDIA's embeddings endpoint
- **Image generation**: `stabilityai/stable-diffusion-3-medium` via NVIDIA's dedicated Stability endpoint
- Tool calling, vision, and structured output are gated conservatively by seeded per-model flags
- Structured output and history extraction are enabled only for the validated subset of NVIDIA text models
- Native image generation is text-to-image only right now; reference images are ignored with a warning
- `/tool estimate cost` does not support NVIDIA live token counting
- Conversation and roleplay compaction are enabled; the compact generator preprocesses images via `fetchAndOptimizeImage()`
- Preset generation is enabled: tries strict `json_schema` mode first, falls back to `json_object` + prompt steering on 400/422 errors with schema-related keywords

## Tool Integration Across Providers

Tools are provider-agnostic at registry level, then adapted per provider by each provider tool adapter.

- Google: `googleToolAdapter.ts`
- OpenRouter: `openrouterToolAdapter.ts`
- NovelAI: `novelaiToolAdapter.ts`
- DeepSeek: `deepseekToolAdapter.ts`
- Custom: `customToolAdapter.ts`
- NVIDIA NIM: `nvidiaToolAdapter.ts`
- Z.ai: `zaiToolAdapter.ts`
- Z.ai (Coding): `zaicodingToolAdapter.ts`

All providers rely on centralized tool filtering via `getAvailableToolsWithMCP()`.

### MCP Adapter Registration (Critical)

Every provider that supports tool calling **must** register its tool adapter with
`registerMCPAdapter()` in `src/events/clientReady/02_registerMCPs.ts`.

This registration is required because tool **definition** and tool **execution** use
different resolution paths:

- **Definition path**: `getAvailableToolsWithMCP()` queries the `mcpManager` directly
  to build the tool list sent to the LLM. This works for any provider regardless of
  adapter registration.
- **Execution path**: `executeTool()` calls `isMCPFunction(functionName, provider)`,
  which looks up the provider's adapter in `ToolRegistry.mcpAdapters`. If no adapter
  is registered for the provider, MCP tool calls silently fall through to the built-in
  tool check and fail with "Tool not found in registry".

If you add a new provider with tool support and skip this registration, MCP tools
(e.g. `fetch`, `web-search`) will appear in the LLM's tool list but fail at execution
time. Built-in tools will still work because they resolve through a separate path.

## Provider Runtime Capabilities

Optional provider-owned runtime capabilities now live on provider classes instead of a central implementation switch table.

Current capability layer:

- capability interfaces: `src/types/provider/featureInterfaces.ts`
- typed resolver: `src/utils/provider/providerCapabilityResolver.ts`
- thin app-level wrappers: `src/providers/utils/providerFeatureExecutors.ts`
- shared schema/builders only: `src/providers/utils/structuredOutput.ts`
- shared compaction schema/builders: `src/providers/utils/compactCommon.ts`
- shared preset schema/prompt/type builders: `src/providers/utils/presetCommon.ts`
- provider-local structured output runtimes:
  - `src/providers/google/googleStructuredOutput.ts`
  - `src/providers/openrouter/openrouterStructuredOutput.ts`
  - `src/providers/deepseek/deepseekStructuredOutput.ts`
  - `src/providers/custom/customStructuredOutput.ts`

Google and OpenRouter currently own runtime execution for:

- embeddings
- structured output execution
- preset generation
- conversation compaction
- roleplay compaction
- history extraction (via structured output capability)

DeepSeek currently owns runtime execution for:

- structured output execution
- preset generation
- conversation compaction
- roleplay compaction
- history extraction (via structured output capability)

NVIDIA currently owns runtime execution for:

- embeddings
- structured output execution
- preset generation
- conversation compaction
- roleplay compaction
- history extraction (via structured output capability)
- native image generation

Custom currently owns runtime execution for:

- structured output execution
- preset generation
- conversation compaction
- roleplay compaction
- history extraction (via structured output capability)

ZAI and ZAI (Coding) currently own runtime execution for:

- structured output execution
- preset generation
- conversation compaction
- roleplay compaction
- history extraction (via structured output capability)
- native image generation

Live token counting for `/tool estimate cost` still uses a temporary legacy command path for Google, OpenRouter, DeepSeek, and the Z.ai family. NVIDIA intentionally does not implement live token counting.

Rule:

- Keep `providerSupportsFeature()` as the common early-gating helper.
- Put runtime execution on the provider instance when the feature is app-level and provider-specific.
- Keep provider-specific implementation code inside `src/providers/{providerName}/` or shared family internals.
- If a shared utility exists, keep it genuinely generic; provider-specific HTTP requests, prompt shaping, and response parsing should stay in the provider folder.
- `resolveProviderFeatureImplementation()` is now temporary legacy routing for the runtime paths that have not been migrated yet.

## Writing Provider-Aware Commands

When adding a new command or tool flow that depends on provider support:

1. Decide whether the command only needs static gating, or also needs runtime execution.
2. Add or reuse a `ProviderInfo.featureSupport` flag for the app-level feature.
3. In the command, fail early with `providerSupportsFeature(providerName, featureName)`.
4. If runtime execution is needed, resolve the provider-owned capability instead of switching on provider names.

Use this pattern:

- static gating only:
  - examples: hide/deny a feature before execution, validate setup, choose UI availability
  - use `providerSupportsFeature()`
- migrated runtime execution:
  - examples: embeddings, structured output, preset generation, compaction, history extraction
  - use `src/utils/provider/providerCapabilityResolver.ts` directly or a thin wrapper such as `src/providers/utils/providerFeatureExecutors.ts`
- legacy runtime execution:
  - examples: native image generation, live token counting
  - these still use `resolveProviderFeatureImplementation()` temporarily until migrated

Rules for command authors:

- Do not add new `provider === "google"` or `provider === "openrouter"` checks in commands for app-level features.
- Keep provider identity separate even when internals are shared across a family.
- If a provider does not implement the runtime capability, return a clean unsupported error near the command boundary.
- If a new feature will be reused by multiple commands, prefer adding a new optional capability interface over creating another central switch table.

Current command examples:

- `src/commands/server/initialize/expressions.ts`
- `src/commands/persona/generate.ts`
- `src/commands/tool/compact.ts`
- `src/commands/teach/history.ts`

## Intentional Exceptions

Some literal provider names are still correct and should remain explicit:

- flows that require a truly provider-specific optional credential
- direct vendor-specific capabilities that are not abstracted yet
- remaining legacy runtime paths such as native image generation and live token counting until they are moved onto provider capabilities

Example:

- NovelAI inpainting can optionally use a Google key for Gemini segmentation. That is intentionally a Google-specific integration, not a generic "Gemini-family" provider capability.

## Context Item Tag Routing (Important)

`ContextItemTag` in `src/types/misc/context.ts` controls whether a context block is injected as:

- provider system instruction
- conversation history

Use this mental model when adding new context blocks:

- system instruction tags (`SYSTEM_*`, `KNOWLEDGE_*`) are prompt-level guidance
- dialogue tags (`DIALOGUE_*`) are chat history items

Critical rule:

- If an instruction must appear in conversation history, inject with `DIALOGUE_HISTORY`
  and the correct role (`"user"`/`"model"`), not with `SYSTEM_*`/`KNOWLEDGE_*`.
- Generated media annotations such as `[System: This message contains an image...]`
  or media tool-use hints should be detached into their own synthetic `"user"`
  `DIALOGUE_HISTORY` item so assistant turns only carry speaker-authored content.

Why this matters:

- providers treat system instruction and history differently for behavior/token usage
- incorrect tagging can silently change response quality and tool behavior

## API Key Setup Commands

- `/config apikey set provider:google key:...`
- `/config apikey set provider:openrouter key:...`
- `/config apikey set provider:novelai key:...`
- `/config apikey set provider:deepseek key:...`
- `/config apikey set provider:nvidia key:...`
- `/config apikey set provider:zai key:...`
- `/config apikey set provider:zaicoding key:...`

Provider choice/model selection commands:

- `/config model text`
- `/config model image`
- `/config model embedding`
