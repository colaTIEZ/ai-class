"""LangGraph 编排器模块

负责构建和执行 StateGraph，管理 Quiz 生成流程。
使用 SQLite Checkpointer 实现状态持久化。
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.core.config import settings
from app.graph.state import SocraticState
from app.graph.nodes.retrieve import retrieve_node
from app.graph.nodes.question_gen import question_gen_node
from app.graph.nodes.validate import validate_answer_node
from app.graph.nodes.hint import generate_hint_node
from app.graph.nodes.guardrails import evaluate_guardrails_node
from app.graph.nodes.prune import prune_context_node
from app.graph.nodes.escape import apply_escape_hatch_node


def get_checkpointer_path() -> str:
    """获取 checkpointer 数据库路径"""
    db_dir = Path(settings.database_path).parent
    return str(db_dir / "langgraph_checkpoint.db")


def create_connection() -> sqlite3.Connection:
    """创建 SQLite 连接用于 checkpointer
    
    Returns:
        sqlite3.Connection: 配置好的数据库连接
    """
    path = get_checkpointer_path()
    # 确保目录存在
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # 使用 check_same_thread=False 支持多线程访问
    return sqlite3.connect(path, check_same_thread=False)


def create_checkpointer(conn: Optional[sqlite3.Connection] = None) -> SqliteSaver:
    """创建 SQLite checkpointer 用于状态持久化
    
    Args:
        conn: 可选的已有连接。如未提供则创建新连接。
        
    Returns:
        SqliteSaver: 配置好的 checkpointer 实例
    """
    if conn is None:
        conn = create_connection()
    return SqliteSaver(conn)


def build_quiz_graph() -> StateGraph:
    """构建 Quiz 生成的 StateGraph

    流程:
        START -> retrieve -> question_gen -> END

    Returns:
        编译后的 StateGraph
    """
    # 创建 StateGraph
    workflow = StateGraph(SocraticState)

    # 添加节点
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("question_gen", question_gen_node)

    # 定义边
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "question_gen")
    workflow.add_edge("question_gen", END)

    return workflow


def build_answer_feedback_graph() -> StateGraph:
    """构建答题反馈图：validate -> guardrails -> prune/escape/hint/end。"""
    workflow = StateGraph(SocraticState)
    workflow.add_node("validate", validate_answer_node)
    workflow.add_node("guardrails", evaluate_guardrails_node)
    workflow.add_node("prune", prune_context_node)
    workflow.add_node("escape_action", apply_escape_hatch_node)
    workflow.add_node("socratic_hint", generate_hint_node)

    def route_after_guardrails(state: SocraticState) -> str:
        action = state.get("escape_action", "continue")
        if action in {"show_answer", "skip"}:
            return "escape_action"

        validation = state.get("validation_result") or {}
        is_correct = validation.get("is_correct") is True
        if is_correct:
            return END

        guardrail_triggered = state.get("guardrail_triggered") is True
        return "prune" if guardrail_triggered else "socratic_hint"

    def route_after_prune(state: SocraticState) -> str:
        validation = state.get("validation_result") or {}
        return END if validation.get("is_correct") is True else "socratic_hint"

    workflow.add_edge(START, "validate")
    workflow.add_edge("validate", "guardrails")
    workflow.add_conditional_edges("guardrails", route_after_guardrails)
    workflow.add_conditional_edges("prune", route_after_prune)
    workflow.add_edge("escape_action", END)
    workflow.add_edge("socratic_hint", END)
    return workflow


def compile_graph(checkpointer: Optional[SqliteSaver] = None) -> StateGraph:
    """编译 StateGraph 并绑定 checkpointer

    Args:
        checkpointer: 可选的 checkpointer 实例。如未提供则创建新实例。

    Returns:
        编译后的可执行 graph
    """
    workflow = build_quiz_graph()
    
    if checkpointer is None:
        checkpointer = create_checkpointer()
    
    return workflow.compile(checkpointer=checkpointer)


def invoke_quiz_generation(
    selected_node_ids: list[str],
    question_type: str = "multiple_choice",
    thread_id: Optional[str] = None
) -> dict:
    """执行 Quiz 生成流程

    Args:
        selected_node_ids: 用户选择的知识节点 ID 列表
        question_type: 问题类型 (multiple_choice / short_answer)
        thread_id: 可选的线程 ID，用于状态持久化

    Returns:
        包含生成问题和追踪信息的结果字典
    """
    import uuid
    
    # 生成 thread_id 用于状态追踪
    if thread_id is None:
        thread_id = str(uuid.uuid4())
    
    # 初始化状态
    initial_state: SocraticState = {
        "selected_node_ids": selected_node_ids,
        "retrieved_chunks": [],
        "current_question": None,
        "question_type": question_type,
        "trace_log": [{
            "node": "init",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "selected_node_ids": selected_node_ids,
                "question_type": question_type
            }
        }],
        "error_message": None
    }
    
    with create_connection() as conn:
        checkpointer = create_checkpointer(conn)
        graph = compile_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(initial_state, config)
    
    return {
        "state": result,
        "thread_id": thread_id
    }


def invoke_answer_feedback(
    *,
    thread_id: str,
    selected_node_ids: list[str],
    question_type: str,
    current_answer: str,
    current_question: dict,
    escape_action: str = "continue",
    current_node_id: str | None = None,
) -> dict:
    """执行答题反馈流程（验证+路由+提示）。"""
    initial_state: SocraticState = {
        "selected_node_ids": selected_node_ids,
        "retrieved_chunks": [],
        "current_question": current_question,
        "question_type": question_type,
        "current_answer": current_answer,
        "escape_action": escape_action,
        "current_node_id": current_node_id,
        "validation_result": None,
        "error_type": None,
        "current_hint": None,
        "turn_count": 0,
        "stagnation_score": 0.0,
        "frustration_signals": [],
        "guardrail_triggered": False,
        "escape_hatch_visible": False,
        "tutor_mode": "socratic",
        "needs_review_node_ids": [],
        "review_reason": None,
        "context_summary": None,
        "pruned_message_count": 0,
        "conversation_history": [],
        "trace_log": [{
            "node": "init_answer_feedback",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "thread_id": thread_id,
                "question_type": question_type,
                "escape_action": escape_action,
            }
        }],
        "error_message": None,
    }
    with create_connection() as conn:
        workflow = build_answer_feedback_graph()
        checkpointer = create_checkpointer(conn)
        graph = workflow.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.invoke(initial_state, config)
    return {"state": state, "thread_id": thread_id}
