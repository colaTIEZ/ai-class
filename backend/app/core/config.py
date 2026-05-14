"""应用配置模块 - 使用 pydantic-settings 管理环境变量"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局应用设置，通过 .env 文件或环境变量加载"""

    # 应用基本信息
    app_name: str = "ai-class"
    app_version: str = "0.1.0"
    debug: bool = False

    # 数据库配置
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_class"
    database_path: str = str(
        Path(__file__).resolve().parent.parent.parent / "data" / "ai_class.db"
    )

    # Milvus 向量数据库配置
    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_collection_name: str = "knowledge_chunks"

    # 对象存储配置
    object_storage_backend: str = "local"
    object_storage_bucket: str = "ai-class-dev"
    object_storage_endpoint: str = ""
    object_storage_access_key: str = ""
    object_storage_secret_key: str = ""
    object_storage_local_root: str = str(
        Path(__file__).resolve().parent.parent.parent / "data" / "object_store"
    )

    # 多租户默认配置
    default_tenant_id: str = "local-dev"

    # 外部 API 配置
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    openai_embedding_model: str = ""
    openai_embedding_fallback_model: str = ""

    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    MAX_QUEUE_SIZE: int = 100
    zombie_task_timeout_seconds: int = 300

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 配置
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def embedding_ready(self) -> bool:
        return bool((self.openai_api_key or "").strip())


# 全局单例
settings = Settings()
