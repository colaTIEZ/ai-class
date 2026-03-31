"""知识树数据契约 - 前后端共享的严格数据结构定义

此模块定义了从 PDF 中提取的知识点层级结构的数据格式。
前端的 AntV G6 图可视化和后端的 RAG 检索都严格依赖此契约。
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class KnowledgeNode(BaseModel):
    """单个知识节点的数据模型

    通过 parent_id 构建 Chapter -> Section -> Chunk 的层级关系。
    """

    node_id: str = Field(
        ...,
        description="节点唯一标识符，格式: doc_{document_id}_node_{序号}",
        examples=["doc_1_node_001"],
    )
    label: str = Field(
        ...,
        description="节点展示标签（章节/知识点名称）",
        examples=["第一章：线性代数基础"],
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="父节点 ID，根节点为 None",
        examples=["doc_1_node_000"],
    )
    content_summary: str = Field(
        ...,
        description="节点内容摘要，用于前端预览和 RAG 上下文检索",
        examples=["本章介绍矩阵运算、特征值分解等核心概念"],
    )


class KnowledgeNodeInDB(KnowledgeNode):
    """数据库中存储的知识节点，包含额外的元数据字段"""

    document_id: int = Field(..., description="所属文档 ID")
    depth: int = Field(default=0, description="节点在树中的深度层级，0 为根节点")
    chunk_text: Optional[str] = Field(
        default=None, description="完整文本块内容，用于生成嵌入向量"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        description="创建时间，ISO 8601 UTC 格式",
    )


class KnowledgeTree(BaseModel):
    """完整知识树响应模型"""

    document_id: int = Field(..., description="文档 ID")
    nodes: list[KnowledgeNode] = Field(
        default_factory=list, description="知识节点列表"
    )
    total_nodes: int = Field(default=0, description="节点总数")
