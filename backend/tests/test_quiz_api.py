"""Quiz API 集成测试

测试 POST /api/v1/quiz/init 端点的完整流程。
使用 mock 避免实际 LLM API 调用。
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.graph.state import SocraticState


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestQuizInitEndpoint:
    """测试 /api/v1/quiz/init 端点"""
    
    def test_missing_node_ids(self, client):
        """缺少节点 ID 返回 422"""
        response = client.post("/api/v1/quiz/init", json={})
        assert response.status_code == 422
    
    def test_empty_node_ids_returns_422(self, client):
        """空节点列表返回 422（Pydantic 验证）"""
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": []}
        )
        assert response.status_code == 422
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_successful_quiz_generation(self, mock_invoke, client):
        """成功生成 quiz 返回 200"""
        # Mock 成功的 graph 执行结果
        mock_state: SocraticState = {
            "selected_node_ids": ["node_1"],
            "retrieved_chunks": [{"chunk_text": "Test content"}],
            "current_question": {
                "question_text": "What is Python?",
                "options": ["A language", "A snake", "A game", "A movie"],
                "correct_answer": "A language"
            },
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": None
        }
        mock_invoke.return_value = {
            "state": mock_state,
            "thread_id": "test-thread-id"
        }
        
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": ["node_1"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["question"]["question_text"] == "What is Python?"
        assert len(data["data"]["question"]["options"]) == 4
        assert data["data"]["question_type"] == "multiple_choice"
        assert "trace_id" in data
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_short_answer_question_type(self, mock_invoke, client):
        """短答题类型正确处理"""
        mock_state: SocraticState = {
            "selected_node_ids": ["node_1"],
            "retrieved_chunks": [{"chunk_text": "Test content"}],
            "current_question": {
                "question_text": "Explain Python.",
                "options": None,
                "correct_answer": "Python is a programming language."
            },
            "question_type": "short_answer",
            "trace_log": [],
            "error_message": None
        }
        mock_invoke.return_value = {
            "state": mock_state,
            "thread_id": "test-thread-id"
        }
        
        response = client.post(
            "/api/v1/quiz/init",
            json={
                "selected_node_ids": ["node_1"],
                "question_type": "short_answer"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["question"]["options"] is None
        assert data["data"]["question_type"] == "short_answer"
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_retrieval_error(self, mock_invoke, client):
        """检索错误返回 500"""
        mock_state: SocraticState = {
            "selected_node_ids": ["node_1"],
            "retrieved_chunks": [],
            "current_question": None,
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": "No relevant content found"
        }
        mock_invoke.return_value = {
            "state": mock_state,
            "thread_id": "test-thread-id"
        }
        
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": ["node_1"]}
        )
        
        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["status"] == "error"
        assert "No relevant content" in data["message"]
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_llm_error(self, mock_invoke, client):
        """LLM 错误返回 500"""
        mock_invoke.side_effect = Exception("LLM API timeout")
        
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": ["node_1"]}
        )
        
        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["status"] == "error"
        assert "LLM API timeout" in data["message"]
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_no_question_generated(self, mock_invoke, client):
        """未生成问题返回 500"""
        mock_state: SocraticState = {
            "selected_node_ids": ["node_1"],
            "retrieved_chunks": [{"chunk_text": "Test"}],
            "current_question": None,  # 没有生成问题
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": None  # 也没有错误信息
        }
        mock_invoke.return_value = {
            "state": mock_state,
            "thread_id": "test-thread-id"
        }
        
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": ["node_1"]}
        )
        
        assert response.status_code == 500
        data = response.json()["detail"]
        assert "Failed to generate" in data["message"]
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_multiple_node_ids(self, mock_invoke, client):
        """多个节点 ID 正确传递"""
        mock_state: SocraticState = {
            "selected_node_ids": ["node_1", "node_2", "node_3"],
            "retrieved_chunks": [{"chunk_text": "Combined content"}],
            "current_question": {
                "question_text": "What covers all topics?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A"
            },
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": None
        }
        mock_invoke.return_value = {
            "state": mock_state,
            "thread_id": "test-thread-id"
        }
        
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": ["node_1", "node_2", "node_3"]}
        )
        
        assert response.status_code == 200
        
        # 验证调用参数
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args
        assert call_args.kwargs["selected_node_ids"] == ["node_1", "node_2", "node_3"]


class TestResponseFormat:
    """测试响应格式符合数据契约"""
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_response_uses_snake_case(self, mock_invoke, client):
        """响应使用 snake_case"""
        mock_state: SocraticState = {
            "selected_node_ids": ["node_1"],
            "retrieved_chunks": [{"chunk_text": "Test"}],
            "current_question": {
                "question_text": "Test?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A"
            },
            "question_type": "multiple_choice",
            "trace_log": [],
            "error_message": None
        }
        mock_invoke.return_value = {"state": mock_state, "thread_id": "test"}
        
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": ["node_1"]}
        )
        
        data = response.json()
        
        # 验证所有键使用 snake_case
        assert "question_text" in data["data"]["question"]
        assert "correct_answer" in data["data"]["question"]
        assert "question_type" in data["data"]
        assert "trace_id" in data
        
        # 验证没有 camelCase
        json_str = json.dumps(data)
        assert "questionText" not in json_str
        assert "correctAnswer" not in json_str
        assert "traceId" not in json_str
    
    @patch("app.api.v1.chat.invoke_quiz_generation")
    def test_response_envelope_structure(self, mock_invoke, client):
        """响应使用标准信封格式"""
        mock_state: SocraticState = {
            "selected_node_ids": ["node_1"],
            "retrieved_chunks": [{"chunk_text": "Test"}],
            "current_question": {
                "question_text": "Test?",
                "options": None,
                "correct_answer": "Answer"
            },
            "question_type": "short_answer",
            "trace_log": [],
            "error_message": None
        }
        mock_invoke.return_value = {"state": mock_state, "thread_id": "test"}
        
        response = client.post(
            "/api/v1/quiz/init",
            json={"selected_node_ids": ["node_1"]}
        )
        
        data = response.json()
        
        # 验证信封结构
        assert "status" in data
        assert "data" in data
        assert "trace_id" in data
        assert data["status"] == "success"
