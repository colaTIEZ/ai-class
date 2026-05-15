"""RAG 检索节点单元测试

测试 retrieve_node 的 Milvus 检索逻辑。
"""

import pytest
from unittest.mock import AsyncMock

from app.graph.nodes.retrieve import retrieve_node
from app.graph.state import SocraticState


def _setup_mocks(monkeypatch, chunks):
    mock_provider = AsyncMock()
    mock_provider.embed_batch = AsyncMock(return_value=[[0.1] * 1024])

    monkeypatch.setattr(
        "app.services.embedding_service.get_embedding_provider",
        lambda: mock_provider,
    )

    async def mock_retrieve(query, provider):
        return chunks

    monkeypatch.setattr(
        "app.graph.nodes.retrieve.retrieve_chunks",
        mock_retrieve,
    )


class TestRetrieveNode:
    """测试 retrieve_node LangGraph 节点"""

    def test_trace_log_appended(self, monkeypatch):
        _setup_mocks(monkeypatch, [{"chunk_id": "c1", "body_text": "text", "score": 0.9}])

        state: SocraticState = {
            "retrieved_chunks": [],
            "trace_log": [{"node": "init", "timestamp": "2026-01-01T00:00:00Z", "metadata": {}}],
        }

        result = retrieve_node(state)

        assert len(result["trace_log"]) == 2
        assert result["trace_log"][1]["node"] == "retrieve"

    def test_preserves_existing_trace_log(self, monkeypatch):
        _setup_mocks(monkeypatch, [{"chunk_id": "c1", "body_text": "text", "score": 0.9}])

        existing_entry = {"node": "init", "timestamp": "2026-01-01T00:00:00Z", "metadata": {"test": True}}
        state: SocraticState = {
            "retrieved_chunks": [],
            "trace_log": [existing_entry],
        }

        result = retrieve_node(state)

        assert result["trace_log"][0] == existing_entry


class TestRetrieveNodeMilvus:
    """retrieve_node Milvus 集成测试（mocked embedding provider）"""

    def test_retrieval_returns_chunks(self, monkeypatch):
        mock_chunks = [
            {"chunk_id": "c1", "body_text": "text1", "score": 0.9},
            {"chunk_id": "c2", "body_text": "text2", "score": 0.8},
        ]
        _setup_mocks(monkeypatch, mock_chunks)

        state: SocraticState = {
            "retrieved_chunks": [],
            "trace_log": [],
            "question_type": "multiple_choice",
            "current_question": None,
            "error_message": None,
        }

        result = retrieve_node(state)

        assert len(result["retrieved_chunks"]) == 2
        assert result["error_message"] is None
        assert result["trace_log"][0]["metadata"]["chunks_retrieved"] == 2

    def test_retrieval_empty_result(self, monkeypatch):
        _setup_mocks(monkeypatch, [])

        state: SocraticState = {
            "retrieved_chunks": [],
            "trace_log": [],
        }

        result = retrieve_node(state)

        assert result["retrieved_chunks"] == []
        assert result["error_message"] == "No relevant content found"
