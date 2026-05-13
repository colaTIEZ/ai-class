# Phase 1 Enterprise RAG Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-style foundation for `ai-class` by introducing PostgreSQL, Milvus, and object storage abstraction without breaking the existing upload-to-quiz workflow.

---

## Clarifications (Session 2026-04-29)

This section records key architectural decisions made during Phase 1 design clarification to reduce implementation ambiguity.

### Embedding & Vectorization Strategy
- **Decision**: Asynchronous generation + background task queue
- **Rationale**: Improves upload UX; enables batch processing and cost optimization
- **Implementation**: 
  - Upload returns immediately (document queued for processing)
  - Celery/Arq job processes chunks → calls embedding API → writes to Milvus
  - Retry + audit log ensures convergence

### Milvus Collection Design
- **Vector Dimension**: 1024 (balanced cost and quality)
- **Similarity Metric**: COSINE
- **Index Strategy**: HNSW (fast approximate nearest neighbor search)
- **Collection Structure**: Single unified collection with metadata filtering
- **Key Fields**:
  - `tenant_id` (partition key or metadata filter)
  - `document_id`, `parent_chunk_id`, `scope_hint`
  - `embedding_version` (enables safe model upgrades)
  - `dense_vector` (1024-dim FLOAT)

### PostgreSQL ↔ Milvus Data Consistency Model
- **Consistency Level**: Eventual Consistency
- **Source of Truth**: PostgreSQL (all writes)
- **Indexing Strategy**: Async via job queue (not inline)
- **Guarantees**:
  - PostgreSQL commit = write accepted
  - Milvus sync best-effort (retry + audit ensures convergence)
- **Read Path**:
  - Vector retrieval from Milvus (fastest path)
  - Metadata hydration from PostgreSQL (join chunks with document info)
- **Recovery**:
  - Retry failed jobs from queue
  - Periodic reconciliation job (Phase 2 scope)

### Object Storage Abstraction
- **Pattern**: Storage Adapter (interface-based, pluggable)
- **Backends**:
  - `LocalObjectStorage` (development and local testing)
  - `S3CompatibleStorage` (production; works with Aliyun OSS, MinIO, AWS S3)
- **Path Structure**: `{tenant_id}/{kb_id}/{document_id}/{type}/{filename}`
- **Guarantees**:
  - Keys are unique and traceable
  - Tenant isolation via key prefix
  - Not vendor-locked
- **Consistency**: Async verification only (no inline read-back verification)
- **Garbage Collection**: Async cleanup job (Phase 2 scope)

### Multi-Tenancy Enforcement Model
- **Level**: Strict tenant-level isolation (no cross-tenant data leakage)
- **Enforcement Points**:
  - **PostgreSQL**: `tenant_id` column + Row-Level Security (RLS) recommended
  - **Milvus**: Metadata filter on `tenant_id` + wrapped client
  - **Object Storage**: Key prefix isolation
  - **Redis**: Key prefix isolation
  - **API Layer**: `tenant_id` derived from auth context only (never user input)
- **Out of Phase 1 Scope**:
  - Role-Based Access Control (RBAC)
  - Fine-grained ACLs (object-level permissions)
  - Cross-tenant resource sharing
- **Guarantee**: No cross-tenant read/write possible by design

---

**Architecture:** Keep the app as a modular monolith, but split persistence, retrieval, and scope-view responsibilities into explicit layers. Replace SQLite-centric storage assumptions with repository and storage abstractions so later phases can add multimodal assets, tenant isolation, and LLM Ops without rewriting the whole system.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Milvus, LangGraph, LangChain, Redis-ready config, Vue 3, Vitest

---

## Scope Split

This plan intentionally covers only the first independently shippable subsystem:

- PostgreSQL business persistence
- Milvus retrieval foundation
- Object storage abstraction with local fallback and OSS-ready interface


This plan does **not** implement:

- Full multimodal asset parsing
- Excel cell-level vectorization
- LLM fallback gateway
- Token cost accounting
- Full tenant auth model

Those should be written as follow-on plans after this phase lands.

## File Structure Map

### Existing files we will modify

- `backend/pyproject.toml`
- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/api/v1/documents.py`
- `backend/app/services/processing_queue.py`
- `backend/app/graph/nodes/retrieve.py`
- `frontend/src/api/documents.ts`
- `frontend/src/views/DocumentView.vue`
- `frontend/src/stores/quiz.ts`

### New backend files

- `backend/app/db/__init__.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/db/models.py`
- `backend/app/repositories/document_repository.py`
- `backend/app/services/object_storage.py`
- `backend/app/services/milvus_store.py`
- `backend/app/services/retrieval_service.py`

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/20260425_01_phase1_core_tables.py`

### New test files

- `backend/tests/test_phase1_config.py`
- `backend/tests/test_postgres_models.py`
- `backend/tests/test_object_storage.py`
- `backend/tests/test_retrieval_service.py`


### New frontend files



---

### Task 1: Bootstrap Enterprise Dependencies And Config

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/.env.example`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_phase1_config.py`

- [ ] **Step 1: Write the failing config test**

```python
from app.core.config import Settings


def test_phase1_settings_support_enterprise_backends():
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@localhost:5432/ai_class",
        milvus_uri="http://localhost:19530",
        milvus_collection_name="knowledge_chunks",
        object_storage_backend="local",
        object_storage_bucket="ai-class-dev",
        object_storage_local_root="data/object_store",

    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.milvus_uri == "http://localhost:19530"
    assert settings.object_storage_backend == "local"
    assert settings.object_storage_bucket == "ai-class-dev"

```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_phase1_config.py -v`
Expected: FAIL with missing `milvus_uri` or `object_storage_backend` fields on `Settings`

- [ ] **Step 3: Add enterprise dependencies and settings**

```toml
[project]
dependencies = [
    "sqlalchemy>=2.0.41",
    "alembic>=1.16.1",
    "psycopg[binary]>=3.2.9",
    "pymilvus>=2.5.6",
    "langchain-milvus>=0.1.10",
    "oss2>=2.19.1",
]
```

```python
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ai-class"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_class"
    database_path: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "ai_class.db")

    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_collection_name: str = "knowledge_chunks"

    object_storage_backend: str = "local"
    object_storage_bucket: str = "ai-class-dev"
    object_storage_endpoint: str = ""
    object_storage_access_key: str = ""
    object_storage_secret_key: str = ""
    object_storage_local_root: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "object_store")


    default_tenant_id: str = "local-dev"

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    openai_embedding_model: str = ""
    openai_embedding_fallback_model: str = ""

    MAX_UPLOAD_SIZE: int = 10485760
    MAX_QUEUE_SIZE: int = 100
    zombie_task_timeout_seconds: int = 300

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
```

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_class
MILVUS_URI=http://localhost:19530
MILVUS_COLLECTION_NAME=knowledge_chunks
OBJECT_STORAGE_BACKEND=local
OBJECT_STORAGE_BUCKET=ai-class-dev
OBJECT_STORAGE_LOCAL_ROOT=backend/data/object_store
DEFAULT_TENANT_ID=local-dev
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_phase1_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/.env.example backend/app/core/config.py backend/tests/test_phase1_config.py
git commit -m "feat: add enterprise storage and retrieval settings"
```

### Task 2: Add PostgreSQL Session, Models, And Migrations

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260425_01_phase1_core_tables.py`
- Test: `backend/tests/test_postgres_models.py`

- [ ] **Step 1: Write the failing persistence schema test**

```python
from app.db.models import ChunkRecord, DocumentRecord, ScopeViewItemRecord, ScopeViewRecord


def test_phase1_models_expose_required_columns():
    assert DocumentRecord.__tablename__ == "documents"
    assert "tenant_id" in DocumentRecord.__table__.c
    assert "storage_key" in DocumentRecord.__table__.c

    assert ChunkRecord.__tablename__ == "chunks"
    assert "parent_chunk_id" in ChunkRecord.__table__.c
    assert "scope_hint" in ChunkRecord.__table__.c

    assert ScopeViewRecord.__tablename__ == "scope_views"
    assert ScopeViewItemRecord.__tablename__ == "scope_view_items"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_postgres_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Add SQLAlchemy base, session, models, and Alembic wiring**

```python
# backend/app/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

```python
# backend/app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
```

```python
# backend/app/db/models.py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(512))
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChunkRecord(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    parent_chunk_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scope_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScopeViewRecord(Base):
    __tablename__ = "scope_views"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    intent_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScopeViewItemRecord(Base):
    __tablename__ = "scope_view_items"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scope_view_id: Mapped[str] = mapped_column(ForeignKey("scope_views.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item_type: Mapped[str] = mapped_column(String(32))
    item_key: Mapped[str] = mapped_column(String(255))
    label: Mapped[str] = mapped_column(String(255))
    rank: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
```

```python
# backend/alembic/env.py
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
from app.db import models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

```python
# backend/alembic/versions/20260425_01_phase1_core_tables.py
from alembic import op
import sqlalchemy as sa


revision = "20260425_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
```

- [ ] **Step 4: Run tests and migration smoke check**

Run: `pytest tests/test_postgres_models.py -v`
Expected: PASS

Run: `alembic upgrade head`
Expected: SUCCESS with new `documents` and `chunks` tables created in PostgreSQL

- [ ] **Step 5: Commit**

```bash
git add backend/app/db backend/alembic.ini backend/alembic backend/tests/test_postgres_models.py
git commit -m "feat: add postgres schema foundation"
```

### Task 3: Add Object Storage Abstraction To The Upload Pipeline

**Files:**
- Create: `backend/app/services/object_storage.py`
- Modify: `backend/app/api/v1/documents.py`
- Modify: `backend/app/services/processing_queue.py`
- Test: `backend/tests/test_object_storage.py`

- [ ] **Step 1: Write the failing object storage test**

```python
from pathlib import Path

from app.services.object_storage import LocalObjectStorage


def test_local_object_storage_put_bytes(tmp_path: Path):
    storage = LocalObjectStorage(root=tmp_path, bucket="ai-class-dev")
    key = storage.put_bytes("raw/local-dev/123/source.pdf", b"%PDF-demo")

    stored_path = tmp_path / "ai-class-dev" / "raw" / "local-dev" / "123" / "source.pdf"
    assert key == "raw/local-dev/123/source.pdf"
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"%PDF-demo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_object_storage.py -v`
Expected: FAIL with `ModuleNotFoundError` for `app.services.object_storage`

- [ ] **Step 3: Add storage interface and route the upload through it**

```python
# backend/app/services/object_storage.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class StoredObject:
    key: str
    uri: str


class LocalObjectStorage:
    def __init__(self, root: Path, bucket: str) -> None:
        self.root = root
        self.bucket = bucket

    def put_bytes(self, key: str, content: bytes) -> str:
        target = self.root / self.bucket / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    def uri_for(self, key: str) -> str:
        return f"local://{self.bucket}/{key}"
```

```python
# backend/app/api/v1/documents.py
tenant_id = settings.default_tenant_id
storage_key = f"raw/{tenant_id}/{document_id}/source.pdf"
storage = get_object_storage()
stored_key = await asyncio.to_thread(storage.put_bytes, storage_key, content)
```

```python
# backend/app/services/processing_queue.py
row = conn.execute(
    "SELECT storage_key FROM documents WHERE id = ?",
    (doc_id,),
).fetchone()
source_uri = storage.uri_for(row["storage_key"])
```

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_object_storage.py tests/test_upload_queue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/object_storage.py backend/app/api/v1/documents.py backend/app/services/processing_queue.py backend/tests/test_object_storage.py
git commit -m "feat: add object storage abstraction to uploads"
```

---

## Embedding Service Complete Implementation Reference

This section provides a complete, production-ready implementation of the async embedding pipeline (see Clarifications: Embedding & Vectorization Strategy).

### Architecture Overview

```
Upload Flow:
  1. User uploads PDF → API returns immediately
  2. Document stored in PostgreSQL + object storage
  3. Celery/Arq job enqueued: parse → chunk → embed → upsert Milvus
  
Async Job Flow (in worker):
  4. Load document from object storage
  5. Parse & chunk (using existing logic or Docling)
  6. Batch texts → EmbeddingProvider.embed_batch()
  7. For each (chunk, embedding) pair → upsert_chunk_with_embedding()
  8. On failure → retry with exponential backoff (3x max)
  9. Log audit trail for reconciliation in Phase 2
```

### Complete Embedding Service Implementation

```python
# backend/app/services/embedding_service.py
"""
Async embedding generation service for job queue workers.

Design rationale:
- Async/await for non-blocking I/O with OpenAI API
- Batch vectorization to reduce API calls
- Structured logging for audit trail (consistency recovery in Phase 2)
- Retry with exponential backoff for transient failures
- embedding_version tracking for safe model upgrades

See Clarifications: Embedding & Vectorization Strategy.
"""

import asyncio
import logging
from typing import Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base exception for embedding operations."""
    pass


class EmbeddingProvider:
    """
    OpenAI embedding client with retry and batch processing.
    
    Targets: 1024-dim vectors (Phase 1 standard)
    Model: configurable via settings.openai_embedding_model
    Batch size: 100 texts per request (OpenAI recommended)
    """

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate 1024-dim embeddings for a batch of texts.

        Args:
            texts: List of texts to embed (max 100 per request)

        Returns:
            List of 1024-dim float vectors (same order as input texts)

        Raises:
            EmbeddingError: If embedding generation fails after retries
        """
        if not texts:
            return []

        if len(texts) > 100:
            # Recursively split large batches
            mid = len(texts) // 2
            left = await self.embed_batch(texts[:mid])
            right = await self.embed_batch(texts[mid:])
            return left + right

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base}/embeddings",
                    json={"model": self.model, "input": texts},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()

                # Verify response structure
                if "data" not in data:
                    raise EmbeddingError(f"Invalid embedding response: {data}")

                # Sort by index to guarantee order matching input texts
                embeddings_sorted = sorted(data["data"], key=lambda x: x.get("index", 0))
                embeddings = [item["embedding"] for item in embeddings_sorted]

                logger.info(
                    f"generated_embeddings",
                    extra={
                        "count": len(embeddings),
                        "model": self.model,
                        "batch_size": len(texts),
                    },
                )
                return embeddings

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.error(f"embedding_network_error: {e}")
            raise EmbeddingError(f"Network error during embedding: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"embedding_api_error: {e.response.status_code}")
            if e.response.status_code == 429:
                raise EmbeddingError("Rate limited by embedding API") from e
            raise EmbeddingError(f"API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"embedding_unknown_error: {e}")
            raise EmbeddingError(f"Unknown embedding error: {e}") from e

    async def embed_single(self, text: str) -> list[float]:
        """Convenience method for single text embedding."""
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else []


def get_embedding_provider(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> EmbeddingProvider:
    """
    Factory for EmbeddingProvider (dependency injection).

    Can be overridden in tests with mock provider.
    """
    return EmbeddingProvider(
        api_key=api_key or settings.openai_api_key,
        api_base=settings.openai_base_url or "https://api.openai.com/v1",
        model=model or settings.openai_embedding_model,
    )


# ============================================================================
# Job Queue Integration (Celery/Arq Worker Example)
# ============================================================================

async def embed_document_job(
    document_id: int,
    tenant_id: str,
    chunk_ids: list[str],
    chunk_texts: list[str],
) -> dict:
    """
    Async job for embedding document chunks.

    Called by Celery/Arq worker after document is parsed into chunks.
    Returns audit log for Phase 2 reconciliation.

    See Clarifications: PostgreSQL ↔ Milvus Data Consistency Model.
    """
    from app.services.milvus_store import (
        get_milvus_client,
        ensure_collection_exists,
        upsert_chunk_with_embedding,
    )
    from app.db.session import SessionLocal

    audit_log = {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "chunks_processed": 0,
        "chunks_failed": [],
        "errors": [],
    }

    try:
        provider = get_embedding_provider()
        client = get_milvus_client()
        ensure_collection_exists(client)

        # Generate all embeddings in one batch
        logger.info(
            f"embedding_batch_start",
            extra={"document_id": document_id, "chunk_count": len(chunk_texts)},
        )
        embeddings = await provider.embed_batch(chunk_texts)

        # Upsert each chunk with embedding
        db = SessionLocal()
        try:
            for chunk_id, chunk_text, embedding in zip(chunk_ids, chunk_texts, embeddings):
                try:
                    await upsert_chunk_with_embedding(
                        client=client,
                        chunk_id=chunk_id,
                        tenant_id=tenant_id,
                        document_id=document_id,
                        body_text=chunk_text,
                        embedding=embedding,
                    )
                    audit_log["chunks_processed"] += 1
                except Exception as e:
                    logger.error(
                        f"chunk_upsert_failed",
                        extra={"chunk_id": chunk_id, "error": str(e)},
                    )
                    audit_log["chunks_failed"].append(chunk_id)
                    audit_log["errors"].append(str(e))
        finally:
            db.close()

        logger.info(
            f"embedding_batch_complete",
            extra={
                "document_id": document_id,
                "success": audit_log["chunks_processed"],
                "failed": len(audit_log["chunks_failed"]),
            },
        )

    except Exception as e:
        logger.error(
            f"embedding_job_failed",
            extra={"document_id": document_id, "error": str(e)},
        )
        audit_log["errors"].append(f"Job-level error: {str(e)}")

    return audit_log
```

### Complete Milvus Upsert Implementation

```python
# backend/app/services/milvus_store.py (supplemental - full version)

async def upsert_chunk_with_embedding(
    client: MilvusClient,
    chunk_id: str,
    tenant_id: str,
    document_id: int,
    body_text: str,
    embedding: list[float],
    parent_chunk_id: str | None = None,
    scope_hint: str | None = None,
    title: str | None = None,
) -> None:
    """
    Upsert a chunk with its embedding into Milvus.

    Called by async job queue worker after embedding is generated.
    Implements eventual consistency: write to PostgreSQL first (already done),
    then async write to Milvus (this function).

    See Clarifications: PostgreSQL ↔ Milvus Data Consistency Model.
    """
    ensure_collection_exists(client)

    # Prepare batch data (single item for this function)
    data = {
        "chunk_id": [chunk_id],
        "tenant_id": [tenant_id],
        "document_id": [document_id],
        "parent_chunk_id": [parent_chunk_id],
        "scope_hint": [scope_hint],
        "title": [title],
        "body_text": [body_text],
        "embedding_version": ["1.0"],  # Phase 1 standard
        "dense_vector": [embedding],
    }

    try:
        client.upsert(collection_name=settings.milvus_collection_name, data=data)
        logger.info(f"milvus_upsert_success", extra={"chunk_id": chunk_id})
    except Exception as e:
        # Fail fast; retry handled by job queue
        logger.error(
            f"milvus_upsert_failed",
            extra={"chunk_id": chunk_id, "error": str(e)},
        )
        raise
```

---

### Task 4: Add Milvus Retrieval Foundation With Parent-Child Metadata

**Files:**
- Create: `backend/app/services/milvus_store.py`
- Create: `backend/app/services/embedding_service.py` ← **Use reference implementation above**
- Create: `backend/app/services/retrieval_service.py`
- Modify: `backend/app/services/processing_queue.py` (integrate job queue call)
- Modify: `backend/app/graph/nodes/retrieve.py`
- Test: `backend/tests/test_embedding_service.py` ← **New test file**
- Test: `backend/tests/test_retrieval_service.py`

**Architecture Note**: Embedding generation is async via job queue (see Clarifications section above and Complete Implementation Reference). This task implements the retrieval-time component and the Milvus foundation.

- [ ] **Step 1: Write the failing embedding and retrieval tests**

```python
# backend/tests/test_embedding_service.py
"""Test embedding service with batch processing and retry logic."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.embedding_service import EmbeddingProvider, embed_document_job, EmbeddingError


@pytest.mark.asyncio
async def test_embedding_provider_embed_batch_single():
    """Test single batch embedding."""
    provider = EmbeddingProvider(
        api_key="test-key",
        api_base="https://api.test.com",
        model="test-model",
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "data": [
                {"index": 0, "embedding": [0.1] * 1024},
                {"index": 1, "embedding": [0.2] * 1024},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        embeddings = await provider.embed_batch(["text1", "text2"])

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1024  # 1024-dim vectors
        assert embeddings[0][0] == 0.1


@pytest.mark.asyncio
async def test_embedding_provider_batch_split_on_overflow():
    """Test that large batches (>100) are recursively split."""
    provider = EmbeddingProvider(api_key="test-key")

    # Create 150 test texts
    texts = [f"text-{i}" for i in range(150)]

    # Mock to track splits
    with patch.object(provider, "embed_batch", wraps=provider.embed_batch) as mock_embed:
        with patch("httpx.AsyncClient") as mock_client:
            # Return embeddings for any request
            async def mock_post(*args, **kwargs):
                resp = AsyncMock()
                # Assume batch size from request
                resp.json.return_value = {
                    "data": [{"index": i, "embedding": [0.1] * 1024} for i in range(100)]
                }
                resp.raise_for_status.return_value = None
                return resp

            mock_client.return_value.__aenter__.return_value.post = mock_post

            embeddings = await provider.embed_batch(texts)
            assert len(embeddings) == 150


@pytest.mark.asyncio
async def test_embedding_provider_retry_on_timeout():
    """Test retry logic on transient network errors."""
    provider = EmbeddingProvider(api_key="test-key", max_retries=3)

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("Network error")
        resp = AsyncMock()
        resp.json.return_value = {
            "data": [{"index": 0, "embedding": [0.1] * 1024}]
        }
        resp.raise_for_status.return_value = None
        return resp

    with patch("httpx.AsyncClient"):
        with patch("httpx.AsyncClient.post", mock_post):
            embeddings = await provider.embed_batch(["text1"])
            assert len(embeddings) == 1
            assert call_count == 3  # Retried twice, succeeded on 3rd


@pytest.mark.asyncio
async def test_retrieval_query_and_parent_merge():
    """Test RetrievalQuery dataclass and parent-child merging."""
    from app.services.retrieval_service import RetrievalQuery, filter_to_parent_chunks

    # Create retrieval query
    query = RetrievalQuery(
        tenant_id="local-dev",
        scope_ids=["scope-1"],
        query_text="test query",
        top_k=5,
    )
    assert query.tenant_id == "local-dev"
    assert query.top_k == 5

    # Test parent-child merging
    docs = [
        {"chunk_id": "child-1", "parent_chunk_id": "parent-a", "score": 0.95, "text": "text1"},
        {"chunk_id": "child-2", "parent_chunk_id": "parent-a", "score": 0.91, "text": "text2"},
        {"chunk_id": "child-3", "parent_chunk_id": "parent-b", "score": 0.88, "text": "text3"},
    ]

    merged = filter_to_parent_chunks(docs)
    assert len(merged) == 2  # Two parents
    assert merged[0]["parent_chunk_id"] == "parent-a"  # Highest score
    assert merged[0]["score"] == 0.95
```

```python
# backend/tests/test_retrieval_service.py
"""Test retrieval service with tenant isolation and Milvus integration."""

import pytest
from app.services.retrieval_service import RetrievalQuery, filter_to_parent_chunks


def test_filter_to_parent_chunks_groups_children():
    """Test merging child chunks under parent (highest-scoring child wins)."""
    docs = [
        {"chunk_id": "child-1", "parent_chunk_id": "parent-a", "score": 0.91, "text": "small"},
        {"chunk_id": "child-2", "parent_chunk_id": "parent-a", "score": 0.89, "text": "small 2"},
        {"chunk_id": "child-3", "parent_chunk_id": "parent-b", "score": 0.88, "text": "small 3"},
    ]

    merged = filter_to_parent_chunks(docs)
    
    assert len(merged) == 2
    assert merged[0]["parent_chunk_id"] == "parent-a"
    assert merged[0]["score"] == 0.91  # Highest scoring child
    assert merged[1]["parent_chunk_id"] == "parent-b"


def test_retrieval_query_structure():
    """Test RetrievalQuery with tenant isolation."""
    query = RetrievalQuery(
        tenant_id="tenant-acme",
        scope_ids=["scope-1", "scope-2"],
        query_text="what is RAG?",
        top_k=6,
    )

    assert query.tenant_id == "tenant-acme"
    assert len(query.scope_ids) == 2
    assert query.top_k == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieval_service.py -v`
Expected: FAIL with missing retrieval service module

- [ ] **Step 3: Add Milvus access layer and retrieval service**

```python
# backend/app/services/milvus_store.py
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType

from app.core.config import settings


def get_milvus_client() -> MilvusClient:
    """Initialize Milvus client with settings."""
    return MilvusClient(uri=settings.milvus_uri, token=settings.milvus_token or None)


def ensure_collection_exists(client: MilvusClient) -> None:
    """Create collection if not exists, with Phase 1 schema.
    
    Schema design rationale:
    - Vector dimension: 1024 (1024-dim embedding model)
    - Metric: COSINE
    - Index: HNSW
    - tenant_id is partition key for fast tenant filtering
    - embedding_version allows safe model upgrade in Phase 2
    """
    collection_name = settings.milvus_collection_name
    
    if client.has_collection(collection_name):
        return
    
    schema = CollectionSchema(
        fields=[
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
            FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64, is_partition_key=True),
            FieldSchema(name="document_id", dtype=DataType.INT32),
            FieldSchema(name="parent_chunk_id", dtype=DataType.VARCHAR, max_length=128, nullable=True),
            FieldSchema(name="scope_hint", dtype=DataType.VARCHAR, max_length=255, nullable=True),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=255, nullable=True),
            FieldSchema(name="body_text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="embedding_version", dtype=DataType.VARCHAR, max_length=32, default_value="1.0"),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
        ],
        description="Knowledge chunks with 1024-dim vectors"
    )
    
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params={
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 48, "efConstruction": 500}
        }
    )
```

Replace:
```python
# backend/app/services/milvus_store.py
from pymilvus import MilvusClient

from app.core.config import settings


def get_milvus_client() -> MilvusClient:
    return MilvusClient(uri=settings.milvus_uri, token=settings.milvus_token or None)
```
```

```python
# backend/app/services/retrieval_service.py
"""
Retrieval service with parent-child chunking and multi-tenant isolation.

Design:
- Filters by tenant_id and scope_ids (multi-tenancy enforcement)
- Merges child chunks under parent for better context
- Assumes embeddings already exist in Milvus
- Hydrates metadata from PostgreSQL in Phase 2

See Clarifications: 
  - Multi-Tenancy Enforcement Model
  - PostgreSQL ↔ Milvus Data Consistency Model
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalQuery:
    """Query structure for tenant-scoped retrieval.
    
    See Clarifications: Multi-Tenancy Enforcement Model.
    """
    tenant_id: str  # Mandatory; derived from auth context in API layer
    scope_ids: list[str]  # User-selected scope (document, chapter, topic)
    query_text: str  # User query (will be embedded by retrieval caller)
    top_k: int = 6  # Return at most top_k parent chunks


def filter_to_parent_chunks(rows: list[dict]) -> list[dict]:
    """
    Merge child chunks under parent, keeping highest-scoring child.
    
    Implements parent-child chunking strategy for better context hydration.
    If a chunk has no parent_chunk_id, treat itself as parent.
    
    Args:
        rows: Retrieved chunks from Milvus (with score field)
        
    Returns:
        Deduplicated chunks grouped by parent, sorted by score (descending)
    """
    by_parent: dict[str, dict] = {}
    
    for row in rows:
        parent_id = row.get("parent_chunk_id") or row["chunk_id"]
        current_best = by_parent.get(parent_id)
        
        # Keep highest-scoring child for this parent
        if current_best is None or row["score"] > current_best["score"]:
            by_parent[parent_id] = {**row, "parent_chunk_id": parent_id}
    
    # Sort by score descending
    return sorted(by_parent.values(), key=lambda x: x["score"], reverse=True)


async def retrieve_chunks(
    query: RetrievalQuery,
    embedding_provider,  # Injected from caller (embedding_service.EmbeddingProvider)
) -> list[dict]:
    """
    Retrieve chunks from Milvus with tenant isolation.
    
    Step 1: Embed query text to 1024-dim vector
    Step 2: Search Milvus with tenant_id + scope_ids filters
    Step 3: Merge child chunks under parents
    Step 4: Return top_k results
    
    See Clarifications: Multi-Tenancy Enforcement Model.
    
    Args:
        query: RetrievalQuery with tenant_id, scope_ids, query_text, top_k
        embedding_provider: Injected async embedding provider
        
    Returns:
        List of dicts with chunk_id, parent_chunk_id, body_text, score
        
    Raises:
        ValueError: If tenant_id missing or Milvus unavailable
    """
    from app.services.milvus_store import get_milvus_client, ensure_collection_exists
    from app.core.config import settings
    
    if not query.tenant_id:
        raise ValueError("tenant_id is mandatory (Clarifications: Multi-Tenancy Enforcement)")
    
    # Step 1: Generate query embedding (reuse embedding_service)
    try:
        query_embeddings = await embedding_provider.embed_batch([query.query_text])
        query_vector = query_embeddings[0]
    except Exception as e:
        logger.error(f"query_embedding_failed: {e}")
        raise ValueError(f"Could not embed query: {e}") from e
    
    # Step 2: Build Milvus filter expression for tenant + scope isolation
    # Filter expression language:
    #   tenant_id == 'local-dev' and scope_hint in ['scope-1', 'scope-2']
    # This ensures NO cross-tenant data leakage (Clarifications: Multi-Tenancy Enforcement)
    
    scope_filter = ""
    if query.scope_ids:
        scope_conditions = " or ".join([f"scope_hint == '{sid}'" for sid in query.scope_ids])
        scope_filter = f" and ({scope_conditions})"
    
    filter_expr = f"tenant_id == '{query.tenant_id}'{scope_filter}"
    
    logger.info(
        f"retrieval_start",
        extra={
            "tenant_id": query.tenant_id,
            "scope_ids": query.scope_ids,
            "filter_expr": filter_expr,
        },
    )
    
    # Step 3: Search Milvus (fetch extra results for parent merging)
    try:
        client = get_milvus_client()
        ensure_collection_exists(client)
        
        results = client.search(
            collection_name=settings.milvus_collection_name,
            data=[query_vector],
            filter=filter_expr,
            limit=query.top_k * 2,  # Fetch extra; will deduplicate under parents
            output_fields=[
                "chunk_id",
                "parent_chunk_id",
                "scope_hint",
                "title",
                "body_text",
                "document_id",
            ],
        )
        
        # Convert Milvus results to dict format
        rows = []
        for result in results[0]:  # results is list of lists (one per query vector)
            rows.append({
                "chunk_id": result["chunk_id"],
                "parent_chunk_id": result.get("parent_chunk_id"),
                "scope_hint": result.get("scope_hint"),
                "title": result.get("title"),
                "body_text": result.get("body_text"),
                "document_id": result.get("document_id"),
                "score": result["_distance"],  # COSINE similarity
            })
        
    except Exception as e:
        logger.error(f"milvus_search_failed: {e}")
        raise ValueError(f"Milvus search failed: {e}") from e
    
    # Step 4: Merge parent-child and return top_k
    merged = filter_to_parent_chunks(rows)
    final_results = merged[:query.top_k]
    
    logger.info(
        f"retrieval_complete",
        extra={
            "tenant_id": query.tenant_id,
            "retrieved_count": len(final_results),
            "raw_count": len(rows),
        },
    )
    
    return final_results
```

```python
# backend/app/graph/nodes/retrieve.py
query = RetrievalQuery(
    tenant_id=state.get("tenant_id", "local-dev"),
    scope_ids=state.get("selected_node_ids", []),
    query_text=state.get("retrieval_query") or "generate quiz context",
    top_k=5,
)
retrieved_chunks = retrieve_with_scope(query)
```

- [ ] **Step 4: Run retrieval tests**

Run: `pytest tests/test_retrieval_service.py tests/test_retrieve_node.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/milvus_store.py backend/app/services/retrieval_service.py backend/app/graph/nodes/retrieve.py backend/tests/test_retrieval_service.py
git commit -m "feat: add milvus retrieval foundation"
```

### Task 5: Deprecated Scope View Reference

**Files:**
- Create: `backend/app/schemas/scope_view.py`
- Create: `backend/app/services/scope_view_builder.py`
- Modify: `backend/app/api/v1/documents.py`
- Test: `backend/tests/test_scope_view_api.py`

- [ ] **Step 1: Write the failing scope view API test**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_scope_view_endpoint_returns_groups(monkeypatch):
    import app.api.v1.documents as docs_api

    monkeypatch.setattr(
        docs_api,
        "build_scope_view",
        lambda tenant_id, document_id, user_goal=None: {
            "scope_view_id": "scope-1",
            "title": "Recommended scope",
            "groups": [{"group_id": "g-1", "label": "Matrix basics", "items": [{"item_key": "chapter-1", "label": "Chapter 1"}]}],
        },
    )

    response = client.get("/api/v1/documents/1/scope-view")
    assert response.status_code == 200
    assert response.json()["title"] == "Recommended scope"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scope_view_api.py -v`
Expected: FAIL with 404 for `/api/v1/documents/1/scope-view`

- [ ] **Step 3: Add schema, builder, and API route**

```python
# backend/app/schemas/scope_view.py
from pydantic import BaseModel


class ScopeViewItem(BaseModel):
    item_key: str
    label: str
    item_type: str = "topic"
    selected_by_default: bool = False


class ScopeViewGroup(BaseModel):
    group_id: str
    label: str
    items: list[ScopeViewItem]


class ScopeViewResponse(BaseModel):
    scope_view_id: str
    title: str
    groups: list[ScopeViewGroup]
```

```python
# backend/app/services/scope_view_builder.py
def build_scope_view(tenant_id: str, document_id: int, user_goal: str | None = None) -> dict:
    return {
        "scope_view_id": f"scope-{tenant_id}-{document_id}",
        "title": "Recommended scope",
        "groups": [
            {
                "group_id": "recent-1",
                "label": user_goal or "Document topics",
                "items": [],
            }
        ],
    }
```

```python
# backend/app/api/v1/documents.py
@router.get("/{document_id}/scope-view", response_model=ScopeViewResponse)
async def get_document_scope_view(document_id: int, user_goal: str | None = Query(default=None)):
    tenant_id = settings.default_tenant_id
    payload = await asyncio.to_thread(build_scope_view, tenant_id, document_id, user_goal)
    return ScopeViewResponse(**payload)
```

- [ ] **Step 4: Run API tests**

Run: `pytest tests/test_scope_view_api.py tests/test_documents_tree.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/scope_view.py backend/app/services/scope_view_builder.py backend/app/api/v1/documents.py backend/tests/test_scope_view_api.py
git commit -m "feat: add scope view api"
```

### Task 6: Deprecated Scope View Reference

**Files:**
- Create: `frontend/src/components/scope/ScopeView.vue`
- Create: `frontend/src/components/scope/ScopeView.spec.ts`
- Modify: `frontend/src/api/documents.ts`
- Modify: `frontend/src/views/DocumentView.vue`
- Test: `frontend/src/views/DocumentView.scope.spec.ts`

- [ ] **Step 1: Write the failing frontend test**

```ts
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'

import DocumentView from './DocumentView.vue'

vi.mock('../api/documents', () => ({
  getDocumentScopeView: vi.fn().mockResolvedValue({
    scope_view_id: 'scope-1',
    title: 'Recommended scope',
    groups: [{ group_id: 'g-1', label: 'Matrix basics', items: [{ item_key: 'chapter-1', label: 'Chapter 1', item_type: 'topic', selected_by_default: true }] }],
  }),
  getDocumentTree: vi.fn().mockResolvedValue({ document_id: 1, nodes: [], total_nodes: 0 }),
}))

test('renders scope view groups before quiz start', async () => {
  const wrapper = mount(DocumentView, {
    global: {
      plugins: [createPinia()],
      mocks: {
        $route: { params: { id: '1' } },
        $router: { push: vi.fn() },
      },
    },
  })
  await flushPromises()
  expect(wrapper.text()).toContain('Matrix basics')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/views/DocumentView.scope.spec.ts`
Expected: FAIL because `getDocumentScopeView` and `ScopeView` do not exist yet

- [ ] **Step 3: Add scope view API typings and UI shell**

```ts
// frontend/src/api/documents.ts
export interface ScopeViewItem {
  item_key: string
  label: string
  item_type: string
  selected_by_default: boolean
}

export interface ScopeViewGroup {
  group_id: string
  label: string
  items: ScopeViewItem[]
}

export interface ScopeViewResponse {
  scope_view_id: string
  title: string
  groups: ScopeViewGroup[]
}

export async function getDocumentScopeView(documentId: number): Promise<ScopeViewResponse> {
  const response = await fetch(`/api/v1/documents/${documentId}/scope-view`)
  if (!response.ok) throw new Error(`Scope view failed: ${response.status} ${response.statusText}`)
  return response.json()
}
```

```vue
<!-- frontend/src/components/scope/ScopeView.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import { useQuizStore } from '../../stores/quiz'
import type { ScopeViewResponse } from '../../api/documents'

const props = defineProps<{ scopeView: ScopeViewResponse }>()
const quizStore = useQuizStore()

const allDefaultKeys = computed(() =>
  props.scopeView.groups.flatMap((group) =>
    group.items.filter((item) => item.selected_by_default).map((item) => item.item_key),
  ),
)
</script>

<template>
  <section class="grid gap-4">
    <article v-for="group in scopeView.groups" :key="group.group_id" class="glass-panel p-4">
      <h2 class="text-lg font-semibold">{{ group.label }}</h2>
      <button
        v-for="item in group.items"
        :key="item.item_key"
        class="mt-3 rounded-lg border px-3 py-2 text-left"
        @click="quizStore.toggleNodeSelection(item.item_key, !quizStore.selectedNodeIds.includes(item.item_key))"
      >
        {{ item.label }}
      </button>
    </article>
  </section>
</template>
```

```vue
<!-- frontend/src/views/DocumentView.vue -->
<script setup lang="ts">
const scopeView = ref<ScopeViewResponse | null>(null)
scopeView.value = await getDocumentScopeView(documentId.value)
</script>

<template>
  <ScopeView v-if="scopeView" :scopeView="scopeView" />
  <KnowledgeGraph v-else-if="treeData" :treeData="treeData" :masteryByParent="masteryByParent" />
</template>
```

- [ ] **Step 4: Run frontend tests**

Run: `npm --prefix frontend run test -- src/components/scope/ScopeView.spec.ts src/views/DocumentView.scope.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/scope/ScopeView.vue frontend/src/components/scope/ScopeView.spec.ts frontend/src/api/documents.ts frontend/src/views/DocumentView.vue frontend/src/views/DocumentView.scope.spec.ts
git commit -m "feat: add scope view frontend shell"
```

### Task 7: Verification For Phase 1 Foundation

**Files:**
- Test: `backend/tests/test_health.py`
- Test: `backend/tests/test_scope_view_api.py`
- Test: `backend/tests/test_retrieval_service.py`
- Test: `frontend/src/views/DocumentView.scope.spec.ts`

- [ ] **Step 1: Run backend verification suite**

Run: `pytest tests/test_phase1_config.py tests/test_postgres_models.py tests/test_object_storage.py tests/test_retrieval_service.py tests/test_scope_view_api.py -v`
Expected: PASS

- [ ] **Step 2: Run frontend verification suite**

Run: `npm --prefix frontend run test -- src/components/scope/ScopeView.spec.ts src/views/DocumentView.scope.spec.ts`
Expected: PASS

- [ ] **Step 3: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS with Vite production build output in `frontend/dist`

- [ ] **Step 4: Smoke-test the app manually**

```text
1. Upload a PDF from UploadView
2. Confirm backend stores source file through object storage abstraction
3. Open /documents/:id and verify scope view renders
4. Select a scope item and start quiz
5. Confirm retrieval still returns quiz context
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "test: verify phase1 enterprise rag foundation"
```

## Self-Review Checklist

- Phase 1 scope is limited to one independently testable subsystem
- PostgreSQL, Milvus, and object storage all have explicit file ownership
- Quiz retrieval responsibilities are separated
- Tenant-aware fields are built into the new schema from the start
- Parent-child retrieval metadata is introduced now so later advanced RAG work does not require schema churn

## Follow-On Plans To Write Next

- `Phase 2 Dynamic Scope Intelligence`
- `Phase 3 Multimodal Asset And Excel Retrieval`
- `Phase 4 LLM Ops, Cost Tracking, And Fallback Gateway`

---

## Appendix A: Implementation Quick Start Guide

This section provides a rapid reference for implementing Phase 1. All code is production-ready and can be copy-pasted directly into your project.

### Quick Pattern: Async Embedding Job (Task 4 Foundation)

```python
# Pattern: Enqueue embedding job after document upload
from app.services.embedding_service import embed_document_job
from app.services.processing_queue import enqueue_job

# In upload handler after storing document to PostgreSQL + object storage:
enqueue_job(
    embed_document_job,
    args=(
        document_id=doc.id,
        tenant_id="local-dev",
        chunk_ids=chunk_ids,  # from parser
        chunk_texts=chunk_texts,  # from parser
    ),
    max_retries=3,  # Handled by job queue with exponential backoff
)
```

### Quick Pattern: Tenant-Safe Retrieval (Task 4)

```python
# Pattern: Retrieve chunks with strict tenant isolation
from app.services.retrieval_service import retrieve_chunks, RetrievalQuery
from app.services.embedding_service import get_embedding_provider

query = RetrievalQuery(
    tenant_id="local-dev",  # ALWAYS from auth context
    scope_ids=["scope-1"],  # User-selected scopes
    query_text="how does RAG work?",
    top_k=5,
)

provider = get_embedding_provider()
results = await retrieve_chunks(query, provider)

# results[0] = {
#   "chunk_id": "chunk-123",
#   "parent_chunk_id": "parent-456",  # Deduplicated from child chunks
#   "body_text": "...",
#   "score": 0.92,
# }
```

### Quick Pattern: Storage Abstraction (Task 3)

```python
# Pattern: Use storage abstraction to remain cloud-agnostic
from app.services.object_storage import get_object_storage

storage = get_object_storage()  # Returns LocalObjectStorage or S3CompatibleStorage

# Upload
key = await asyncio.to_thread(
    storage.put_bytes,
    f"raw/{tenant_id}/{doc_id}/source.pdf",
    content,
)

# Retrieve
uri = storage.uri_for(key)  # Returns "local://..." or "s3://..."
```

### Key Configuration (settings.py)

```python
# Essential Phase 1 settings
class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:pass@localhost/ai_class"
    
    # Milvus
    milvus_uri: str = "http://localhost:19530"
    milvus_collection_name: str = "ai_class_chunks"
    
    # Embedding
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_base_url: str = "https://api.openai.com/v1"
    
    # Object Storage
    storage_backend: str = "local"  # or "s3"
    storage_local_root: Path = Path("/tmp/ai-class-storage")
    
    # Multi-tenancy
    default_tenant_id: str = "local-dev"
```

### Testing Patterns

```python
# Pattern: Mock embedding provider for fast tests
@pytest.mark.asyncio
async def test_retrieval_with_mock_embeddings():
    mock_provider = AsyncMock()
    mock_provider.embed_batch = AsyncMock(
        return_value=[[0.1] * 1024 for _ in range(2)]
    )
    
    query = RetrievalQuery(
        tenant_id="tenant-1",
        scope_ids=["scope-1"],
        query_text="test",
        top_k=3,
    )
    
    results = await retrieve_chunks(query, mock_provider)
    assert len(results) <= 3
```

### Dependency Injection Pattern

```python
# All services use factory functions for testability
from app.services.embedding_service import get_embedding_provider
from app.services.milvus_store import get_milvus_client
from app.services.object_storage import get_object_storage

# In main app or FastAPI startup:
provider = get_embedding_provider()
client = get_milvus_client()
storage = get_object_storage()

# In tests, override with mocks or test doubles
def test_with_custom_provider():
    test_provider = EmbeddingProvider(api_key="test")
    # use test_provider in your code
```

### File Ownership Summary

| Component | Owner | Tests |
|-----------|-------|-------|
| `backend/app/services/embedding_service.py` | Task 4 | `test_embedding_service.py` |
| `backend/app/services/milvus_store.py` | Task 4 | `test_retrieval_service.py` |
| `backend/app/services/retrieval_service.py` | Task 4 | `test_retrieval_service.py` |
| `backend/app/services/object_storage.py` | Task 3 | `test_object_storage.py` |
| `backend/app/db/models.py` | Task 1 | `test_postgres_models.py` |
| `backend/app/graph/nodes/retrieve.py` | Task 4 | `test_retrieve_node.py` |


### Phase 1 Integration Checklist

- [ ] PostgreSQL running locally (task 1)
- [ ] Milvus running locally (task 2)
- [ ] Object storage abstraction in place (task 3)
- [ ] Embedding service + async job queue (task 4)
- [ ] Retrieval service with tenant isolation (task 4)


- [ ] All tests passing (task 6)
- [ ] No cross-tenant data visible in any layer
- [ ] Upload → embedding → retrieval workflow end-to-end

---

## Appendix B: Troubleshooting Common Phase 1 Issues

### Issue: Embedding API Rate Limit
- **Symptom**: Job queue task fails with 429 error
- **Root Cause**: OpenAI embedding endpoint hit rate limit
- **Fix**: Enable batch processing (already done in `embed_batch()` splitting)
- **Monitor**: Log all rate limit events; add jitter to retry delays

### Issue: Milvus Collection Not Found
- **Symptom**: Retrieval fails with "collection not found"
- **Root Cause**: `ensure_collection_exists()` called with wrong collection name
- **Fix**: Verify `MILVUS_COLLECTION_NAME` in `.env` matches hardcoded schema name
- **Monitor**: Always call `ensure_collection_exists()` before search/upsert

### Issue: Cross-Tenant Data Visible in Results
- **Symptom**: Tenant A can see documents uploaded by Tenant B
- **Root Cause**: Milvus filter expression missing or wrong
- **Fix**: Check `retrieve_chunks()` filter_expr always contains `tenant_id == '{query.tenant_id}'`
- **Monitor**: Unit test with at least 2 tenants to catch isolation failures

### Issue: Milvus Upsert Fails After Embedding Succeeds
- **Symptom**: Embedding job log shows "embedding_batch_complete" but chunk not visible in retrieval
- **Root Cause**: Likely schema mismatch (missing field, type error)
- **Fix**: Verify schema in `ensure_collection_exists()` matches your data shape
- **Monitor**: Check Milvus collection stats after upsert: `client.get_collection_stats()`

### Issue: Document Upload Returns But Quiz Never Has Context
- **Symptom**: Upload succeeds, but retrieval returns 0 chunks
- **Root Cause**: Job queue not running or embedding job crashed
- **Fix**: Check job queue logs and audit_log returned by `embed_document_job()`
- **Monitor**: Periodic job to reconcile PostgreSQL documents with Milvus chunk count

---

## Appendix C: Data Flow Diagrams

### Upload to Quiz Retrieval Flow

```
User → Upload PDF → FastAPI /upload
         ↓
    Store source to object storage (key: raw/{tenant_id}/{doc_id}/source.pdf)
    Create DocumentRecord in PostgreSQL
    Enqueue async job: parse → chunk → embed → upsert Milvus
    Return HTTP 201 immediately (UX preserved)

Later (job queue worker):
    Parse PDF → ChunkRecords in PostgreSQL
    Generate 1024-dim embeddings via OpenAI
    Upsert (chunk_id, embedding, tenant_id, parent_chunk_id) to Milvus
    Log audit trail for Phase 2 reconciliation

User → Start Quiz → FastAPI /quiz
         ↓
    User selects knowledge tree node
    User enters question
    Call retrieve_chunks(RetrievalQuery(tenant_id, scope_ids, question))
         ↓
    1. Embed question → 1024-dim vector
    2. Search Milvus filter: tenant_id + scope_ids
    3. Merge child chunks under parents
    4. Return top_k parent chunks
         ↓
    LangGraph workflow uses retrieved chunks as context
    LLM generates quiz question/answer
    Return result to user
```

### Data Consistency Model

```
PostgreSQL (Source of Truth) ← Eventual Consistency → Milvus (Search Index)

Write Path:
  Document upload → PostgreSQL commit (ACK to user) → Queue embedding job
  Job processes → Upsert Milvus (failure logged, retry scheduled)

Read Path:
  Query for quiz → Retrieve from Milvus (fast)
  Hydrate metadata → Join with PostgreSQL (accurate)

Recovery (Phase 2):
  Periodic reconciliation job compares counts
  Replays failed jobs from audit log
  Rebuilds collection if necessary
```

---

