# Unified Tool System Plan

## Executive Summary

FemboiBot's current tool flow works, but it is not yet a durable tool platform. Tool definitions are thin, availability is mostly feature-flag based, execution is orchestrated inside `ai_brain.py`, prompt-emulated tool calls are coupled to one parser shape, and there is no first-class policy engine, no MCP control plane, and no durable tool execution audit trail. That is workable for a small built-in tool set, but it will not scale cleanly to provider-aware gating, model-aware gating, admin-global and guild-scoped MCP, category policy, automatic quarantine, or serious operational introspection.

The recommended target architecture is a layered in-process tool control plane with DB-backed policy, MCP registration, quarantine, and audit state. The key architectural choice is separation of concerns:

- discovery determines which tools exist
- policy determines whether they are allowed for the current turn
- transport determines how the model sees and emits tool calls
- execution runs the tool through a backend adapter
- observability records what happened and why

This plan deliberately does not optimize for the smallest MVP. It optimizes for the cleanest long-term architecture that can still be rolled out incrementally in this Python `discord.py` repo without breaking current user-visible tool behavior.

The first rollout should standardize on prompt-emulated tool calls across providers, but the design must remain explicitly compatible with native provider tool-calling adapters later. MCP should be first-class from the architecture level, but introduced safely with admin-global scope first, trusted registration requirements, discovery approval, explicit policy, health monitoring, and strong runtime degradation behavior.

## Current-State Audit

### Files and references inspected

Primary FemboiBot files inspected:

- `discord_bot/cogs/ai_brain.py`
- `discord_bot/utils/tool_registry.py`
- `discord_bot/utils/tool_parser.py`
- `discord_bot/utils/tool_flags.py`
- `discord_bot/utils/tool_context.py`
- `discord_bot/utils/web_search.py`
- `discord_bot/utils/url_fetcher.py`
- `discord_bot/utils/image_generation.py`
- `discord_bot/utils/expression_tools.py`
- `discord_bot/utils/pin_tool.py`
- `discord_bot/utils/profile_peek.py`
- `discord_bot/utils/db_handler.py`
- `discord_bot/cogs/config.py`
- `discord_bot/cogs/tools_admin.py`
- `discord_bot/utils/guild_ai.py`
- `discord_bot/utils/feature_flag_mapper.py`
- `discord_bot/utils/review_capabilities.py`
- `discord_bot/utils/self_teaching.py`

Tomori reference docs inspected:

- `E:\femboibot\tomoribot\docs\systems\tool-system.md`
- `E:\femboibot\tomoribot\docs\ai\providers.md`
- `E:\femboibot\tomoribot\docs\systems\security.md`
- `E:\femboibot\tomoribot\docs\systems\caching.md`

Requested repo docs not found at the specified paths:

- `docs/FEATURES.md`
- `docs/AGENTS.md`

### Current architecture summary

Current tooling is centered around `discord_bot/utils/tool_registry.py`.

- `ToolDefinition` contains:
  - `name`
  - `description`
  - `args_schema`
  - `handler`
  - `feature_flag`
  - `required_permission`
  - `allow_in_dms`
- `ToolResult` contains:
  - `ok`
  - `summary`
  - `data`
  - `user_message`
  - `skip_model`
- tool registration is manual through `register_builtin_tools()`
- there is one in-memory registry, no namespacing, no source-type distinction, no rich metadata model

Tool invocation is prompt-emulated:

- `tool_parser.py` extracts a fenced JSON tool block
- the model emits a payload like:
  - `{"tool": "web_search", "args": {...}}`
- `ai_brain.py` parses that response
- `ai_brain.py` executes the tool directly through the registry
- `ai_brain.py` appends the tool result back into the chat loop

Current availability logic is coarse:

- guild feature flags come from `guild_config`
- `tool_flags.py` and `feature_flag_mapper.py` map tool names to coarse capability flags
- `tool_registry.py` adds only DM and mod/admin permission checks
- there is no explicit provider-aware gating
- there is no explicit model-aware gating
- there are no per-tool allow/deny policy overrides
- there are no category-scoped policies
- cooldowns and runtime rate limits are not part of availability computation

Current provider model is also ad hoc:

- `ai_brain.py` selects OpenRouter for evil mode, then custom endpoint, then Gemini
- `guild_ai.py` exposes per-guild provider key/model/config helpers
- `custom_model_capabilities` exists in `guild_config`, which is useful, but it is not part of a general tool gating engine

Current admin/debug tooling is limited:

- `config.py` toggles capability flags and config state
- `tools_admin.py` shows enabled and disabled tools
- there is no "why was this tool filtered out for this turn?" view
- there is no execution history or structured audit trail for tool runs
- there is no quarantine state, trust state, or health model for unstable tools

Current tool implementation shape is inconsistent:

- built-in and REST-backed tools are both represented as direct Python handlers
- some tools choose their own runtime providers internally
- some tools perform side effects directly in the handler
- some tools embed provider assumptions that should eventually move into metadata or backend adapters

Current storage model is strong enough to support the refactor:

- per-guild config already lives in `guild_config`
- `guild_config_audit` already exists
- a global DB already exists for stats and guild registry
- execution logs, MCP registrations, policy tables, and quarantine state can live in the global DB keyed by `guild_id`

### Main weaknesses

1. The current registry is not a true control plane.
2. Tool metadata is too thin for durable policy, safety, and interoperability.
3. `ai_brain.py` owns orchestration that should belong to tooling infrastructure.
4. Availability decisions are opaque and not inspectable.
5. There is no unified abstraction for built-in, REST, and MCP tools.
6. There is no first-class concept of discovered remote tools.
7. There is no privacy-safe audit trail for tool execution.
8. There is no quarantine model for unstable tools.
9. There is no clean future path to native provider tool-calling adapters.

## Design Goals and Non-Goals

### Goals

- Provide one coherent registry and execution model for built-in, REST, and MCP tools.
- Compute "available tools for this turn" centrally instead of hardcoding tool choices in cogs.
- Make filtering explicit across:
  - provider
  - model
  - guild feature flags
  - category policy
  - tool policy
  - Discord permissions
  - cooldown/rate-limit state
  - runtime context
- Support policy modes from day one:
  - `allow`
  - `deny`
  - `admin_only`
  - `manual_only`
- Support category-scoped and tool-scoped policy from day one.
- Support admin-global MCP in v1 and guild-scoped MCP later through the same architecture.
- Keep prompt-emulated tool calling as the v1 runtime standard across providers.
- Stay compatible with future native provider tool-calling adapters.
- Preserve current user-visible tool behavior during migration where feasible.
- Make execution observable, auditable, and privacy-safe by default.
- Support automatic quarantine for unstable tools, with admin visibility and manual override.

### Non-goals

- Rewriting every existing tool implementation before the new control plane exists.
- Forcing all tools into MCP.
- Making native provider tool calling a dependency for the first rollout.
- Storing rich policy or MCP registration state inside `guild_config`.
- Logging raw args/results by default.
- Requiring per-tool quarantine threshold tuning in v1.

## Architecture Options

### Option 1: Expanded Flat Registry

Description:

- keep one main registry module
- add more fields to `ToolDefinition`
- continue executing from `ai_brain.py`
- layer more checks around the current flow

Pros:

- smallest amount of code movement
- easiest short-term migration

Cons:

- keeps orchestration coupled to the cog
- encourages continued branching by source type and provider
- hard to scale cleanly to MCP trust, category policy, quarantine, and approval workflows
- difficult to keep introspection and execution consistent

Assessment:

- viable as a short-term patch
- not strong enough for the requested long-term design

### Option 2: Layered In-Process Tool Control Plane

Description:

- one in-process registry
- separate modules for:
  - contracts
  - discovery
  - policy
  - availability
  - transport
  - execution
  - audit
  - MCP control plane
- DB-backed policy, registration, quarantine, and audit state

Pros:

- clean separation of concerns
- realistic in Python and `discord.py`
- supports incremental rollout
- supports built-in, REST, and MCP through the same abstraction
- naturally supports prompt-emulated now and native adapters later

Cons:

- higher up-front design and migration cost
- requires stronger schema work early

Assessment:

- strongest realistic option for this repo
- recommended

### Option 3: DB-Driven Dynamic Control Plane

Description:

- push much more of the registry into database state
- synthesize tool definitions dynamically from stored metadata
- use DB as primary source of truth for most tools

Pros:

- powerful for fully dynamic remote tool ecosystems
- admin-driven control can be very rich

Cons:

- too much complexity for current repo maturity
- higher risk of drift between code-owned built-ins and DB-owned metadata
- testing and refactoring cost is high

Assessment:

- good source of ideas for policy and MCP state storage
- not the right primary architecture for this repo

## Recommended Architecture

The recommended architecture is **Option 2: Layered In-Process Tool Control Plane**.

### Architectural layers

1. **Descriptor Layer**
- defines what a tool is
- source type, category, schema, permissions, policy defaults, runtime requirements

2. **Registry Layer**
- stores canonical descriptors
- indexes by internal ID, public name, aliases, scope
- handles built-in, REST, and discovered MCP tools

3. **Policy Layer**
- resolves category and tool policy
- enforces `allow`, `deny`, `admin_only`, `manual_only`
- handles trust state and quarantine state

4. **Availability Layer**
- computes current-turn allowed tools
- returns structured denial reasons for admin/debug surfaces

5. **Transport Layer**
- prompt-emulated tool-call rendering and parsing in v1
- future native provider adapters later

6. **Execution Layer**
- validate
- authorize
- execute
- normalize
- log

7. **Audit and Operations Layer**
- privacy-safe execution logs
- quarantine state
- MCP health
- debug raw capture

8. **MCP Control Plane**
- registrations
- trust and approval
- discovery cache
- health and cooldown

### Source-type model

All tools share the same registry and policy engine, but execute through different backends:

- `builtin`
- `rest`
- `mcp`

The source type must not change how policy is modeled. It only changes discovery, readiness checks, and execution backend behavior.

### Scope model

Scopes must exist from day one:

- global operational scope
- admin-global MCP scope
- guild scope
- category scope
- tool scope

This avoids building guild-scoped MCP as a special case later.

## Core Interfaces and Data Models

### ToolDescriptor

Recommended core fields:

- `tool_id`
- `public_name`
- `aliases`
- `source_type`
- `source_ref`
- `scope_type`
- `guild_id` nullable
- `display_name`
- `description`
- `category`
- `tags`
- `input_schema`
- `output_schema`
- `required_user_permission`
- `required_bot_permissions`
- `dm_policy`
- `provider_requirements`
- `model_requirements`
- `runtime_requirements`
- `rate_limit_policy`
- `cooldown_policy`
- `side_effect_level`
- `default_policy_mode`
- `supports_model_invocation`
- `supports_manual_invocation`
- `stability`
- `operational_state`
- `quarantine_behavior`
- `trust_requirements`

### ToolTurnContext

- `request_id`
- `turn_id`
- `guild_id`
- `channel_id`
- `thread_id`
- `user_id`
- `guild`
- `channel`
- `member`
- `guild_config`
- `provider_name`
- `model_name`
- `provider_capabilities`
- `model_capabilities`
- `rate_limit_snapshot`
- `cooldown_snapshot`
- `debug_mode`
- `timestamp`

### ToolAvailabilityDecision

- `tool_id`
- `public_name`
- `category`
- `candidate`
- `allowed`
- `effective_policy_mode`
- `is_quarantined`
- `decision_layers`
- `primary_reason_code`
- `reason_detail`
- `admin_visible_metadata`

### ToolCallEnvelope

The execution layer should receive a transport-neutral call envelope:

- `call_id`
- `tool_name`
- `tool_id` nullable until resolved
- `arguments`
- `invocation_mode`
- `raw_payload`
- `transport_metadata`

### ToolExecutionResult

- `status`
- `summary`
- `model_visible_output`
- `user_visible_override`
- `structured_output`
- `side_effects`
- `latency_ms`
- `error_category`
- `retryable`
- `redacted_args_summary`
- `redacted_result_summary`
- `raw_capture_eligible`
- `backend_metadata`

### Backend protocol

Each backend should implement a common async execution interface:

- `execute(invocation, context) -> ToolExecutionResult`

Backend types:

- builtin backend wraps current Python handlers
- REST backend wraps outbound API tools
- MCP backend wraps approved remote tool calls

## Policy and Filtering Pipeline

The policy engine must evaluate tools in explicit layers, with structured reason codes at each step.

### Policy modes

- `allow`
- `deny`
- `admin_only`
- `manual_only`

### Admin-only qualification

`admin_only` should resolve to allowed only if the invoking user is one of:

- Discord Administrator
- the repo's existing top-level configured admin/staff tier, if it already represents equivalent high-trust authority

Lower staff/mod tiers do not qualify.

### Policy scopes

- category-scoped policy from day one
- tool-scoped policy from day one
- global and guild policy support

### Recommended evaluation order

1. Candidate discovery
2. Global operational disable
3. Trust and approval gate
4. Quarantine gate
5. Provider capability gate
6. Model capability gate
7. Guild capability flag gate
8. Category policy gate
9. Tool policy gate
10. Discord user permission gate
11. Bot permission gate
12. DM/thread/context gate
13. Runtime readiness gate
14. Cooldown/rate-limit gate
15. Contextual relevance gate

### Trust and approval

For discovered MCP tools:

- discovery and inventory do not imply runtime eligibility
- discovered tools can be visible to admins before approval
- they do not become normal runtime candidate descriptors until approved

Trust rules:

- admin-global MCP requires explicitly trusted registration
- guild-scoped MCP later defaults deny until guild admin allows/enables
- no broad default allow for discovered remote tools

### Quarantine

Quarantine should act as a policy gate.

Threshold model:

- global default thresholds
- per-category overrides allowed
- no per-tool threshold tuning required in v1

Automatic quarantine applies when repeated failures cross the effective threshold for that tool's category/scope.

### Manual-only

`manual_only` tools:

- are excluded from normal model-visible tool lists
- remain visible in admin-facing capability/review surfaces
- must be clearly labeled as non-auto-invocable and manual/admin-trigger only

### Available tools for this turn

Normal runtime should only receive tools where:

- trust/approval is satisfied
- quarantine is not active
- effective policy mode resolves to `allow`, or `admin_only` with a qualifying admin user
- all capability, permission, runtime, and cooldown gates pass

Admin/debug surfaces should receive:

- all candidate tools
- denied tools
- exact filtering reasons
- effective policy mode
- quarantine state
- trust state

## Registry/Discovery Model

### Registry responsibilities

- register code-owned built-in descriptors at startup
- register code-owned REST descriptors at startup
- synthesize approved MCP descriptors from discovery state
- maintain canonical IDs and aliases
- prevent collisions

### Internal ID model

Recommended internal ID format:

- `builtin:web_search`
- `rest:generate_image`
- `mcp:admin_global:server_slug:remote_tool_name`
- `mcp:guild:123456789:server_slug:remote_tool_name`

`public_name` can stay simpler where needed for compatibility, but policy and audit should always key off the stable internal ID.

### Discovery model

Built-in and REST:

- code-owned descriptors
- loaded at startup

MCP:

- registration in DB
- discovery against registered server
- discovered tools stored as inventory records
- admin approval/trust step
- approved discovered tools promoted to normal candidate descriptors

### MCP lifecycle

1. register server
2. validate transport/config
3. discover remote tools
4. store inventory
5. admin reviews and approves
6. approved tools become candidate descriptors
7. policy and availability engine decide runtime exposure

This separation between discovery and eligibility is critical for remote tool safety.

## Execution Pipeline

### V1 transport

Prompt-emulated tool calling remains the standard across providers in v1.

Canonical desired payload:

```tool
{"name":"tool_name","arguments":{"key":"value"},"call_id":"optional-id"}
```

Migration compatibility:

- continue accepting legacy payload:
  - `{"tool":"tool_name","args":{...}}`
- parser should normalize both into `ToolCallEnvelope`

### Execution stages

1. Provider/model resolved for the turn
2. `ToolTurnContext` built
3. registry computes candidate tools
4. policy/availability engine computes decisions
5. model-visible tool list built from allowed decisions only
6. provider transport renders prompt-emulated instructions
7. model emits tool call
8. parser normalizes to `ToolCallEnvelope`
9. descriptor resolved by name/alias
10. arguments validated against schema
11. policy re-check at execution time
12. backend executes tool
13. result normalized
14. redacted summaries built
15. execution log written
16. optional raw capture written only if explicitly enabled
17. tool result returned to chat loop

### Failure handling requirements

Unavailable tool:

- return normalized unavailable result
- log `execution_outcome=unavailable`
- provide reason code

Denied tool:

- return normalized denied result
- do not execute
- log denial path

Timeout:

- return retryable timeout result
- increment backend/category failure counters
- participate in quarantine thresholds

Malformed arguments:

- reject before backend execution
- return validation error result
- do not count as backend instability unless parser/descriptor mismatch indicates systemic issue

Execution exceptions:

- return normalized error result
- log category
- count toward quarantine if backend/systemic

Partial results:

- supported through `status=partial`
- include safe structured summary

MCP transport failure:

- mark backend error
- update MCP health state
- contribute to quarantine and health cooldown logic

## Logging/Observability Model

Logging must be privacy-safe by default.

### Default logging principles

- always log structured metadata
- default to redacted/summarized args/results
- never store full raw args/results by default
- raw capture only through explicit temporary admin/debug control

### Global DB execution log

Table: `tool_execution_log`

Required dimensions:

- `guild_id`
- `channel_id`
- `user_id`
- `provider`
- `model`
- `tool_name`
- `tool_source_type`
- `invocation_mode`
- `decision_outcome`
- `execution_outcome`
- `latency_ms`
- `timestamp`
- `error_category`

Additional recommended columns:

- `request_id`
- `turn_id`
- `tool_id`
- `category`
- `reason_codes_json`
- `args_summary_json`
- `result_summary_json`
- `debug_capture_id`

### Raw capture

Separate table: `tool_debug_capture`

- disabled by default
- explicit admin/debug enablement only
- strict TTL cleanup
- linked from execution log through `debug_capture_id`

### Quarantine and health observability

Tables:

- `tool_quarantine_state`
- `mcp_server_health`

Admin surfaces should show:

- current quarantine state
- reason
- thresholds
- recent failure history
- MCP health and cooldown

## Schema/Config Changes

### Keep in `guild_config`

- coarse capability flags
- provider config
- model config
- existing custom endpoint capability hints

### Add to global DB

- `tool_execution_log`
- `tool_debug_capture`
- `tool_policy_rules`
- `tool_policy_audit`
- `tool_quarantine_state`
- `tool_quarantine_policy`
- `mcp_server_registrations`
- `mcp_discovered_tools`
- `mcp_server_health`

### Category quarantine policy

`tool_quarantine_policy` should support:

- global default thresholds
- per-category overrides

This matches the decision not to require per-tool threshold tuning in v1.

### Admin commands and config surfaces

`config.py` and `tools_admin.py` should gain surfaces for:

- category policy
- tool policy
- MCP registration
- MCP trust/approval
- quarantine inspection/override
- temporary raw capture controls

## File Impact Map

### Existing files likely to change

- `discord_bot/cogs/ai_brain.py`
  - remove direct ownership of tool selection logic
  - call new availability and execution services

- `discord_bot/utils/tool_registry.py`
  - likely becomes compatibility layer or is split into new registry modules

- `discord_bot/utils/tool_parser.py`
  - upgraded to support canonical and legacy prompt-emulated payloads

- `discord_bot/utils/tool_flags.py`
  - slimmed down into legacy compatibility helpers

- `discord_bot/utils/tool_context.py`
  - replaced or expanded into richer turn context model

- `discord_bot/utils/web_search.py`
- `discord_bot/utils/url_fetcher.py`
- `discord_bot/utils/image_generation.py`
- `discord_bot/utils/expression_tools.py`
- `discord_bot/utils/pin_tool.py`
- `discord_bot/utils/profile_peek.py`
- `discord_bot/utils/self_teaching.py`
  - migrated to first-class descriptors or wrapped by compatibility layer

- `discord_bot/utils/db_handler.py`
  - substantial global DB schema additions

- `discord_bot/cogs/config.py`
  - add policy, MCP, and debug admin controls

- `discord_bot/cogs/tools_admin.py`
  - expand into capability review, filtered-tool introspection, policy and quarantine surfaces

- `discord_bot/utils/guild_ai.py`
  - expose normalized provider/model capability information to the tool system

### New modules recommended

- `discord_bot/tools/contracts.py`
- `discord_bot/tools/descriptors.py`
- `discord_bot/tools/registry.py`
- `discord_bot/tools/policy_engine.py`
- `discord_bot/tools/availability.py`
- `discord_bot/tools/executor.py`
- `discord_bot/tools/audit.py`
- `discord_bot/tools/provider_capabilities.py`
- `discord_bot/tools/transports/prompt_emulated.py`
- `discord_bot/tools/transports/native_base.py`
- `discord_bot/tools/backends/builtin.py`
- `discord_bot/tools/backends/rest.py`
- `discord_bot/tools/backends/mcp.py`
- `discord_bot/tools/mcp/manager.py`
- `discord_bot/tools/mcp/discovery.py`
- `discord_bot/tools/mcp/approval.py`
- `discord_bot/tools/mcp/health.py`

## Migration Phases

### Phase 1: Contracts and compatibility scaffolding

- add new contracts and registry skeleton
- wrap current `ToolDefinition` objects in compatibility descriptors
- no runtime behavior change

Safe checkpoint:

- all current tools still register and execute as before

### Phase 2: Category normalization and policy schema

- define stable category set
- add category and tool policy tables
- add policy engine in shadow mode

Safe checkpoint:

- admin/debug output can compare current behavior with new policy decisions without changing runtime

### Phase 3: Privacy-safe execution logging

- add execution log and debug capture schema
- log current tool executions through compatibility layer

Safe checkpoint:

- no behavior change, but tool runs are now auditable

### Phase 4: Registry-driven availability in shadow mode

- compute candidate tools and denial reasons per turn
- compare with current `get_available_tools()` results

Safe checkpoint:

- drift between old and new availability is visible before switchover

### Phase 5: Runtime switch to new availability/execution pipeline

- `ai_brain.py` asks new resolver for "available tools for this turn"
- keep prompt-emulated tool transport
- keep current tool loop semantics

Safe checkpoint:

- user-visible behavior remains stable while policy and audit are centralized

### Phase 6: Admin/debug surfaces

- add tool/category policy commands
- add filtered-tool introspection
- add quarantine and raw-capture admin controls

Safe checkpoint:

- admins can fully inspect and influence tool behavior before MCP rollout

### Phase 7: Automatic quarantine

- add threshold policies
- implement quarantine state transitions and admin override

Safe checkpoint:

- unstable tools can be isolated without removing them from code

### Phase 8: Admin-global MCP

- add trusted server registration
- inventory discovered tools
- require approval before eligibility
- execute approved MCP tools through backend adapter

Safe checkpoint:

- admin-global MCP works without changing the AI cog again

### Phase 9: Guild-scoped MCP

- store in global DB keyed by `guild_id`
- same discovery, approval, policy, and execution path
- default deny until guild admin allows/enables

Safe checkpoint:

- scope separation and safety bias verified

### Phase 10: Future native provider adapters

- add provider-native definition/rendering/parsing adapters
- keep the same registry, policy engine, and executor

Safe checkpoint:

- one provider can move to native tool-calling without architectural churn

## Testing Strategy

### Unit tests

- descriptor validation
- category validation
- policy precedence resolution
- admin-only qualification logic
- manual-only visibility logic
- quarantine threshold calculation
- provider/model capability normalization
- prompt-emulated parser normalization
- redaction and summary generation

### Registry tests

- built-in registration
- REST registration
- discovered MCP inventory registration
- approved MCP descriptor promotion
- collision and alias handling
- category and tool lookups

### Policy tests

- category allow/deny/admin_only/manual_only
- tool allow/deny/admin_only/manual_only
- precedence between category and tool policy
- guild flag interaction with explicit policy
- trust state interaction with policy
- quarantine interaction with policy

### Parser tests

- canonical payload parsing
- legacy payload parsing
- malformed JSON
- invalid schema type
- unknown tool name
- multiple tool-loop edge cases

### Tool execution tests

- success path for built-in tools
- success path for REST tools
- success path for approved MCP tools
- timeout handling
- malformed arg rejection
- exception normalization
- partial result handling
- side-effect tool permission behavior

### Failure-path tests

- unavailable tool
- denied tool
- untrusted MCP server
- discovered but unapproved MCP tool
- MCP transport failure
- repeated backend failures causing quarantine
- admin override of quarantine

### Migration/regression tests

- current tool names preserved
- current prompt-emulated flow preserved
- current guild feature flags still respected
- current tool behavior for search/image/pin/profile/memory remains acceptable

### Operational tests

- policy changes invalidate caches correctly
- debug raw capture expires correctly
- admin-global MCP discovery/approval works
- guild-scoped MCP default deny works
- filtered-tool introspection shows exact reasons

## Risks and Open Questions

### Risks

- Some current tools embed provider choices internally, which will require careful migration.
- Prompt-emulated tool calling still requires strong schema validation and parser hardening.
- MCP introduces remote schema drift, transport reliability issues, and operational overhead.
- Policy complexity can become hard to reason about without excellent admin/debug UX.
- Quarantine thresholds that are too aggressive may hide useful tools; thresholds that are too loose may not protect operations enough.
- Privacy-safe logging needs strict discipline so later debug features do not silently erode the default safety posture.

### Open questions

- Should the top-level configured admin/staff tier be identified by the existing `permission_level == 2` model, or should there be an explicit "tool admin equivalent" concept?
- Should approval of discovered MCP tools happen per tool, per server, or both?
- Should `manual_only` tools be invocable only through explicit admin slash commands, or also through separate debug console flows?
- Should quarantine be scoped only globally and per guild, or also per provider/model combination for remote-heavy tools?
- Should there be a separate "experimental" stability class that defaults tools into `manual_only` even before they fail?

### Recommendation on unresolved areas

- Treat existing highest-trust configured staff tier as admin-equivalent only if it already functions as equivalent top-level authority in the repo today.
- Require tool-level approval for discovered MCP tools, not just server-level trust.
- Limit `manual_only` execution to explicit admin/debug command surfaces in v1.
- Keep quarantine scoped at global and guild levels in v1, with provider/model detail logged but not yet used as a distinct policy scope.
