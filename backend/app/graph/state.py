"""LangGraph 状态定义模块

定义 Socratic 对话系统的核心状态架构，支持 Quiz 生成流程。
"""

from typing import TypedDict, Optional, Literal


class QuestionSchema(TypedDict):
    """生成的问题结构"""
    question_text: str
    options: Optional[list[str]]  # Multiple choice 时有值，short_answer 时为 None
    correct_answer: str


class TraceEntry(TypedDict):
    """追踪日志条目"""
    node: str
    timestamp: str
    metadata: dict


class SocraticState(TypedDict, total=False):
    """Socratic 对话系统的核心状态

    此状态通过 LangGraph StateGraph 管理，由 SQLite Checkpointer 持久化。
    设计支持 Epic 2 全部 stories：问题生成、答案验证、提示系统。

    Fields:
        selected_node_ids: 用户选择的知识图谱节点 ID 列表
        retrieved_chunks: 从向量数据库检索的相关文本块
        current_question: 当前生成的问题
        question_type: 问题类型 (multiple_choice / short_answer)
        trace_log: 技术可观测性追踪日志
        error_message: 错误信息（如果有）
        
    Future Extensions (Epic 2.2+):
        user_answer: 用户提交的答案
        answer_feedback: 答案评估反馈
        hints: 已提供的提示列表
        conversation_history: 对话历史
    """
    # Story 2.1: Bounded Question Generation
    selected_node_ids: list[str]
    retrieved_chunks: list[dict]  # [{"node_id": str, "chunk_text": str, "score": float}]
    current_question: Optional[QuestionSchema]
    question_type: Literal["multiple_choice", "short_answer"]
    current_answer: Optional[str]
    escape_action: Literal["continue", "show_answer", "skip"]
    current_node_id: Optional[str]
    validation_result: Optional[dict]
    error_type: Optional[str]
    current_hint: Optional[str]
    turn_count: int
    stagnation_score: float
    frustration_signals: list[str]
    guardrail_triggered: bool
    escape_hatch_visible: bool
    tutor_mode: Literal["socratic", "semi_transparent"]
    needs_review_node_ids: list[str]
    review_reason: Optional[str]
    context_summary: Optional[str]
    pruned_message_count: int
    conversation_history: list[dict]
    trace_log: list[TraceEntry]
    error_message: Optional[str]
