# Unified Tool System Runtime Notes

This document captures the implemented runtime shape after the unified tool-system refactor rollout.

## Runtime architecture

The active runtime remains prompt-emulated tool calling.

The stack is now explicitly layered:

- `tools.registry`
  - canonical descriptors for built-in and promoted MCP tools
- `tools.policy_engine`
  - global and guild category/tool rules
  - policy modes: `allow`, `deny`, `admin_only`, `manual_only`
- `tools.availability`
  - current-turn allow/deny decisions with structured denial reasons
  - quarantine, MCP trust/enablement, and MCP cooldown visibility
- `tools.executor`
  - central authorization and dispatch
  - built-in compatibility path plus MCP backend dispatch
- `tools.audit`
  - privacy-safe execution logging with summary/redacted defaults
  - temporary raw capture windows only by explicit admin action
- `tools.quarantine`
  - global default thresholds with per-category overrides
- `tools.mcp.control_plane`
  - registration, discovery, approval, descriptor promotion, and health state
- `tools.transports.prompt_emulated`
  - current prompt-rendering and parsing boundary
- `tools.transports.native_base`
  - future provider-native adapter boundary

## MCP rollout model

Two MCP scopes now exist under the same control plane:

- `admin_global`
  - registrations must be explicitly trusted
  - discovered tools require approval before descriptor promotion
  - approved and trusted tools default to normal runtime allow, subject to policy/quarantine
- `guild`
  - registrations are stored in the global DB keyed by `guild_id`
  - discovered tools require approval before descriptor promotion
  - approved tools default to descriptor policy `deny` until a guild admin explicitly allows them via tool/category policy

MCP server health is tracked in `mcp_server_health`.

Current health behavior:

- discovery status and errors are recorded
- call status and errors are recorded
- transport failures create a temporary cooldown
- cooldown blocks runtime availability and is visible in admin inspection/health output

## Admin surfaces

`/tools` now includes:

- `status`
- `inspect`
- `policy set-category`
- `policy clear-category`
- `policy set-tool`
- `policy clear-tool`
- `debug raw-capture-status`
- `debug raw-capture-enable`
- `debug raw-capture-disable`
- `quarantine status`
- `quarantine clear`
- `mcp list-registrations`
- `mcp list-tools`
- `mcp health`
- `mcp register-global`
- `mcp trust-global`
- `mcp enable-global`
- `mcp discover-global`
- `mcp approve-global`
- `mcp register-guild`
- `mcp enable-guild`
- `mcp discover-guild`
- `mcp approve-guild`

Owner-only intent:

- admin-global MCP commands are reserved for the bot owner

Guild-admin intent:

- guild-scoped MCP commands are for guild administrators
- allowing approved guild MCP tools happens through the normal tool policy commands

## Logging and safety defaults

Execution logging is privacy-safe by default:

- structured metadata is always stored
- argument/result summaries are redacted/summarized by default
- raw argument/result capture is disabled by default
- raw capture requires temporary admin enablement and expires

## Native adapter boundary

Native provider tool calling is not active.

The explicit boundary now exists so providers can later add native tool-definition rendering and tool-call parsing without changing:

- descriptor modeling
- policy evaluation
- availability resolution
- execution
- audit/quarantine behavior
