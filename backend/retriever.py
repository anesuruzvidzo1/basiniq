import asyncio
from sentence_transformers import SentenceTransformer, CrossEncoder
from sqlalchemy import text
from db import AsyncSessionLocal


async def bm25_search(query: str, top_k: int = 20) -> list[dict]:
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT id, chunk_text, document_name, chunk_index, page_number
                    FROM document_chunks, websearch_to_tsquery('english', :query) q
                    WHERE to_tsvector('english', chunk_text) @@ q
                    ORDER BY ts_rank_cd(to_tsvector('english', chunk_text), q) DESC
                    LIMIT :limit
                """),
                {"query": query, "limit": top_k},
            )
            rows = result.fetchall()
        return [
            {
                "pg_chunk_id": row.id,
                "chunk_text": row.chunk_text,
                "document_name": row.document_name,
                "chunk_index": row.chunk_index,
                "page_number": row.page_number or 1,
            }
            for row in rows
        ]
    except Exception:
        return []


async def dense_search(query: str, bi_encoder: SentenceTransformer, top_k: int = 20) -> list[dict]:
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, lambda: bi_encoder.encode(query).tolist())
    embedding_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, chunk_text, document_name, chunk_index, page_number
                FROM document_chunks
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            {"embedding": embedding_str, "limit": top_k},
        )
        rows = result.fetchall()

    return [
        {
            "pg_chunk_id": row.id,
            "chunk_text": row.chunk_text,
            "document_name": row.document_name,
            "chunk_index": row.chunk_index,
            "page_number": row.page_number or 1,
        }
        for row in rows
    ]


def reciprocal_rank_fusion(
    bm25_results: list[dict], dense_results: list[dict], k: int = 60
) -> list[dict]:
    scores: dict[int, float] = {}
    chunks: dict[int, dict] = {}

    for rank, result in enumerate(bm25_results):
        pid = result["pg_chunk_id"]
        scores[pid] = scores.get(pid, 0.0) + 1 / (k + rank + 1)
        chunks[pid] = result

    for rank, result in enumerate(dense_results):
        pid = result["pg_chunk_id"]
        scores[pid] = scores.get(pid, 0.0) + 1 / (k + rank + 1)
        chunks[pid] = result

    ranked_ids = sorted(scores, key=lambda pid: scores[pid], reverse=True)
    return [chunks[pid] for pid in ranked_ids]


async def rerank(
    query: str, candidates: list[dict], cross_encoder: CrossEncoder, top_n: int = 5
) -> list[dict]:
    if not candidates:
        return []
    pairs = [(query, c["chunk_text"]) for c in candidates]
    loop = asyncio.get_event_loop()
    scores = await loop.run_in_executor(None, lambda: cross_encoder.predict(pairs))
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked[:top_n]]


async def hybrid_search(
    query: str,
    bi_encoder: SentenceTransformer,
    cross_encoder: CrossEncoder,
    top_k: int = 20,
    top_n: int = 5,
) -> list[dict]:
    bm25_results, dense_results = await asyncio.gather(
        bm25_search(query, top_k),
        dense_search(query, bi_encoder, top_k),
    )
    fused = reciprocal_rank_fusion(bm25_results, dense_results)
    return await rerank(query, fused[:top_k], cross_encoder, top_n)
