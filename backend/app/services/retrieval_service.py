"""Retrieval service with multi-tenant isolation.

Design:
- Filters by tenant_id (multi-tenancy enforcement)
- Assumes embeddings already exist in Milvus
"""

import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalQuery:
    tenant_id: str
    query_text: str = ""
    top_k: int = 6


async def retrieve_chunks(
    query: RetrievalQuery,
    embedding_provider,
) -> list[dict]:
    """Retrieve chunks from Milvus with tenant isolation.

    Step 1: Embed query text to 1024-dim vector
    Step 2: Search Milvus with tenant_id filter
    Step 3: Return top_k results sorted by score
    """
    from app.services.milvus_store import ensure_collection_exists, get_milvus_client

    if not query.tenant_id:
        raise ValueError("tenant_id is mandatory")

    try:
        query_embeddings = await embedding_provider.embed_batch([query.query_text])
        query_vector = query_embeddings[0]
    except Exception as e:
        logger.error(f"query_embedding_failed: {e}")
        raise ValueError(f"Could not embed query: {e}") from e

    filter_expr = f"tenant_id == '{query.tenant_id}'"

    try:
        client = get_milvus_client()
        ensure_collection_exists(client)

        results = client.search(
            collection_name=settings.milvus_collection_name,
            data=[query_vector],
            filter=filter_expr,
            limit=query.top_k,
            output_fields=[
                "chunk_id",
                "title",
                "body_text",
                "document_id",
            ],
        )

        rows = []
        for result in results[0]:
            rows.append({
                "chunk_id": result["chunk_id"],
                "title": result.get("title"),
                "body_text": result.get("body_text"),
                "document_id": result.get("document_id"),
                "score": result.get("distance", result.get("_distance", 0)),
            })

    except Exception as e:
        logger.error(f"milvus_search_failed: {e}")
        raise ValueError(f"Milvus search failed: {e}") from e

    logger.info(
        "retrieval_complete",
        extra={
            "tenant_id": query.tenant_id,
            "retrieved_count": len(rows),
        },
    )

    return rows
