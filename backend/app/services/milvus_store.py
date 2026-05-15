"""Milvus vector store access layer."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_milvus_client():
    from pymilvus import MilvusClient

    return MilvusClient(uri=settings.milvus_uri, token=settings.milvus_token or None)


def ensure_collection_exists(client) -> None:
    from pymilvus import CollectionSchema, DataType, FieldSchema

    collection_name = settings.milvus_collection_name

    if client.has_collection(collection_name):
        return

    schema = CollectionSchema(
        fields=[
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
            FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64, is_partition_key=True),
            FieldSchema(name="document_id", dtype=DataType.INT32),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=255, nullable=True),
            FieldSchema(name="body_text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="embedding_version", dtype=DataType.VARCHAR, max_length=32, default_value="1.0"),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
        ],
        description="Knowledge chunks with 1024-dim vectors",
    )

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params={
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 48, "efConstruction": 500},
        },
    )
    logger.info(f"Created Milvus collection: {collection_name}")


async def upsert_chunk_with_embedding(
    client,
    chunk_id: str,
    tenant_id: str,
    document_id: int,
    body_text: str,
    embedding: list[float],
    title: str | None = None,
) -> None:
    ensure_collection_exists(client)

    data = {
        "chunk_id": [chunk_id],
        "tenant_id": [tenant_id],
        "document_id": [document_id],
        "title": [title],
        "body_text": [body_text],
        "embedding_version": ["1.0"],
        "dense_vector": [embedding],
    }

    try:
        client.upsert(collection_name=settings.milvus_collection_name, data=data)
        logger.info("milvus_upsert_success", extra={"chunk_id": chunk_id})
    except Exception as e:
        logger.error("milvus_upsert_failed", extra={"chunk_id": chunk_id, "error": str(e)})
        raise
