"""Wrong-answer notebook schemas.

These models define the strict API contract for grouped review data.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class WrongAnswerQuestion(BaseModel):
    """Single wrong-answer record used inside a node group."""

    question_record_id: str = Field(..., description="Unique answer record ID")
    question_id: Optional[str] = Field(default=None, description="Original question ID")
    node_id: str = Field(..., description="Knowledge node ID")
    question_text: str = Field(..., description="Question text")
    user_answer: str = Field(..., description="Student answer")
    correct_answer: str = Field(..., description="Correct answer")
    error_type: str = Field(..., description="Validation error classification")
    error_severity: int = Field(..., ge=1, le=3, description="Error severity 1-3")
    question_type: Literal["multiple_choice", "short_answer"] = Field(
        default="multiple_choice",
        description="Question type",
    )
    attempted_at: str = Field(..., description="ISO 8601 timestamp")
    is_invalidated: bool = Field(default=False, description="Hallucination flag")


class WrongAnswerNodeGroup(BaseModel):
    """Grouped wrong answers for one knowledge node."""

    node_id: str = Field(..., description="Knowledge node ID")
    node_label: str = Field(..., description="Knowledge node label")
    total_errors: int = Field(..., ge=0, description="Number of wrong answers")
    questions: list[WrongAnswerQuestion] = Field(default_factory=list)


class WrongAnswersSummary(BaseModel):
    """Aggregate wrong-answer summary."""

    total_wrong_count: int = Field(..., ge=0)
    total_nodes_with_errors: int = Field(..., ge=0)


class WrongAnswersData(BaseModel):
    """Data payload for the wrong-answer notebook."""

    by_node: list[WrongAnswerNodeGroup] = Field(default_factory=list)
    summary: WrongAnswersSummary


class WrongAnswersResponse(BaseModel):
    """Standard response envelope for the review API."""

    status: Literal["success", "error"] = Field(default="success")
    data: Optional[WrongAnswersData] = Field(default=None)
    message: str = Field(default="")
    trace_id: str = Field(default="")
