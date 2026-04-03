from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

import aiosqlite

from tools.categories import normalize_tool_category
from tools.contracts import ToolDescriptor, ToolPolicyMode
from utils.db_handler import get_staff_roles, global_db


POLICY_SCOPE_GLOBAL = "global"
POLICY_SCOPE_GUILD = "guild"
POLICY_SUBJECT_CATEGORY = "category"
POLICY_SUBJECT_TOOL = "tool"
VALID_POLICY_SCOPES = {POLICY_SCOPE_GLOBAL, POLICY_SCOPE_GUILD}
VALID_POLICY_SUBJECTS = {POLICY_SUBJECT_CATEGORY, POLICY_SUBJECT_TOOL}


@dataclass(slots=True, frozen=True)
class ToolPolicyRule:
    subject_type: str
    subject_id: str
    policy_mode: ToolPolicyMode
    scope_type: str = POLICY_SCOPE_GLOBAL
    guild_id: int = 0
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    note: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ResolvedToolPolicy:
    tool_id: str
    public_name: str
    category: str
    effective_mode: ToolPolicyMode
    matched_rule: Optional[ToolPolicyRule]
    source: str


def normalize_policy_scope(scope_type: str, guild_id: Optional[int] = None) -> tuple[str, int]:
    normalized_scope = str(scope_type or POLICY_SCOPE_GLOBAL).strip().lower()
    if normalized_scope not in VALID_POLICY_SCOPES:
        raise ValueError(f"Unsupported policy scope: {scope_type}")
    normalized_guild_id = int(guild_id or 0)
    if normalized_scope == POLICY_SCOPE_GLOBAL:
        return normalized_scope, 0
    if normalized_guild_id <= 0:
        raise ValueError("guild-scoped policy rules require a guild_id")
    return normalized_scope, normalized_guild_id


def normalize_policy_subject(subject_type: str, subject_id: str) -> tuple[str, str]:
    normalized_type = str(subject_type or "").strip().lower()
    if normalized_type not in VALID_POLICY_SUBJECTS:
        raise ValueError(f"Unsupported policy subject type: {subject_type}")
    normalized_id = str(subject_id or "").strip()
    if not normalized_id:
        raise ValueError("Policy subject_id must be non-empty.")
    if normalized_type == POLICY_SUBJECT_CATEGORY:
        normalized_id = normalize_tool_category(normalized_id)
    return normalized_type, normalized_id


def _coerce_policy_mode(policy_mode: ToolPolicyMode | str) -> ToolPolicyMode:
    if isinstance(policy_mode, ToolPolicyMode):
        return policy_mode
    normalized = str(policy_mode or "").strip().lower()
    try:
        return ToolPolicyMode(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported policy mode: {policy_mode}") from exc


def _serialize_metadata(metadata: Optional[dict[str, Any]]) -> str:
    return json.dumps(metadata or {}, ensure_ascii=True, sort_keys=True)


def _deserialize_metadata(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _row_to_policy_rule(row: Any) -> ToolPolicyRule:
    return ToolPolicyRule(
        subject_type=row["subject_type"],
        subject_id=row["subject_id"],
        policy_mode=_coerce_policy_mode(row["policy_mode"]),
        scope_type=row["scope_type"],
        guild_id=int(row["guild_id"] or 0),
        created_by=row["created_by"],
        updated_by=row["updated_by"],
        note=row["note"],
        metadata=_deserialize_metadata(row["metadata_json"]),
    )


async def upsert_tool_policy_rule(
    *,
    subject_type: str,
    subject_id: str,
    policy_mode: ToolPolicyMode | str,
    guild_id: Optional[int] = None,
    scope_type: str = POLICY_SCOPE_GLOBAL,
    actor_id: Optional[int] = None,
    note: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ToolPolicyRule:
    normalized_scope, normalized_guild_id = normalize_policy_scope(scope_type, guild_id)
    normalized_type, normalized_id = normalize_policy_subject(subject_type, subject_id)
    normalized_mode = _coerce_policy_mode(policy_mode)
    metadata_json = _serialize_metadata(metadata)

    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO tool_policy_rules
                (scope_type, guild_id, subject_type, subject_id, policy_mode, note, metadata_json, created_by, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, guild_id, subject_type, subject_id)
            DO UPDATE SET
                policy_mode = excluded.policy_mode,
                note = excluded.note,
                metadata_json = excluded.metadata_json,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                normalized_scope,
                normalized_guild_id,
                normalized_type,
                normalized_id,
                normalized_mode.value,
                note,
                metadata_json,
                actor_id,
                actor_id,
            ),
        )
        await db.execute(
            """
            INSERT INTO tool_policy_audit
                (scope_type, guild_id, subject_type, subject_id, policy_mode, actor_id, note, metadata_json, action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_scope,
                normalized_guild_id,
                normalized_type,
                normalized_id,
                normalized_mode.value,
                actor_id,
                note,
                metadata_json,
                "upsert",
            ),
        )
        await db.commit()

    return ToolPolicyRule(
        subject_type=normalized_type,
        subject_id=normalized_id,
        policy_mode=normalized_mode,
        scope_type=normalized_scope,
        guild_id=normalized_guild_id,
        created_by=actor_id,
        updated_by=actor_id,
        note=note,
        metadata=metadata or {},
    )


async def delete_tool_policy_rule(
    *,
    subject_type: str,
    subject_id: str,
    guild_id: Optional[int] = None,
    scope_type: str = POLICY_SCOPE_GLOBAL,
    actor_id: Optional[int] = None,
    note: Optional[str] = None,
) -> bool:
    normalized_scope, normalized_guild_id = normalize_policy_scope(scope_type, guild_id)
    normalized_type, normalized_id = normalize_policy_subject(subject_type, subject_id)

    async with global_db() as db:
        cursor = await db.execute(
            """
            DELETE FROM tool_policy_rules
            WHERE scope_type = ? AND guild_id = ? AND subject_type = ? AND subject_id = ?
            """,
            (normalized_scope, normalized_guild_id, normalized_type, normalized_id),
        )
        removed = cursor.rowcount > 0
        if removed:
            await db.execute(
                """
                INSERT INTO tool_policy_audit
                    (scope_type, guild_id, subject_type, subject_id, actor_id, note, action)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_scope,
                    normalized_guild_id,
                    normalized_type,
                    normalized_id,
                    actor_id,
                    note,
                    "delete",
                ),
            )
        await db.commit()
    return removed


async def list_tool_policy_rules(
    *,
    guild_id: Optional[int] = None,
    include_global: bool = False,
) -> list[ToolPolicyRule]:
    clauses = []
    params: list[Any] = []
    normalized_guild_id = int(guild_id or 0)

    if include_global and normalized_guild_id > 0:
        clauses.append("(scope_type = ? AND guild_id = 0 OR scope_type = ? AND guild_id = ?)")
        params.extend([POLICY_SCOPE_GLOBAL, POLICY_SCOPE_GUILD, normalized_guild_id])
    elif normalized_guild_id > 0:
        clauses.append("scope_type = ? AND guild_id = ?")
        params.extend([POLICY_SCOPE_GUILD, normalized_guild_id])
    else:
        clauses.append("scope_type = ? AND guild_id = 0")
        params.append(POLICY_SCOPE_GLOBAL)

    where_clause = " AND ".join(f"({clause})" for clause in clauses) if clauses else "1 = 1"

    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT *
            FROM tool_policy_rules
            WHERE {where_clause}
            ORDER BY
                CASE subject_type WHEN 'tool' THEN 0 ELSE 1 END,
                CASE scope_type WHEN 'guild' THEN 0 ELSE 1 END,
                subject_id ASC
            """,
            params,
        ) as cursor:
            rows = await cursor.fetchall()
    return [_row_to_policy_rule(row) for row in rows]


async def resolve_tool_policy(
    descriptor: ToolDescriptor,
    *,
    guild_id: Optional[int] = None,
) -> ResolvedToolPolicy:
    rules = await list_tool_policy_rules(guild_id=guild_id, include_global=True)
    return resolve_tool_policy_from_rules(descriptor, rules=rules, guild_id=guild_id)


def resolve_tool_policy_from_rules(
    descriptor: ToolDescriptor,
    *,
    rules: list[ToolPolicyRule],
    guild_id: Optional[int] = None,
) -> ResolvedToolPolicy:

    precedence: list[tuple[str, str, str, int]] = []
    if guild_id:
        precedence.extend(
            [
                (POLICY_SCOPE_GUILD, POLICY_SUBJECT_TOOL, descriptor.tool_id, int(guild_id)),
                (POLICY_SCOPE_GUILD, POLICY_SUBJECT_CATEGORY, descriptor.category, int(guild_id)),
            ]
        )
    precedence.extend(
        [
            (POLICY_SCOPE_GLOBAL, POLICY_SUBJECT_TOOL, descriptor.tool_id, 0),
            (POLICY_SCOPE_GLOBAL, POLICY_SUBJECT_CATEGORY, descriptor.category, 0),
        ]
    )

    for scope_type, subject_type, subject_id, rule_guild_id in precedence:
        for rule in rules:
            if (
                rule.scope_type == scope_type
                and rule.subject_type == subject_type
                and rule.subject_id == subject_id
                and rule.guild_id == rule_guild_id
            ):
                return ResolvedToolPolicy(
                    tool_id=descriptor.tool_id,
                    public_name=descriptor.public_name,
                    category=descriptor.category,
                    effective_mode=rule.policy_mode,
                    matched_rule=rule,
                    source=f"{scope_type}:{subject_type}",
                )

    return ResolvedToolPolicy(
        tool_id=descriptor.tool_id,
        public_name=descriptor.public_name,
        category=descriptor.category,
        effective_mode=descriptor.default_policy_mode,
        matched_rule=None,
        source="descriptor_default",
    )


async def user_qualifies_for_admin_only(member: Any) -> bool:
    if not member or not getattr(member, "guild", None):
        return False
    permissions = getattr(member, "guild_permissions", None)
    if permissions and bool(getattr(permissions, "administrator", False)):
        return True

    roles = getattr(member, "roles", None) or []
    role_ids = {int(getattr(role, "id", 0)) for role in roles if getattr(role, "id", None) is not None}
    if not role_ids:
        return False

    staff_roles = await get_staff_roles(int(member.guild.id))
    highest_level = max((int(level) for _role_id, level in staff_roles), default=0)
    required_level = max(2, highest_level if highest_level >= 2 else 0)
    if required_level < 2:
        return False
    return any(int(level) >= required_level and int(role_id) in role_ids for role_id, level in staff_roles)
