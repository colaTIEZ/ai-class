"""Pytest 配置 - 提供测试用 FastAPI 客户端"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.processing_queue import processing_queue
from app.services.vector_store import init_db


@pytest.fixture
def client():
    """创建测试用 HTTP 客户端"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def enable_embedding_for_tests():
    """默认开启 embedding 配置，避免与上传流程冲突。"""
    old_key = settings.openai_api_key
    settings.openai_api_key = "test-key"
    yield
    settings.openai_api_key = old_key


@pytest.fixture
def force_no_openai_key(monkeypatch: pytest.MonkeyPatch):
    """在需要规则回退分支时，强制禁用 API Key，避免测试并发写全局配置。"""
    monkeypatch.setattr(settings, "openai_api_key", "")


@pytest_asyncio.fixture
async def async_client():
    """异步客户端，复用应用并显式管理队列生命周期。"""
    async with ASGITransport(app=app) as transport:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            init_db()
            processing_queue.start_worker()
            yield client
            await processing_queue.stop_worker()
