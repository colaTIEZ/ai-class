"""RAG 检索节点

根据用户选择的知识节点 ID，从向量数据库检索相关文本块。
实现层级展开：选择父节点时自动包含所有子节点。
"""

from datetime import datetime
from typing import Any

from app.graph.state import SocraticState


def retrieve_node(state: SocraticState) -> dict[str, Any]:
    """检索节点：从向量数据库获取与选定节点相关的文本块

    实现上下文边界 RAG：
    1. 接收用户选择的 node_id 列表
    2. 展开到所有后代节点（层级展开）
    3. 检索相关 chunk_text
    4. 填充 retrieved_chunks 状态

    Args:
        state: 当前 Socratic 状态

    Returns:
        更新后的状态字段 (retrieved_chunks, trace_log, error_message)
    """
    from app.services.vector_store import retrieve_by_nodes
    
    selected_node_ids = state.get("selected_node_ids", [])
    trace_log = list(state.get("trace_log", []))
    
    # 输入验证
    if not selected_node_ids:
        trace_log.append({
            "node": "retrieve",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "error": "No node IDs provided",
                "chunks_retrieved": 0
            }
        })
        return {
            "retrieved_chunks": [],
            "trace_log": trace_log,
            "error_message": "No node IDs selected for quiz generation"
        }
    
    # 调用 vector_store 服务检索相关 chunks
    try:
        retrieved_chunks = retrieve_by_nodes(selected_node_ids, top_k=5)
        error_message = None
        
        # 安全检查：如果没有检索到 chunks，设置错误信息
        if not retrieved_chunks:
            error_message = "No relevant content found for selected nodes"
            
    except Exception as e:
        retrieved_chunks = []
        error_message = f"Retrieval failed: {str(e)}"
    
    # 添加追踪日志
    trace_log.append({
        "node": "retrieve",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {
            "selected_node_ids": selected_node_ids,
            "chunks_retrieved": len(retrieved_chunks),
            "error": error_message
        }
    })
    
    return {
        "retrieved_chunks": retrieved_chunks,
        "trace_log": trace_log,
        "error_message": error_message
    }
