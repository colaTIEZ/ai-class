"""Chat 和 Quiz 路由

实现 Quiz 初始化 API，触发 LangGraph 编排的问题生成流程。
"""

import json
import logging
import uuid
from datetime import datetime
from time import perf_counter
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas.quiz import (
    QuizInitRequest,
    QuizInitResponse,
    QuizInitResponseData,
    QuestionData,
    ErrorResponse,
    AnswerSubmitRequest,
)
from app.graph.orchestrator import (
    build_answer_feedback_graph,
    create_checkpointer,
    create_connection,
    invoke_quiz_generation,
)
from app.services.vector_store import mark_node_needs_review

logger = logging.getLogger(__name__)

router = APIRouter()


def _error_response(status_code: int, message: str, trace_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "data": None,
            "message": message,
            "trace_id": trace_id,
        },
    )


@router.post(
    "/quiz/init",
    response_model=QuizInitResponse,
    responses={
        400: {"model": ErrorResponse, "description": "无效请求"},
        500: {"model": ErrorResponse, "description": "服务器错误"}
    },
    summary="初始化 Quiz",
    description="根据用户选择的知识节点生成测验问题"
)
async def init_quiz(request: QuizInitRequest) -> QuizInitResponse:
    """初始化 Quiz 会话
    
    接收用户选择的节点 ID 列表，触发 LangGraph 流程：
    1. 检索相关文本块（上下文边界 RAG）
    2. 使用 LLM 生成测验问题
    3. 返回生成的问题
    
    Args:
        request: Quiz 初始化请求，包含选中的节点 ID
        
    Returns:
        QuizInitResponse: 包含生成问题的响应
        
    Raises:
        400/500 错误响应信封
    """
    # 生成追踪 ID
    trace_id = str(uuid.uuid4())
    
    # 验证输入
    if not request.selected_node_ids:
        return _error_response(400, "At least one node ID must be selected", trace_id)
    
    logger.info(
        f"Quiz init request: nodes={request.selected_node_ids}, "
        f"type={request.question_type}, trace_id={trace_id}"
    )
    
    try:
        # 调用 LangGraph 编排器
        result = invoke_quiz_generation(
            selected_node_ids=request.selected_node_ids,
            question_type=request.question_type,
            thread_id=trace_id
        )
        
        state = result["state"]
        
        # 检查是否有错误
        if state.get("error_message"):
            logger.warning(f"Quiz generation error: {state['error_message']}")
            return _error_response(500, state["error_message"], trace_id)
        
        # 检查是否生成了问题
        current_question = state.get("current_question")
        if not current_question:
            return _error_response(500, "Failed to generate question", trace_id)
        
        # 构建响应
        question_data = QuestionData(
            question_text=current_question["question_text"],
            options=current_question.get("options"),
            correct_answer=current_question["correct_answer"]
        )
        
        response_data = QuizInitResponseData(
            question=question_data,
            question_type=state.get("question_type", request.question_type)
        )
        
        logger.info(f"Quiz generated successfully: trace_id={trace_id}")
        
        return QuizInitResponse(
            status="success",
            data=response_data,
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.exception(f"Quiz generation failed: {e}")
        return _error_response(500, f"Internal server error: {str(e)}", trace_id)


def _sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _project_trace_entry(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None

    node_name = entry.get("node_name") or entry.get("node") or "unknown"
    metadata = entry.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "node_name": str(node_name),
        "metadata": metadata,
    }


def _extract_trace_entry(node_update: Any) -> dict[str, Any] | None:
    if not isinstance(node_update, dict):
        return None

    trace_log = node_update.get("trace_log")
    if isinstance(trace_log, list) and trace_log:
        return _project_trace_entry(trace_log[-1])

    validation_result = node_update.get("validation_result")
    if isinstance(validation_result, dict):
        nested_trace_log = validation_result.get("trace_log")
        if isinstance(nested_trace_log, list) and nested_trace_log:
            return _project_trace_entry(nested_trace_log[-1])

    return None


@router.post(
    "/chat/message",
    summary="提交答案并流式返回苏格拉底提示",
    description="验证学生答案并通过 SSE 返回 content/trace/error 事件",
)
async def submit_answer_stream(request: AnswerSubmitRequest) -> StreamingResponse:
    trace_id = str(uuid.uuid4())

    async def event_generator():
        started = perf_counter()
        try:
            current_question = request.current_question.model_dump()
            initial_state = {
                "selected_node_ids": request.selected_node_ids,
                "retrieved_chunks": [],
                "current_question": current_question,
                "question_type": request.question_type,
                "current_answer": request.current_answer,
                "escape_action": request.action or "continue",
                "current_node_id": request.current_node_id or request.current_question.current_node_id,
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
                "trace_log": [
                    {
                        "node": "init_answer_feedback",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "metadata": {
                            "thread_id": trace_id,
                            "question_type": request.question_type,
                            "escape_action": request.action or "continue",
                        },
                    }
                ],
                "error_message": None,
            }

            with create_connection() as conn:
                workflow = build_answer_feedback_graph()
                checkpointer = create_checkpointer(conn)
                graph = workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": trace_id}}

                yield _sse_data(
                    {
                        "type": "trace",
                        "data": {
                            "node_name": "init_answer_feedback",
                            "metadata": {
                                "thread_id": trace_id,
                                "question_type": request.question_type,
                                "escape_action": request.action or "continue",
                            },
                        },
                        "trace_id": trace_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )

                state: dict[str, Any] = dict(initial_state)
                validation: dict[str, Any] = {}

                for chunk in graph.stream(initial_state, config, stream_mode="updates"):
                    if not isinstance(chunk, dict):
                        continue

                    for node_name, node_update in chunk.items():
                        if not isinstance(node_update, dict):
                            continue
                        state.update(node_update)

                        projected = _extract_trace_entry(node_update)
                        if projected is None:
                            continue

                        trace_node_name = str(node_name)
                        yield _sse_data(
                            {
                                "type": "trace",
                                "data": {
                                    "node_name": trace_node_name,
                                    "metadata": projected["metadata"],
                                },
                                "trace_id": trace_id,
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                            }
                        )

                        if node_name == "validate":
                            validation = state.get("validation_result") or {}

                hint = state.get("current_hint")
                tutor_mode = str(state.get("tutor_mode") or "socratic")
                escape_hatch_visible = state.get("escape_hatch_visible") is True
                needs_review_queued = bool(state.get("needs_review_node_ids")) or bool(state.get("review_reason"))
                guardrail_reason = ",".join(state.get("frustration_signals", []))

                if request.action == "skip" and needs_review_queued:
                    review_reason = str(state.get("review_reason") or "user_skipped_after_guardrail")
                    for node_id in state.get("needs_review_node_ids", []):
                        if isinstance(node_id, str) and node_id.strip():
                            mark_node_needs_review(trace_id, node_id, review_reason)

                if state.get("error_message"):
                    yield _sse_data(
                        {
                            "type": "error",
                            "data": {"message": state["error_message"], "code": "VALIDATION_ERROR"},
                            "trace_id": trace_id,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )
                    return

                if isinstance(hint, str) and hint.strip():
                    yield _sse_data(
                        {
                            "type": "content",
                            "data": {
                                "text": hint,
                                "hint_type": "scaffold" if tutor_mode == "semi_transparent" else "leading_question",
                                "tutor_mode": tutor_mode,
                                "escape_hatch_visible": escape_hatch_visible,
                                "guardrail_reason": guardrail_reason,
                                "needs_review_queued": needs_review_queued,
                            },
                            "trace_id": trace_id,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )
                elif validation.get("is_correct") is False:
                    yield _sse_data(
                        {
                            "type": "content",
                            "data": {
                                "text": "Your answer is not quite there yet. Try focusing on the core concept again.",
                                "hint_type": "leading_question",
                                "tutor_mode": tutor_mode,
                                "escape_hatch_visible": escape_hatch_visible,
                                "guardrail_reason": guardrail_reason,
                                "needs_review_queued": needs_review_queued,
                            },
                            "trace_id": trace_id,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )
                elif validation.get("is_correct") is True:
                    yield _sse_data(
                        {
                            "type": "content",
                            "data": {
                                "text": "Great job! Your answer is correct.",
                                "hint_type": "check_understanding",
                                "tutor_mode": tutor_mode,
                                "escape_hatch_visible": escape_hatch_visible,
                                "guardrail_reason": guardrail_reason,
                                "needs_review_queued": needs_review_queued,
                            },
                            "trace_id": trace_id,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )

                first_byte_latency_ms = int((perf_counter() - started) * 1000)
                yield _sse_data(
                    {
                        "type": "trace",
                        "data": {
                            "node_name": "sse",
                            "metadata": {
                                "first_byte_latency_ms": first_byte_latency_ms,
                            },
                        },
                        "trace_id": trace_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )
        except Exception as e:
            logger.exception("submit_answer_stream failed: %s", e)
            yield _sse_data(
                {
                    "type": "error",
                    "data": {"message": "Unable to generate hint, please retry.", "code": "INTERNAL_ERROR"},
                    "trace_id": trace_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
