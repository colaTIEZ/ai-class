"""Chat 和 Quiz 路由

实现 Quiz 初始化 API，触发 LangGraph 编排的问题生成流程。
"""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.quiz import (
    QuizInitRequest,
    QuizInitResponse,
    QuizInitResponseData,
    QuestionData,
    ErrorResponse
)
from app.graph.orchestrator import invoke_quiz_generation

logger = logging.getLogger(__name__)

router = APIRouter()


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
        HTTPException: 400 - 无效请求（无节点选择）
        HTTPException: 500 - LLM 或数据库错误
    """
    # 生成追踪 ID
    trace_id = str(uuid.uuid4())
    
    # 验证输入
    if not request.selected_node_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "At least one node ID must be selected",
                "trace_id": trace_id
            }
        )
    
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
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": state["error_message"],
                    "trace_id": trace_id
                }
            )
        
        # 检查是否生成了问题
        current_question = state.get("current_question")
        if not current_question:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": "Failed to generate question",
                    "trace_id": trace_id
                }
            )
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Quiz generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Internal server error: {str(e)}",
                "trace_id": trace_id
            }
        )