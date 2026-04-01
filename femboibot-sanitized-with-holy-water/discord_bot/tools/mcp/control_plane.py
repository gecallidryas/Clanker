from __future__ import annotations

import json
import os
import shlex
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import aiosqlite

from tools.categories import normalize_tool_category
from tools.contracts import (
    ToolDescriptor,
    ToolPolicyMode,
    ToolScopeType,
    ToolSourceType,
    ToolTrustRequirement,
)
from tools.mcp import manager
from tools.registry import get_tool_registry
from utils.db_handler import global_db


ADMIN_GLOBAL_SCOPE = "admin_global"
GUILD_SCOPE = "guild"
VALID_SCOPES = {ADMIN_GLOBAL_SCOPE, GUILD_SCOPE}
MCP_DEFAULT_COOLDOWN_SECONDS = 60


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_scope(scope_type: str, guild_id: Optional[int] = None) -> tuple[str, int]:
    normalized = str(scope_type or ADMIN_GLOBAL_SCOPE).strip().lower()
    if normalized not in VALID_SCOPES:
        raise ValueError(f"Unsupported MCP scope: {scope_type}")
    normalized_guild_id = int(guild_id or 0)
    if normalized == GUILD_SCOPE and normalized_guild_id <= 0:
        raise ValueError("guild-scoped MCP registrations require guild_id")
    if normalized == ADMIN_GLOBAL_SCOPE:
        return normalized, 0
    return normalized, normalized_guild_id


def _normalize_server_slug(server_slug: str) -> str:
    normalized = str(server_slug or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not normalized:
        raise ValueError("server_slug is required.")
    return normalized


def _parse_command(command_line: str) -> list[str]:
    parts = shlex.split(command_line or "", posix=os.name != "nt")
    if not parts:
        raise ValueError("command_line is required.")
    return parts


def _normalize_input_schema(input_schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(input_schema, dict) or not input_schema:
        return {"type": "object", "properties": {}, "additionalProperties": False}
    normalized = dict(input_schema)
    normalized.setdefault("type", "object")
    properties = normalized.get("properties")
    if not isinstance(properties, dict):
        normalized["properties"] = {}
    normalized.setdefault("additionalProperties", False)
    return normalized


def _tool_id_for(scope_type: str, guild_id: int, server_slug: str, remote_tool_name: str) -> str:
    if scope_type == ADMIN_GLOBAL_SCOPE:
        return f"mcp:admin_global:{server_slug}:{remote_tool_name}"
    return f"mcp:guild:{guild_id}:{server_slug}:{remote_tool_name}"


def _source_ref_for(server_slug: str, remote_tool_name: str) -> str:
    return f"{server_slug}:{remote_tool_name}"


def _descriptor_from_mcp_row(row: dict[str, Any]) -> ToolDescriptor:
    scope_type = row["scope_type"]
    guild_id = int(row["guild_id"] or 0)
    server_slug = row["server_slug"]
    remote_tool_name = row["remote_tool_name"]
    category = row["category"] or "uncategorized"
    tool_id = _tool_id_for(scope_type, guild_id, server_slug, remote_tool_name)
    default_policy_mode = ToolPolicyMode.ALLOW if scope_type == ADMIN_GLOBAL_SCOPE else ToolPolicyMode.DENY
    trust_requirement = (
        ToolTrustRequirement.EXPLICIT_TRUST
        if scope_type == ADMIN_GLOBAL_SCOPE
        else ToolTrustRequirement.DISCOVERY_APPROVAL
    )
    return ToolDescriptor(
        tool_id=tool_id,
        public_name=row["public_name"],
        description=row["description"] or row["remote_tool_name"],
        display_name=row["display_name"] or row["public_name"],
        source_type=ToolSourceType.MCP,
        source_ref=_source_ref_for(server_slug, remote_tool_name),
        scope_type=ToolScopeType.ADMIN_GLOBAL if scope_type == ADMIN_GLOBAL_SCOPE else ToolScopeType.GUILD,
        guild_id=guild_id or None,
        category=category,
        input_schema=_normalize_input_schema(json.loads(row["input_schema_json"] or "{}")),
        supports_model_invocation=True,
        supports_manual_invocation=True,
        default_policy_mode=default_policy_mode,
        trust_requirement=trust_requirement,
    )


async def register_mcp_server(
    *,
    scope_type: str,
    guild_id: Optional[int] = None,
    server_slug: str,
    command_line: str,
    env: Optional[dict[str, str]] = None,
    trusted: Optional[bool] = None,
    enabled: bool = True,
    actor_id: Optional[int] = None,
    note: Optional[str] = None,
) -> dict[str, Any]:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    command = _parse_command(command_line)
    effective_trusted = bool(trusted) if trusted is not None else (normalized_scope == GUILD_SCOPE)
    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO mcp_server_registrations
                (scope_type, guild_id, server_slug, transport_type, command_json, env_json, trusted, enabled, note, created_by, updated_by)
            VALUES (?, ?, ?, 'stdio', ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, guild_id, server_slug)
            DO UPDATE SET
                command_json = excluded.command_json,
                env_json = excluded.env_json,
                trusted = excluded.trusted,
                enabled = excluded.enabled,
                note = excluded.note,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                normalized_scope,
                normalized_guild_id,
                normalized_slug,
                json.dumps(command, ensure_ascii=True),
                json.dumps(env or {}, ensure_ascii=True, sort_keys=True),
                int(effective_trusted),
                int(bool(enabled)),
                note,
                actor_id,
                actor_id,
            ),
        )
        await db.commit()
    return {
        "scope_type": normalized_scope,
        "guild_id": normalized_guild_id,
        "server_slug": normalized_slug,
        "command": command,
        "trusted": effective_trusted,
        "enabled": bool(enabled),
    }


async def register_admin_global_mcp_server(
    *,
    server_slug: str,
    command_line: str,
    env: Optional[dict[str, str]] = None,
    trusted: bool = False,
    enabled: bool = True,
    actor_id: Optional[int] = None,
    note: Optional[str] = None,
) -> dict[str, Any]:
    return await register_mcp_server(
        scope_type=ADMIN_GLOBAL_SCOPE,
        server_slug=server_slug,
        command_line=command_line,
        env=env,
        trusted=trusted,
        enabled=enabled,
        actor_id=actor_id,
        note=note,
    )


async def register_guild_mcp_server(
    *,
    guild_id: int,
    server_slug: str,
    command_line: str,
    env: Optional[dict[str, str]] = None,
    trusted: bool = True,
    enabled: bool = True,
    actor_id: Optional[int] = None,
    note: Optional[str] = None,
) -> dict[str, Any]:
    return await register_mcp_server(
        scope_type=GUILD_SCOPE,
        guild_id=guild_id,
        server_slug=server_slug,
        command_line=command_line,
        env=env,
        trusted=trusted,
        enabled=enabled,
        actor_id=actor_id,
        note=note,
    )


async def list_mcp_registrations(*, scope_type: str = ADMIN_GLOBAL_SCOPE, guild_id: Optional[int] = None) -> list[dict[str, Any]]:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM mcp_server_registrations
            WHERE scope_type = ? AND guild_id = ?
            ORDER BY server_slug ASC
            """,
            (normalized_scope, normalized_guild_id),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_mcp_registration(
    *,
    scope_type: str,
    guild_id: Optional[int] = None,
    server_slug: str,
) -> Optional[dict[str, Any]]:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    rows = await list_mcp_registrations(scope_type=normalized_scope, guild_id=normalized_guild_id)
    for row in rows:
        if row["server_slug"] == normalized_slug:
            return row
    return None


async def get_admin_global_registration(server_slug: str) -> Optional[dict[str, Any]]:
    return await get_mcp_registration(scope_type=ADMIN_GLOBAL_SCOPE, server_slug=server_slug)


async def set_mcp_registration_trust(
    *,
    server_slug: str,
    trusted: bool,
    scope_type: str = ADMIN_GLOBAL_SCOPE,
    guild_id: Optional[int] = None,
    actor_id: Optional[int] = None,
) -> None:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    async with global_db() as db:
        await db.execute(
            """
            UPDATE mcp_server_registrations
            SET trusted = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE scope_type = ? AND guild_id = ? AND server_slug = ?
            """,
            (int(bool(trusted)), actor_id, normalized_scope, normalized_guild_id, normalized_slug),
        )
        await db.commit()
    await refresh_mcp_descriptors(scope_type=normalized_scope, guild_id=normalized_guild_id)


async def set_mcp_registration_enabled(
    *,
    server_slug: str,
    enabled: bool,
    scope_type: str = ADMIN_GLOBAL_SCOPE,
    guild_id: Optional[int] = None,
    actor_id: Optional[int] = None,
) -> None:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    async with global_db() as db:
        await db.execute(
            """
            UPDATE mcp_server_registrations
            SET enabled = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE scope_type = ? AND guild_id = ? AND server_slug = ?
            """,
            (int(bool(enabled)), actor_id, normalized_scope, normalized_guild_id, normalized_slug),
        )
        await db.commit()
    await refresh_mcp_descriptors(scope_type=normalized_scope, guild_id=normalized_guild_id)


async def _record_discovery_health(
    *,
    scope_type: str,
    guild_id: int,
    server_slug: str,
    status: str,
    error: Optional[str],
) -> None:
    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO mcp_server_health (scope_type, guild_id, server_slug, last_discovery_status, last_discovery_error, last_discovery_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(scope_type, guild_id, server_slug)
            DO UPDATE SET
                last_discovery_status = excluded.last_discovery_status,
                last_discovery_error = excluded.last_discovery_error,
                last_discovery_at = CURRENT_TIMESTAMP
            """,
            (scope_type, guild_id, server_slug, status, error),
        )
        await db.commit()


async def record_mcp_call_health(
    *,
    scope_type: str,
    guild_id: Optional[int] = None,
    server_slug: str,
    status: str,
    error: Optional[str] = None,
    cooldown_seconds: int = MCP_DEFAULT_COOLDOWN_SECONDS,
) -> None:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    cooldown_until = None
    if status != "ok":
        cooldown_until = (datetime.now(timezone.utc) + timedelta(seconds=max(0, int(cooldown_seconds)))).isoformat()
    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO mcp_server_health
                (scope_type, guild_id, server_slug, last_call_status, last_call_error, last_call_at, cooldown_until)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(scope_type, guild_id, server_slug)
            DO UPDATE SET
                last_call_status = excluded.last_call_status,
                last_call_error = excluded.last_call_error,
                last_call_at = CURRENT_TIMESTAMP,
                cooldown_until = excluded.cooldown_until
            """,
            (normalized_scope, normalized_guild_id, normalized_slug, status, error, cooldown_until),
        )
        await db.commit()


async def list_mcp_server_health(*, scope_type: Optional[str] = None, guild_id: Optional[int] = None) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if scope_type:
        normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
        clauses.append("scope_type = ? AND guild_id = ?")
        params.extend([normalized_scope, normalized_guild_id])
    elif guild_id:
        clauses.append("guild_id = ?")
        params.append(int(guild_id))
    where_clause = " AND ".join(f"({clause})" for clause in clauses) if clauses else "1 = 1"
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT *
            FROM mcp_server_health
            WHERE {where_clause}
            ORDER BY scope_type ASC, guild_id ASC, server_slug ASC
            """,
            params,
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_mcp_health(
    *,
    scope_type: str,
    guild_id: Optional[int] = None,
    server_slug: str,
) -> Optional[dict[str, Any]]:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    rows = await list_mcp_server_health(scope_type=normalized_scope, guild_id=normalized_guild_id)
    for row in rows:
        if row["server_slug"] == normalized_slug:
            return row
    return None


async def discover_mcp_tools(
    *,
    server_slug: str,
    scope_type: str = ADMIN_GLOBAL_SCOPE,
    guild_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    registration = await get_mcp_registration(
        scope_type=normalized_scope,
        guild_id=normalized_guild_id,
        server_slug=normalized_slug,
    )
    if registration is None:
        raise ValueError(f"Unknown MCP server `{server_slug}`.")

    command = json.loads(registration["command_json"])
    env = json.loads(registration["env_json"] or "{}")
    try:
        discovered = await manager.list_tools(command=command, env=env)
        status = "ok"
        error = None
    except Exception as exc:
        discovered = []
        status = "error"
        error = str(exc)

    await _record_discovery_health(
        scope_type=normalized_scope,
        guild_id=normalized_guild_id,
        server_slug=normalized_slug,
        status=status,
        error=error,
    )

    async with global_db() as db:
        for tool in discovered:
            remote_tool_name = tool["name"]
            await db.execute(
                """
                INSERT INTO mcp_discovered_tools
                    (scope_type, guild_id, server_slug, remote_tool_name, public_name, display_name, description, input_schema_json, category, approved, discovered_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'uncategorized', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(scope_type, guild_id, server_slug, remote_tool_name)
                DO UPDATE SET
                    description = excluded.description,
                    input_schema_json = excluded.input_schema_json,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (
                    normalized_scope,
                    normalized_guild_id,
                    normalized_slug,
                    remote_tool_name,
                    remote_tool_name,
                    remote_tool_name,
                    tool["description"],
                    json.dumps(tool["inputSchema"], ensure_ascii=True, sort_keys=True),
                ),
            )
        await db.commit()

    if error:
        raise RuntimeError(error)
    return discovered


async def list_mcp_tools(
    *,
    server_slug: Optional[str] = None,
    approved_only: bool = False,
    scope_type: str = ADMIN_GLOBAL_SCOPE,
    guild_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    clauses = ["scope_type = ? AND guild_id = ?"]
    params: list[Any] = [normalized_scope, normalized_guild_id]
    if server_slug:
        clauses.append("server_slug = ?")
        params.append(_normalize_server_slug(server_slug))
    if approved_only:
        clauses.append("approved = 1")

    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT *
            FROM mcp_discovered_tools
            WHERE {' AND '.join(clauses)}
            ORDER BY server_slug ASC, remote_tool_name ASC
            """,
            params,
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def approve_mcp_tool(
    *,
    server_slug: str,
    remote_tool_name: str,
    category: str,
    public_name: Optional[str] = None,
    actor_id: Optional[int] = None,
    scope_type: str = ADMIN_GLOBAL_SCOPE,
    guild_id: Optional[int] = None,
) -> None:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    normalized_slug = _normalize_server_slug(server_slug)
    normalized_category = normalize_tool_category(category)
    tools = await list_mcp_tools(
        server_slug=normalized_slug,
        approved_only=False,
        scope_type=normalized_scope,
        guild_id=normalized_guild_id,
    )
    row = next((item for item in tools if item["remote_tool_name"] == remote_tool_name), None)
    if row is None:
        raise ValueError(f"Unknown discovered MCP tool `{remote_tool_name}`.")

    registry = get_tool_registry()
    chosen_public_name = (public_name or remote_tool_name).strip()
    existing = registry.resolve_descriptor(chosen_public_name)
    target_tool_id = _tool_id_for(normalized_scope, normalized_guild_id, normalized_slug, remote_tool_name)
    if existing is not None and existing.tool_id != target_tool_id:
        chosen_public_name = f"mcp_{normalized_slug}_{remote_tool_name}".strip()

    async with global_db() as db:
        await db.execute(
            """
            UPDATE mcp_discovered_tools
            SET approved = 1,
                approved_by = ?,
                approved_at = CURRENT_TIMESTAMP,
                category = ?,
                public_name = ?,
                display_name = COALESCE(display_name, ?)
            WHERE scope_type = ? AND guild_id = ? AND server_slug = ? AND remote_tool_name = ?
            """,
            (
                actor_id,
                normalized_category,
                chosen_public_name,
                chosen_public_name,
                normalized_scope,
                normalized_guild_id,
                normalized_slug,
                remote_tool_name,
            ),
        )
        await db.commit()

    await refresh_mcp_descriptors(scope_type=normalized_scope, guild_id=normalized_guild_id)


async def refresh_mcp_descriptors(*, scope_type: str, guild_id: Optional[int] = None) -> None:
    normalized_scope, normalized_guild_id = _normalize_scope(scope_type, guild_id)
    registry = get_tool_registry()
    prefix = "mcp:admin_global:" if normalized_scope == ADMIN_GLOBAL_SCOPE else f"mcp:guild:{normalized_guild_id}:"
    registry.remove_descriptors_by_prefix(prefix)
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT dt.*, reg.trusted, reg.enabled
            FROM mcp_discovered_tools dt
            JOIN mcp_server_registrations reg
              ON reg.scope_type = dt.scope_type
             AND reg.guild_id = dt.guild_id
             AND reg.server_slug = dt.server_slug
            WHERE dt.scope_type = ?
              AND dt.guild_id = ?
              AND dt.approved = 1
              AND reg.trusted = 1
              AND reg.enabled = 1
            ORDER BY dt.server_slug ASC, dt.remote_tool_name ASC
            """,
            (normalized_scope, normalized_guild_id),
        ) as cursor:
            rows = await cursor.fetchall()
    for row in rows:
        registry.register_descriptor(_descriptor_from_mcp_row(dict(row)))


async def refresh_admin_global_mcp_descriptors() -> None:
    await refresh_mcp_descriptors(scope_type=ADMIN_GLOBAL_SCOPE)


async def refresh_guild_mcp_descriptors(guild_id: int) -> None:
    await refresh_mcp_descriptors(scope_type=GUILD_SCOPE, guild_id=guild_id)


async def refresh_all_mcp_descriptors() -> None:
    await refresh_admin_global_mcp_descriptors()

    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT DISTINCT guild_id
            FROM mcp_server_registrations
            WHERE scope_type = ? AND guild_id > 0
            ORDER BY guild_id ASC
            """,
            (GUILD_SCOPE,),
        ) as cursor:
            guild_rows = await cursor.fetchall()
    for row in guild_rows:
        await refresh_guild_mcp_descriptors(int(row["guild_id"]))


async def get_mcp_runtime_metadata(descriptor: ToolDescriptor) -> dict[str, Any]:
    if descriptor.source_type != ToolSourceType.MCP:
        raise ValueError("Descriptor is not an MCP tool.")
    source_ref = str(descriptor.source_ref or "")
    if ":" not in source_ref:
        raise ValueError("Descriptor source_ref is invalid.")
    server_slug, remote_tool_name = source_ref.split(":", 1)
    scope_type = ADMIN_GLOBAL_SCOPE if descriptor.scope_type == ToolScopeType.ADMIN_GLOBAL else GUILD_SCOPE
    guild_id = descriptor.guild_id if scope_type == GUILD_SCOPE else 0
    registration = await get_mcp_registration(
        scope_type=scope_type,
        guild_id=guild_id,
        server_slug=server_slug,
    )
    health = await get_mcp_health(
        scope_type=scope_type,
        guild_id=guild_id,
        server_slug=server_slug,
    )
    return {
        "scope_type": scope_type,
        "guild_id": int(guild_id or 0),
        "server_slug": server_slug,
        "remote_tool_name": remote_tool_name,
        "registration": registration,
        "health": health,
    }


__all__ = [
    "ADMIN_GLOBAL_SCOPE",
    "GUILD_SCOPE",
    "approve_mcp_tool",
    "discover_mcp_tools",
    "get_admin_global_registration",
    "get_mcp_health",
    "get_mcp_registration",
    "get_mcp_runtime_metadata",
    "list_mcp_registrations",
    "list_mcp_server_health",
    "list_mcp_tools",
    "record_mcp_call_health",
    "refresh_admin_global_mcp_descriptors",
    "refresh_all_mcp_descriptors",
    "refresh_guild_mcp_descriptors",
    "refresh_mcp_descriptors",
    "register_admin_global_mcp_server",
    "register_guild_mcp_server",
    "register_mcp_server",
    "set_mcp_registration_enabled",
    "set_mcp_registration_trust",
]
