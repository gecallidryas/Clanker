from __future__ import annotations

import os
from typing import Optional

try:
    import asyncpg
    from pgvector.asyncpg import register_vector
except ModuleNotFoundError:  # pragma: no cover - exercised in test environments without pg deps
    asyncpg = None
    register_vector = None

from utils.logger import get_logger

logger = get_logger(__name__)

_pool: Optional["asyncpg.Pool"] = None
_schema_ready = False


def _build_dsn() -> Optional[str]:
    host = os.getenv("POSTGRES_HOST")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB")
    if not host or not user or not db_name:
        return None
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql://{user}:{password or ''}@{host}:{port}/{db_name}"


async def _init_connection(conn: "asyncpg.Connection") -> None:
    if register_vector is None:
        return
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await register_vector(conn)


async def get_pg_pool() -> Optional["asyncpg.Pool"]:
    global _pool
    if _pool is not None:
        return _pool
    if asyncpg is None:
        return None
    dsn = _build_dsn()
    if not dsn:
        return None
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5, init=_init_connection)
    return _pool


async def ensure_pg_schema() -> bool:
    global _schema_ready
    if _schema_ready:
        return True
    if asyncpg is None:
        return False
    pool = await get_pg_pool()
    if pool is None:
        return False
    embed_dim = int(os.getenv("RAG_EMBEDDING_DIM", "1536"))
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                title TEXT,
                source TEXT,
                content_hash TEXT,
                uploader_id BIGINT,
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                guild_id BIGINT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR({embed_dim}),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS document_chunks_guild_idx ON document_chunks (guild_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS document_chunks_doc_idx ON document_chunks (document_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx "
            "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )
    _schema_ready = True
    return True
