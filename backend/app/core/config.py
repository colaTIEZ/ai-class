"""应用配置模块 - 使用 pydantic-settings 管理环境变量"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """全局应用设置，通过 .env 文件或环境变量加载"""

    # 应用基本信息
    app_name: str = "ai-class"
    app_version: str = "0.1.0"
    debug: bool = False

    # 数据库配置
    database_url: str = "sqlite:///data/ai_class.db"
    database_path: str = str(
        Path(__file__).resolve().parent.parent.parent / "data" / "ai_class.db"
    )

    # 外部 API 配置（后续 Epic 使用）
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "deepseek-chat"

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 配置
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# 全局单例
settings = Settings()
