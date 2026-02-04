from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from utils.logger import get_logger
from utils.pg_client import ensure_pg_schema, get_pg_pool
from utils.rag_documents import chunk_text, hash_content
from utils.rag_embeddings import embed_texts

logger = get_logger(__name__)


async def store_document(
    guild_id: int,
    title: str,
    source: str,
    text: str,
    uploader_id: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> tuple[int, int]:
    ready = await ensure_pg_schema()
    if not ready:
        raise RuntimeError("Postgres is not configured.")
    chunks = chunk_text(
        text,
        chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "800")),
        overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "100")),
    )
    if not chunks:
        raise RuntimeError("No chunks extracted from document.")
    embeddings = await embed_texts(guild_id, chunks)
    if len(embeddings) != len(chunks):
        raise RuntimeError("Embedding count mismatch.")

    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Postgres pool not available.")

    content_hash = hash_content(text)
    async with pool.acquire() as conn:
        async with conn.transaction():
            doc_id = await conn.fetchval(
                """
                INSERT INTO documents (guild_id, title, source, content_hash, uploader_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                guild_id,
                title,
                source,
                content_hash,
                uploader_id,
                metadata or {},
            )
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                await conn.execute(
                    """
                    INSERT INTO document_chunks (document_id, guild_id, chunk_index, content, embedding)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    doc_id,
                    guild_id,
                    idx,
                    chunk,
                    embedding,
                )
    return doc_id, len(chunks)


async def delete_document(guild_id: int, document_id: int) -> bool:
    pool = await get_pg_pool()
    if pool is None:
        return False
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM documents WHERE id = $1 AND guild_id = $2",
            document_id,
            guild_id,
        )
        return result.endswith("DELETE 1")


async def query_similar_chunks(
    guild_id: int,
    embedding: List[float],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    pool = await get_pg_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT content, document_id, chunk_index,
                   1 - (embedding <=> $1) AS score
            FROM document_chunks
            WHERE guild_id = $2
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            embedding,
            guild_id,
            top_k,
        )
    return [dict(row) for row in rows]


async def get_rag_context(guild_id: int, query: str, top_k: int = 5) -> str:
    if not query.strip():
        return ""
    ready = await ensure_pg_schema()
    if not ready:
        return ""
    embeddings = await embed_texts(guild_id, [query])
    if not embeddings:
        return ""
    chunks = await query_similar_chunks(guild_id, embeddings[0], top_k=top_k)
    if not chunks:
        return ""
    lines = []
    for item in chunks:
        score = item.get("score")
        content = item.get("content")
        if content:
            lines.append(f"- ({score:.2f}) {content}")
    return "\n".join(lines)
