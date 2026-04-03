# 9. Tool System

TomoriBot exposes built-in tools, MCP tools, and REST-backed tools through one central registry.

## Core Components

- Registry: `src/tools/toolRegistry.ts`
- Startup loader: `src/tools/toolInitializer.ts`
- Tool contracts: `src/types/tool/interfaces.ts`
- Feature flag mapper: `src/utils/tools/featureFlagMapper.ts`

## Registration Model (Current)

Built-in tools are class-based:

- each tool extends `BaseTool`
- `toolInitializer.ts` auto-discovers classes in `src/tools/functionCalls/`
- no manual `registerTool(...)` calls in tool files

## Built-In Function Tools (Current)

From `src/tools/functionCalls/`:

- `remember_this_fact` (`memoryTool.ts`)
- `update_long_term_memory` (`updateLongTermMemoryTool.ts`)
- `update_short_term_memory` (`updateShortTermMemoryTool.ts`)
- `create_task` (`reminderTool.ts`)
- `select_sticker_for_response` (`stickerTool.ts`)
- `process_youtube_video` (`youtubeVideoTool.ts`)
- `pin_selected_message` (`pinMessageTool.ts`)
- `peek_profile_picture` (`peekProfilePictureTool.ts`)
- `increase_media_context` (`increaseMediaContextTool.ts`)
- `process_gif` (`processGifTool.ts`)
- `generate_image` (`generateImageTool.ts`)
- `generate_image_nai` (`generateImageNaiTool.ts`)
- `review_capabilities` (`reviewCapabilities.ts`)

Current `cross_channel_message` runtime notes:

- can target another text channel immediately without scheduling
- also supports thread targets by exact `channel_id`
- fallback `channel_name` lookup checks both guild channel names and active thread titles
- thread permission checks use `SendMessagesInThreads` instead of `SendMessages`
- Discord channel/thread links in prompt context are normalized into the same readable `#name` + ID form used for channel mentions, so pasted links are easier for the model to reuse as `channel_id` targets

Current `generate_image_nai` runtime notes:

- server-wide style tags come from `/novelai tags style` via `tomori_configs.nai_style_tags`
- server-wide negative tags come from `/novelai tags negative` via `tomori_configs.nai_negative_tags`
- the dedicated `generate_image_nai` model override comes from `/novelai image model` via `tomori_configs.nai_diffusion_model_id`, with fallback to the shared image model only when that shared model is already NovelAI
- `characters[]` now drives V4 multi-character prompting for `generate_image_nai`; coordinate mode is enabled when two or more characters are present
- persona and user appearance tags are resolved from `tomoris.nai_tags` and `users.nai_char_tags`
- tool guidance for `generate_image_nai` now uses a simpler inline-tag model: each `characters[]` item is one visible character instance, and `characters[].tags` must contain that character's full appearance plus their role in the scene. For erotic scenes, clothing tags can be omitted and the intended nude state can be stated directly in `tags`. The active schema/runtime no longer advertises `id`-driven appearance autofill or `remove_tags`; if saved appearance tags are available for a known persona/user, they are shown inline in context and the model is expected to copy them into `tags`
- persona and user reference images are resolved from `tomoris.nai_char_ref_url` and `users.nai_char_ref_url`, normalized onto NovelAI's supported reference canvases with black padding, and sent through `director_reference_images` only for single-character generations when `NAI_ENABLE_CHAR_REFERENCES` is enabled
- avatar-targeting tools that share `avatarResolver.ts` now accept `self` for the current active persona and also treat the bot's Discord user ID as an execution-time alias for that persona, keeping `peek_profile_picture`, `generate_image.user_id`, and `generate_image_nai.characters[].id` aligned
- tool-facing schema guidance now also explicitly prefers `self` over the bot's Discord user ID when the active persona is the intended target, without assuming a specific bot or persona name
- context building now includes saved NAI appearance tags inline on the relevant user/persona conversation entries instead of a separate `# Image Profiles` knowledge block, so image identity guidance stays attached to the same entity description the model is already reading
- provider tool adapters now preserve nested array/object tool schemas recursively, so structured tool params such as `characters[]` survive provider conversion

Current `update_short_term_memory` runtime notes:

- the tool is hidden for a turn when the triggering user message explicitly asks the bot to remember something for future use
- this suppression currently uses a shared English/Japanese phrase detector so direct long-term-memory requests do not compete with STM summary nudges in the same turn

## REST API Tools

- Brave REST tool classes in `src/tools/restAPIs/brave/braveTools.ts`:
  - `brave_web_search`
  - `brave_image_search`
  - `brave_video_search`
  - `brave_news_search`

## MCP Integration

- MCP manager: `src/utils/mcp/mcpManager.ts`
- MCP registration handler: `src/events/clientReady/02_registerMCPs.ts`
- MCP server definitions/configs: `src/tools/mcpServers/*`

Current MCP behavior notes:

- Google and OpenRouter MCP-capable adapters are registered at startup.
- NovelAI MCP adapter is intentionally disabled due prompt budget constraints.
- Guild-registered remote MCP servers added via `/config mcp add` are validated before save and again before each connection attempt.
- In production, guild MCP servers must use HTTPS and resolve only to publicly routable IP addresses.
- Direct HTTP/SSE transports for guild MCP servers disable redirects so a validated URL cannot bounce to a different internal target later.

## Current MCP Servers

From `src/tools/mcpServers/`:

- `brave-search`
- `fetch`
- `duckduckgo-search` (kept available, but search routing may prefer Brave when Brave API is configured)

## Tool Filtering and Availability

`ToolRegistry` filters tools by:

- provider availability (`isAvailableFor` / context-aware checks)
- declared model capability requirements (`requiredModelCapabilities`)
- feature flags (mapped by `featureFlagMapper.ts`)
- permission requirements (`requiresPermissions`)

Centralized helper:

- `getAvailableToolsWithMCP(provider, stateForContext)`
  - returns filtered built-in tools + filtered MCP function names
  - the first pass uses `stateForContext.llm` to filter capability-gated tools before any streaming-context-only checks run

Additional routing logic:

- when Brave API is available, DuckDuckGo MCP search functions are excluded to prefer Brave.
- when Brave is unavailable, DuckDuckGo `web-search` remains the primary free search path.
- if DuckDuckGo `web-search` is rate-limited or returns no usable result, the DuckDuckGo handler may retry internally with `felo-search`.
- `felo-search` remains hidden from provider tool lists; it is used as an internal fallback, not a first-class exposed tool.

## Tool Categories

`ToolCategory` values in current type contracts:

- `discord`
- `search`
- `memory`
- `utility`
- `mcp`

## Creating a New Built-In Tool

1. Add a file under `src/tools/functionCalls/`.
2. Export a class that extends `BaseTool`.
3. Define:
   - `name`, `description`, `category`
   - JSON-schema-like `parameters`
   - `execute(args, context)`
4. Optionally set:
   - `requiredModelCapabilities`
   - `requiresFeatureFlag`
   - `requiresPermissions`
   - `requiresFollowUp`
5. Restart bot; startup auto-discovery registers the tool.

## Observability

Registry tracks execution history and stats:

- `getExecutionHistory(limit)`
- `getStats()`
