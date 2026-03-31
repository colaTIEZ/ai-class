"""Pytest 配置 - 提供测试用 FastAPI 客户端"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """创建测试用 HTTP 客户端"""
    return TestClient(app)
