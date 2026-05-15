"""RAG 检索节点

从 Milvus 向量数据库检索相关文本块，基于 tenant_id 和查询文本。
"""

import asyncio
from datetime import datetime
from typing import Any

from app.graph.state import SocraticState
from app.services.retrieval_service import RetrievalQuery, retrieve_chunks


def retrieve_node(state: SocraticState) -> dict[str, Any]:
    """检索节点：从 Milvus 获取相关文本块。"""
    from app.services.embedding_service import get_embedding_provider

    trace_log = list(state.get("trace_log", []))

    try:
        query = RetrievalQuery(
            tenant_id=state.get("tenant_id", "local-dev"),
            query_text=state.get("retrieval_query") or "generate quiz context",
            top_k=5,
        )
        provider = get_embedding_provider()
        retrieved_chunks = asyncio.run(retrieve_chunks(query, provider))
        error_message = None if retrieved_chunks else "No relevant content found"
    except Exception as e:
        retrieved_chunks = []
        error_message = f"Retrieval failed: {str(e)}"

    trace_log.append({
        "node": "retrieve",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {
            "chunks_retrieved": len(retrieved_chunks),
            "error": error_message,
        },
    })

    return {
        "retrieved_chunks": retrieved_chunks,
        "trace_log": trace_log,
        "error_message": error_message,
    }
