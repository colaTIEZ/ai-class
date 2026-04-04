"""苏格拉底提示输出模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class HintResult(BaseModel):
    """Tutor 节点输出。"""

    hint_text: str = Field(..., description="提示文本")
    hint_type: Literal["leading_question", "scaffold", "check_understanding", "example"] = Field(
        "leading_question", description="提示类型"
    )
    difficulty_level: Literal["easy", "medium", "hard"] = Field("medium")
    next_step_suggestion: str = Field("", description="下一步建议")
    hint_session_count: int = Field(1, ge=1, description="本题提示次数")
