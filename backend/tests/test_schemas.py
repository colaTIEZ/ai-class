"""测试 knowledge_tree 数据契约的严格性"""

import pytest
from pydantic import ValidationError

from app.schemas.knowledge_tree import KnowledgeNode, KnowledgeNodeInDB, KnowledgeTree


class TestKnowledgeNode:
    """测试基础知识节点模型"""

    def test_valid_node_creation(self):
        """验证合法节点能正常创建"""
        node = KnowledgeNode(
            node_id="doc_1_node_001",
            label="第一章：线性代数",
            parent_id=None,
            content_summary="介绍矩阵运算基础",
        )
        assert node.node_id == "doc_1_node_001"
        assert node.label == "第一章：线性代数"
        assert node.parent_id is None
        assert node.content_summary == "介绍矩阵运算基础"

    def test_node_with_parent(self):
        """验证带 parent_id 的子节点创建"""
        node = KnowledgeNode(
            node_id="doc_1_node_002",
            label="1.1 矩阵乘法",
            parent_id="doc_1_node_001",
            content_summary="矩阵乘法规则和性质",
        )
        assert node.parent_id == "doc_1_node_001"

    def test_missing_required_field_raises_error(self):
        """验证缺少必填字段时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            KnowledgeNode(
                node_id="doc_1_node_001",
                # 缺少 label
                content_summary="some summary",
            )

    def test_missing_node_id_raises_error(self):
        """验证缺少 node_id 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            KnowledgeNode(
                label="测试",
                content_summary="摘要",
            )

    def test_missing_content_summary_raises_error(self):
        """验证缺少 content_summary 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            KnowledgeNode(
                node_id="doc_1_node_001",
                label="测试",
            )

    def test_contract_enforces_all_four_fields(self):
        """验证契约强制包含所有四个字段: node_id, label, parent_id, content_summary"""
        node = KnowledgeNode(
            node_id="test_id",
            label="test_label",
            parent_id="parent",
            content_summary="summary",
        )
        # 导出的字典必须包含全部四个契约字段
        exported = node.model_dump()
        assert "node_id" in exported
        assert "label" in exported
        assert "parent_id" in exported
        assert "content_summary" in exported


class TestKnowledgeNodeInDB:
    """测试数据库层知识节点模型"""

    def test_db_node_has_extra_fields(self):
        """验证数据库模型包含扩展字段"""
        node = KnowledgeNodeInDB(
            node_id="doc_1_node_001",
            label="测试节点",
            content_summary="测试摘要",
            document_id=1,
            depth=0,
        )
        assert node.document_id == 1
        assert node.depth == 0
        assert node.created_at is not None

    def test_created_at_is_iso8601(self):
        """验证时间格式符合 ISO 8601 UTC 标准"""
        node = KnowledgeNodeInDB(
            node_id="doc_1_node_001",
            label="测试",
            content_summary="摘要",
            document_id=1,
        )
        # ISO 8601 格式必须以 Z 结尾
        assert node.created_at.endswith("Z")
        assert "T" in node.created_at


class TestKnowledgeTree:
    """测试完整知识树响应模型"""

    def test_empty_tree(self):
        """验证空树创建"""
        tree = KnowledgeTree(document_id=1)
        assert tree.document_id == 1
        assert tree.nodes == []
        assert tree.total_nodes == 0

    def test_tree_with_nodes(self):
        """验证带节点的树"""
        nodes = [
            KnowledgeNode(
                node_id="doc_1_node_001",
                label="根节点",
                parent_id=None,
                content_summary="根摘要",
            ),
            KnowledgeNode(
                node_id="doc_1_node_002",
                label="子节点",
                parent_id="doc_1_node_001",
                content_summary="子摘要",
            ),
        ]
        tree = KnowledgeTree(
            document_id=1,
            nodes=nodes,
            total_nodes=2,
        )
        assert len(tree.nodes) == 2
        assert tree.total_nodes == 2
