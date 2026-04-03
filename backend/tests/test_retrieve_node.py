"""RAG 检索节点单元测试

测试 retrieve_by_nodes 函数和 retrieve_node 的层级展开逻辑。
"""

import pytest
import sqlite3
from datetime import datetime

from app.services.vector_store import (
    get_connection, 
    init_db, 
    get_descendant_node_ids,
    retrieve_by_nodes
)
from app.graph.nodes.retrieve import retrieve_node
from app.graph.state import SocraticState


@pytest.fixture
def test_db():
    """创建内存测试数据库并初始化表结构"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # 创建 knowledge_nodes 表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            node_id TEXT PRIMARY KEY,
            document_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            parent_id TEXT,
            content_summary TEXT NOT NULL,
            depth INTEGER DEFAULT 0,
            chunk_text TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def populated_db(test_db):
    """填充测试数据的数据库"""
    # 创建层级结构：
    # root (depth=0)
    #   ├── chapter1 (depth=1)
    #   │   ├── section1_1 (depth=2)
    #   │   └── section1_2 (depth=2)
    #   └── chapter2 (depth=1)
    #       └── section2_1 (depth=2)
    
    nodes = [
        ("root", 1, "Root Node", None, "Root summary", 0, "Root content about the course."),
        ("chapter1", 1, "Chapter 1", "root", "Chapter 1 summary", 1, "Chapter 1 introduces basic concepts."),
        ("section1_1", 1, "Section 1.1", "chapter1", "Section 1.1 summary", 2, "Section 1.1 covers fundamentals."),
        ("section1_2", 1, "Section 1.2", "chapter1", "Section 1.2 summary", 2, "Section 1.2 discusses examples."),
        ("chapter2", 1, "Chapter 2", "root", "Chapter 2 summary", 1, "Chapter 2 explores advanced topics."),
        ("section2_1", 1, "Section 2.1", "chapter2", "Section 2.1 summary", 2, "Section 2.1 dives into algorithms."),
    ]
    
    test_db.executemany(
        """
        INSERT INTO knowledge_nodes 
        (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        nodes
    )
    test_db.commit()
    return test_db


class TestGetDescendantNodeIds:
    """测试层级展开函数"""
    
    def test_empty_input(self, test_db):
        """空输入返回空列表"""
        result = get_descendant_node_ids(test_db, [])
        assert result == []
    
    def test_leaf_node(self, populated_db):
        """叶子节点只返回自身"""
        result = get_descendant_node_ids(populated_db, ["section1_1"])
        assert set(result) == {"section1_1"}
    
    def test_parent_includes_children(self, populated_db):
        """父节点包含所有子节点"""
        result = get_descendant_node_ids(populated_db, ["chapter1"])
        assert set(result) == {"chapter1", "section1_1", "section1_2"}
    
    def test_root_includes_all(self, populated_db):
        """根节点包含所有后代"""
        result = get_descendant_node_ids(populated_db, ["root"])
        expected = {"root", "chapter1", "section1_1", "section1_2", "chapter2", "section2_1"}
        assert set(result) == expected
    
    def test_multiple_nodes(self, populated_db):
        """多个节点合并结果"""
        result = get_descendant_node_ids(populated_db, ["section1_1", "chapter2"])
        expected = {"section1_1", "chapter2", "section2_1"}
        assert set(result) == expected
    
    def test_nonexistent_node(self, populated_db):
        """不存在的节点返回空"""
        result = get_descendant_node_ids(populated_db, ["nonexistent"])
        assert result == []


class TestRetrieveByNodes:
    """测试 retrieve_by_nodes 函数"""
    
    def test_empty_node_ids(self, populated_db):
        """空节点列表返回空结果"""
        result = retrieve_by_nodes([], conn=populated_db)
        assert result == []
    
    def test_single_leaf_node(self, populated_db):
        """单个叶子节点返回其内容"""
        result = retrieve_by_nodes(["section1_1"], conn=populated_db)
        assert len(result) == 1
        assert result[0]["node_id"] == "section1_1"
        assert result[0]["chunk_text"] == "Section 1.1 covers fundamentals."
    
    def test_parent_retrieves_children(self, populated_db):
        """父节点检索包含子节点内容"""
        result = retrieve_by_nodes(["chapter1"], conn=populated_db)
        # chapter1 + section1_1 + section1_2 = 3 chunks
        assert len(result) == 3
        node_ids = {r["node_id"] for r in result}
        assert node_ids == {"chapter1", "section1_1", "section1_2"}
    
    def test_top_k_limit(self, populated_db):
        """top_k 参数限制返回数量"""
        result = retrieve_by_nodes(["root"], top_k=2, conn=populated_db)
        assert len(result) == 2
    
    def test_result_structure(self, populated_db):
        """验证返回结构正确"""
        result = retrieve_by_nodes(["section1_1"], conn=populated_db)
        assert len(result) == 1
        chunk = result[0]
        assert "node_id" in chunk
        assert "chunk_text" in chunk
        assert "label" in chunk
        assert "depth" in chunk
        assert "score" in chunk
    
    def test_sorted_by_depth(self, populated_db):
        """结果按深度排序（浅层优先）"""
        result = retrieve_by_nodes(["root"], top_k=10, conn=populated_db)
        depths = [r["depth"] for r in result]
        assert depths == sorted(depths)


class TestRetrieveNode:
    """测试 retrieve_node LangGraph 节点"""
    
    def test_empty_state(self):
        """空状态返回错误"""
        state: SocraticState = {
            "selected_node_ids": [],
            "retrieved_chunks": [],
            "trace_log": []
        }
        
        result = retrieve_node(state)
        
        assert result["retrieved_chunks"] == []
        assert result["error_message"] is not None
        assert "No node IDs" in result["error_message"]
    
    def test_trace_log_appended(self):
        """追踪日志被添加"""
        state: SocraticState = {
            "selected_node_ids": ["test_node"],
            "retrieved_chunks": [],
            "trace_log": [{"node": "init", "timestamp": "2026-01-01T00:00:00Z", "metadata": {}}]
        }
        
        result = retrieve_node(state)
        
        assert len(result["trace_log"]) == 2
        assert result["trace_log"][1]["node"] == "retrieve"
        assert "timestamp" in result["trace_log"][1]
        assert "metadata" in result["trace_log"][1]
    
    def test_preserves_existing_trace_log(self):
        """保留现有追踪日志"""
        existing_entry = {"node": "init", "timestamp": "2026-01-01T00:00:00Z", "metadata": {"test": True}}
        state: SocraticState = {
            "selected_node_ids": ["test_node"],
            "retrieved_chunks": [],
            "trace_log": [existing_entry]
        }
        
        result = retrieve_node(state)
        
        assert result["trace_log"][0] == existing_entry


class TestRetrieveNodeIntegration:
    """retrieve_node 集成测试（使用真实数据库）"""
    
    def test_with_populated_db(self, populated_db, monkeypatch):
        """使用填充数据库测试完整流程"""
        # Monkeypatch get_connection 使用测试数据库
        def mock_get_connection():
            return populated_db
        
        monkeypatch.setattr("app.services.vector_store.get_connection", mock_get_connection)
        
        state: SocraticState = {
            "selected_node_ids": ["chapter1"],
            "retrieved_chunks": [],
            "trace_log": [],
            "question_type": "multiple_choice",
            "current_question": None,
            "error_message": None
        }
        
        result = retrieve_node(state)
        
        assert len(result["retrieved_chunks"]) == 3
        assert result["error_message"] is None
        assert result["trace_log"][0]["metadata"]["chunks_retrieved"] == 3
