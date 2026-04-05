"""问题生成节点

基于检索到的文本块，使用 LLM 生成测验问题。
严格遵循上下文边界，防止幻觉。
"""

from datetime import datetime
from typing import Any

from app.graph.state import SocraticState, QuestionSchema


def question_gen_node(state: SocraticState) -> dict[str, Any]:
    """问题生成节点：基于检索内容生成测验问题

    实现反幻觉问题生成：
    1. 检查前序节点是否有错误
    2. 格式化检索内容为上下文
    3. 调用 LLM 生成问题（仅使用上下文）
    4. 解析响应并更新状态

    Args:
        state: 当前 Socratic 状态

    Returns:
        更新后的状态字段 (current_question, trace_log, error_message)
    """
    from app.services.question_generator import generate_question
    
    retrieved_chunks = state.get("retrieved_chunks", [])
    question_type = state.get("question_type", "multiple_choice")
    trace_log = list(state.get("trace_log", []))
    error_message = state.get("error_message")
    
    # 如果前序节点有错误，不生成问题
    if error_message:
        trace_log.append({
            "node": "question_gen",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "skipped": True,
                "reason": error_message
            }
        })
        return {
            "current_question": None,
            "trace_log": trace_log
        }
    
    # 如果没有检索到内容，报错
    if not retrieved_chunks:
        trace_log.append({
            "node": "question_gen",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "error": "No chunks available for question generation",
                "success": False
            }
        })
        return {
            "current_question": None,
            "trace_log": trace_log,
            "error_message": "No content available to generate questions"
        }
    
    # 调用问题生成服务
    try:
        question = generate_question(retrieved_chunks, question_type)
        source_node_id = None
        if retrieved_chunks and isinstance(retrieved_chunks[0], dict):
            source_node_id = retrieved_chunks[0].get("node_id")
            if not isinstance(source_node_id, str) or not source_node_id.strip():
                source_node_id = None

        if source_node_id:
            question["current_node_id"] = source_node_id
        
        trace_log.append({
            "node": "question_gen",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "question_type": question_type,
                "chunks_used": len(retrieved_chunks),
                "question_length": len(question["question_text"]),
                "has_options": question.get("options") is not None,
                "source_node_id": source_node_id,
                "success": True
            }
        })
        
        return {
            "current_question": question,
            "trace_log": trace_log
        }
        
    except Exception as e:
        error_msg = f"Question generation failed: {str(e)}"
        trace_log.append({
            "node": "question_gen",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "error": str(e),
                "question_type": question_type,
                "chunks_used": len(retrieved_chunks),
                "success": False
            }
        })
        
        return {
            "current_question": None,
            "trace_log": trace_log,
            "error_message": error_msg
        }
