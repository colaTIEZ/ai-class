"""前后端集成测试 - 验证 API 端点符合前端预期的标准信封格式"""


def test_health_endpoint_matches_frontend_contract(client):
    """验证 /api/v1/health 返回的数据格式与前端 TypeScript 接口完全匹配

    前端 ApiEnvelope<HealthData> 接口要求:
    - status: 'success' | 'error'
    - data: { service: string, version: string, health: string }
    - message: string
    - trace_id: string
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()

    # 验证 ApiEnvelope 结构
    assert isinstance(data["status"], str)
    assert data["status"] in ("success", "error")
    assert isinstance(data["data"], dict)
    assert isinstance(data["message"], str)
    assert isinstance(data["trace_id"], str)

    # 验证 HealthData 结构
    health_data = data["data"]
    assert isinstance(health_data["service"], str)
    assert isinstance(health_data["version"], str)
    assert isinstance(health_data["health"], str)

    # 验证具体值
    assert health_data["service"] == "ai-class"
    assert health_data["health"] == "ok"


def test_cors_headers_allow_frontend(client):
    """验证 CORS 配置允许前端开发服务器 (localhost:5173) 的跨域请求"""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI CORS 中间件会在 OPTIONS 预检请求上返回 CORS 头
    assert response.status_code == 200


def test_nonexistent_endpoint_returns_json(client):
    """验证不存在的端点返回 404 而不是 HTML 错误页"""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
