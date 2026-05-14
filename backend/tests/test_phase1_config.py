"""Phase 1 enterprise config validation tests."""

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
    assert settings.milvus_collection_name == "knowledge_chunks"
    assert settings.object_storage_backend == "local"
    assert settings.object_storage_bucket == "ai-class-dev"
    assert settings.object_storage_local_root == "data/object_store"


def test_phase1_settings_have_defaults():
    settings = Settings()
    assert settings.milvus_uri == "http://localhost:19530"
    assert settings.milvus_collection_name == "knowledge_chunks"
    assert settings.object_storage_backend == "local"
    assert settings.object_storage_bucket == "ai-class-dev"
    assert settings.default_tenant_id == "local-dev"
