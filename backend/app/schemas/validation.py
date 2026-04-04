"""答案验证输出模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Validator 节点输出。"""

    is_correct: bool = Field(..., description="答案是否正确")
    error_type: Literal[
        "no_error", "logic_gap", "conceptual", "calculation", "incomplete", "off_topic"
    ] = Field(..., description="错误类型分类")
    severity: int = Field(1, ge=1, le=3, description="错误严重程度，1-3")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="判断置信度")
    reasoning: str = Field("", description="简要判断依据")
    key_missing_concepts: list[str] = Field(default_factory=list)
    positive_aspects: list[str] = Field(default_factory=list)
    areas_for_improvement: list[str] = Field(default_factory=list)
