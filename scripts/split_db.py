#!/usr/bin/env python
"""
Split a legacy single SQLite DB into per-guild DBs plus a global stats DB.
"""

import argparse
import asyncio
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


def _chunked(values: List[int], size: int = 900) -> Iterable[List[int]]:
    for i in range(0, len(values), size):
        yield values[i:i + size]


def _get_tables(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def _get_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return column in _get_columns(conn, table)


def _select_common_columns(
    src_conn: sqlite3.Connection,
    dst_conn: sqlite3.Connection,
    table: str,
) -> List[str]:
    src_cols = _get_columns(src_conn, table)
    dst_cols = _get_columns(dst_conn, table)
    return [col for col in src_cols if col in dst_cols]


def _copy_rows(
    src_conn: sqlite3.Connection,
    dst_conn: sqlite3.Connection,
    table: str,
    columns: List[str],
    where: str,
    params: Tuple,
    guild_id_override: int | None = None,
) -> int:
    if not columns:
        return 0
    select_cols = []
    override_params: Tuple = ()
    for col in columns:
        if col == "guild_id" and guild_id_override is not None:
            select_cols.append(
                "CASE WHEN guild_id IS NULL OR guild_id = 0 THEN ? ELSE guild_id END AS guild_id"
            )
            override_params = (guild_id_override,)
        else:
            select_cols.append(col)
    col_list = ", ".join(select_cols)
    placeholders = ", ".join(["?"] * len(columns))
    rows = src_conn.execute(
        f"SELECT {col_list} FROM {table} WHERE {where}",
        (*override_params, *params),
    ).fetchall()
    if not rows:
        return 0
    dst_conn.executemany(
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
        rows,
    )
    return len(rows)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Split legacy DB into per-guild DBs")
    parser.add_argument("--legacy", default=None, help="Path to legacy database.db")
    parser.add_argument("--out-dir", default=None, help="Directory for per-guild DBs")
    parser.add_argument("--global", dest="global_db", default=None, help="Global DB path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing guild DBs")
    parser.add_argument(
        "--default-guild-id",
        type=int,
        default=None,
        help="Assign legacy rows with guild_id 0/NULL to this guild ID",
    )
    args = parser.parse_args()

    # Ensure discord_bot is on sys.path for utils import
    root_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root_dir / "discord_bot"))

    # Resolve paths via env for db_handler
    if args.out_dir:
        os.environ["DATABASE_DIR"] = args.out_dir
    if args.global_db:
        os.environ["GLOBAL_DATABASE_PATH"] = args.global_db
    if args.legacy:
        legacy_path = Path(args.legacy).expanduser()
    else:
        legacy_env = os.getenv("LEGACY_DATABASE_PATH") or os.getenv("DATABASE_PATH")
        legacy_path = Path(legacy_env or (Path(__file__).resolve().parents[1] / "discord_bot" / "database.db"))

    if not legacy_path.exists():
        raise SystemExit(f"Legacy DB not found: {legacy_path}")

    # Import db_handler after env vars are set
    from utils import db_handler

    await db_handler.init_db()

    src_conn = sqlite3.connect(str(legacy_path))
    src_conn.row_factory = sqlite3.Row

    tables = _get_tables(src_conn)
    tables = [t for t in tables if t not in ("sqlite_sequence",)]

    guild_ids: Set[int] = set()
    legacy_guildless = 0
    for table in tables:
        if _table_has_column(src_conn, table, "guild_id"):
            rows = src_conn.execute(
                f"SELECT DISTINCT guild_id FROM {table} WHERE guild_id IS NOT NULL"
            ).fetchall()
            for row in rows:
                gid = row[0]
                if gid and int(gid) != 0:
                    guild_ids.add(int(gid))
                elif gid in (0, None):
                    legacy_guildless += 1

    if args.default_guild_id and legacy_guildless:
        guild_ids.add(args.default_guild_id)

    if not guild_ids:
        raise SystemExit("No guild_id values found in legacy DB.")

    # Copy bot_stats to global db if present
    if "bot_stats" in tables:
        with sqlite3.connect(db_handler.GLOBAL_DATABASE_PATH) as global_conn:
            global_conn.row_factory = sqlite3.Row
            columns = _select_common_columns(src_conn, global_conn, "bot_stats")
            if columns:
                rows = src_conn.execute(
                    f"SELECT {', '.join(columns)} FROM bot_stats WHERE id = 1"
                ).fetchall()
                if rows:
                    placeholders = ", ".join(["?"] * len(columns))
                    global_conn.execute(
                        f"DELETE FROM bot_stats WHERE id = 1"
                    )
                    global_conn.executemany(
                        f"INSERT INTO bot_stats ({', '.join(columns)}) VALUES ({placeholders})",
                        rows,
                    )
                    global_conn.commit()

    # Build user sets per guild
    guild_users: Dict[int, Set[int]] = {gid: set() for gid in guild_ids}
    for table in tables:
        if not _table_has_column(src_conn, table, "guild_id"):
            continue
        columns = _get_columns(src_conn, table)
        user_cols = [c for c in columns if c.endswith("user_id")]
        if not user_cols:
            continue
        for gid in guild_ids:
            match_guild = gid
            include_guildless = args.default_guild_id == gid and legacy_guildless
            for col in user_cols:
                if include_guildless:
                    rows = src_conn.execute(
                        f"SELECT DISTINCT {col} FROM {table} WHERE (guild_id = ? OR guild_id IS NULL OR guild_id = 0) AND {col} IS NOT NULL",
                        (match_guild,),
                    ).fetchall()
                else:
                    rows = src_conn.execute(
                        f"SELECT DISTINCT {col} FROM {table} WHERE guild_id = ? AND {col} IS NOT NULL",
                        (match_guild,),
                    ).fetchall()
                for row in rows:
                    if row[0]:
                        guild_users[gid].add(int(row[0]))

    # Create and populate per-guild DBs
    for gid in sorted(guild_ids):
        target_path = Path(db_handler.get_guild_db_path(gid))
        if target_path.exists():
            if args.overwrite:
                target_path.unlink()
            else:
                print(f"Skipping existing DB for guild {gid}: {target_path}")
                continue

        await db_handler.init_guild_db(gid)

        with sqlite3.connect(str(target_path)) as dst_conn:
            dst_conn.row_factory = sqlite3.Row
            for table in tables:
                if table in ("bot_stats", "guild_registry"):
                    continue

                if _table_has_column(src_conn, table, "guild_id"):
                    columns = _select_common_columns(src_conn, dst_conn, table)
                    if not columns:
                        continue
                    include_guildless = args.default_guild_id == gid and legacy_guildless
                    if include_guildless:
                        where = "guild_id = ? OR guild_id IS NULL OR guild_id = 0"
                        count = _copy_rows(
                            src_conn,
                            dst_conn,
                            table,
                            columns,
                            where,
                            (gid,),
                            guild_id_override=gid,
                        )
                    elif table == "reminders":
                        count = _copy_rows(
                            src_conn,
                            dst_conn,
                            table,
                            columns,
                            "guild_id = ? AND guild_id IS NOT NULL",
                            (gid,),
                        )
                    else:
                        count = _copy_rows(
                            src_conn,
                            dst_conn,
                            table,
                            columns,
                            "guild_id = ?",
                            (gid,),
                        )
                    if count:
                        dst_conn.commit()
                    continue

                if table == "users":
                    columns = _select_common_columns(src_conn, dst_conn, table)
                    if not columns:
                        continue
                    user_ids = sorted(guild_users.get(gid, set()))
                    if not user_ids:
                        continue
                    for chunk in _chunked(user_ids):
                        placeholders = ", ".join(["?"] * len(chunk))
                        rows = src_conn.execute(
                            f"SELECT {', '.join(columns)} FROM users WHERE user_id IN ({placeholders})",
                            tuple(chunk),
                        ).fetchall()
                        if rows:
                            dst_conn.executemany(
                                f"INSERT INTO users ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
                                rows,
                            )
                    dst_conn.commit()

    if legacy_guildless and not args.default_guild_id:
        print(
            "Warning: legacy rows with guild_id 0/NULL were skipped. "
            "Re-run with --default-guild-id to assign them."
        )
    print(f"Split complete. Guild DBs: {len(guild_ids)}")
    print(f"Global DB: {db_handler.GLOBAL_DATABASE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
