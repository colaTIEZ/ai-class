"""Quiz 相关的 Pydantic 模型

定义 Quiz API 的请求和响应模式。
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class QuizInitRequest(BaseModel):
    """Quiz 初始化请求"""
    selected_node_ids: list[str] = Field(
        ...,
        min_length=1,
        description="用户选择的知识图谱节点 ID 列表"
    )
    question_type: Literal["multiple_choice", "short_answer"] = Field(
        default="multiple_choice",
        description="问题类型：多选题或简答题"
    )


class QuestionData(BaseModel):
    """生成的问题数据"""
    question_text: str = Field(..., description="问题文本")
    options: Optional[list[str]] = Field(
        default=None,
        description="选项列表（多选题时有值）"
    )
    correct_answer: str = Field(..., description="正确答案")


class QuizInitResponseData(BaseModel):
    """Quiz 初始化响应数据"""
    question: QuestionData
    question_type: str


class QuizInitResponse(BaseModel):
    """Quiz 初始化响应 - 标准信封格式"""
    status: Literal["success", "error"] = "success"
    data: Optional[QuizInitResponseData] = None
    message: Optional[str] = None
    trace_id: str = Field(..., description="追踪 ID")


class ErrorResponse(BaseModel):
    """错误响应 - 标准信封格式"""
    status: Literal["error"] = "error"
    data: None = None
    message: str
    trace_id: Optional[str] = None
