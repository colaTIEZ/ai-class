"""测试健康检查端点和 API 信封格式"""


def test_health_endpoint_returns_200(client):
    """验证健康检查端点返回 200 状态码"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_endpoint_standard_envelope(client):
    """验证返回数据严格遵循 API 标准信封格式"""
    response = client.get("/api/v1/health")
    data = response.json()

    # 必须包含标准信封的四个顶层字段
    assert "status" in data
    assert "data" in data
    assert "message" in data
    assert "trace_id" in data

    # 验证值
    assert data["status"] == "success"
    assert data["data"]["service"] == "ai-class"
    assert data["data"]["health"] == "ok"
    assert "embedding_ready" in data["data"]
    assert isinstance(data["data"]["embedding_ready"], bool)
    assert data["message"] == ""
    assert data["trace_id"] == ""


def test_health_endpoint_response_keys_are_snake_case(client):
    """验证所有 JSON key 都使用 snake_case 命名"""
    response = client.get("/api/v1/health")
    data = response.json()

    for key in data.keys():
        assert "_" in key or key.islower(), (
            f"Key '{key}' is not snake_case"
        )

    for key in data["data"].keys():
        assert "_" in key or key.islower(), (
            f"Nested key '{key}' is not snake_case"
        )
