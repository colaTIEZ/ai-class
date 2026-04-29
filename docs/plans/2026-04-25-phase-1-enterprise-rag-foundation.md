# Phase 1 Enterprise RAG Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-style foundation for `ai-class` by introducing PostgreSQL, Milvus, object storage abstraction, and a dynamic scope view API without breaking the existing upload-to-quiz workflow.

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
- Dynamic scope view backend + frontend shell

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
- `backend/app/services/scope_view_builder.py`
- `backend/app/schemas/scope_view.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/20260425_01_phase1_core_tables.py`

### New test files

- `backend/tests/test_phase1_config.py`
- `backend/tests/test_postgres_models.py`
- `backend/tests/test_object_storage.py`
- `backend/tests/test_retrieval_service.py`
- `backend/tests/test_scope_view_api.py`
- `frontend/src/views/DocumentView.scope.spec.ts`

### New frontend files

- `frontend/src/components/scope/ScopeView.vue`
- `frontend/src/components/scope/ScopeView.spec.ts`

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
        scope_view_enabled=True,
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.milvus_uri == "http://localhost:19530"
    assert settings.object_storage_backend == "local"
    assert settings.object_storage_bucket == "ai-class-dev"
    assert settings.scope_view_enabled is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_phase1_config.py -v`
Expected: FAIL with missing `milvus_uri`, `object_storage_backend`, or `scope_view_enabled` fields on `Settings`

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

    scope_view_enabled: bool = True
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
SCOPE_VIEW_ENABLED=true
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
Expected: SUCCESS with new `documents`, `chunks`, `scope_views`, and `scope_view_items` tables created in PostgreSQL

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

### Task 4: Add Milvus Retrieval Foundation With Parent-Child Metadata

**Files:**
- Create: `backend/app/services/milvus_store.py`
- Create: `backend/app/services/embedding_service.py`
- Create: `backend/app/services/retrieval_service.py`
- Modify: `backend/app/services/processing_queue.py`
- Modify: `backend/app/graph/nodes/retrieve.py`
- Test: `backend/tests/test_retrieval_service.py`

**Architecture Note**: Embedding generation is async via job queue (see Clarifications section above). This task implements the retrieval-time component and the Milvus foundation.

- [ ] **Step 1: Write the failing retrieval test**

```python
from app.services.retrieval_service import RetrievalQuery, filter_to_parent_chunks


def test_filter_to_parent_chunks_groups_children():
    docs = [
        {"chunk_id": "child-1", "parent_chunk_id": "parent-a", "score": 0.91, "text": "small"},
        {"chunk_id": "child-2", "parent_chunk_id": "parent-a", "score": 0.89, "text": "small 2"},
        {"chunk_id": "child-3", "parent_chunk_id": "parent-b", "score": 0.88, "text": "small 3"},
    ]

    merged = filter_to_parent_chunks(docs)
    assert [item["parent_chunk_id"] for item in merged] == ["parent-a", "parent-b"]
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
from dataclasses import dataclass


@dataclass(slots=True)
class RetrievalQuery:
    tenant_id: str
    scope_ids: list[str]
    query_text: str
    top_k: int = 6


def filter_to_parent_chunks(rows: list[dict]) -> list[dict]:
    by_parent: dict[str, dict] = {}
    for row in rows:
        parent_id = row.get("parent_chunk_id") or row["chunk_id"]
        current = by_parent.get(parent_id)
        if current is None or row["score"] > current["score"]:
            by_parent[parent_id] = {**row, "parent_chunk_id": parent_id}
    return sorted(by_parent.values(), key=lambda item: item["score"], reverse=True)
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

### Task 5: Add Dynamic Scope View Backend API

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

### Task 6: Replace Tree-Only Document Page With Scope View Container

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

### Task 7: Run End-To-End Verification For The New Foundation

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
- Scope view and quiz retrieval responsibilities are separated
- Tenant-aware fields are built into the new schema from the start
- Parent-child retrieval metadata is introduced now so later advanced RAG work does not require schema churn

## Follow-On Plans To Write Next

- `Phase 2 Dynamic Scope Intelligence`
- `Phase 3 Multimodal Asset And Excel Retrieval`
- `Phase 4 LLM Ops, Cost Tracking, And Fallback Gateway`

