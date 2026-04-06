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


class ChapterMasteryItem(BaseModel):
    """Mastery stats grouped by one parent chapter."""

    parent_id: str = Field(..., description="Parent chapter node ID")
    parent_label: str = Field(..., description="Parent chapter label")
    attempted_count: int = Field(..., ge=0)
    correct_count: int = Field(..., ge=0)
    mastery_score: float = Field(..., ge=0.0, le=1.0)


class ChapterMasterySummary(BaseModel):
    """Aggregate summary for chapter mastery."""

    total_parents: int = Field(..., ge=0)
    total_attempted: int = Field(..., ge=0)
    total_correct: int = Field(..., ge=0)
    overall_mastery_score: float = Field(..., ge=0.0, le=1.0)


class ChapterMasteryData(BaseModel):
    """Data payload for chapter mastery metrics."""

    by_parent: list[ChapterMasteryItem] = Field(default_factory=list)
    summary: ChapterMasterySummary


class ChapterMasteryResponse(BaseModel):
    """Standard response envelope for chapter mastery API."""

    status: Literal["success", "error"] = Field(default="success")
    data: Optional[ChapterMasteryData] = Field(default=None)
    message: str = Field(default="")
    trace_id: str = Field(default="")


class InvalidateQuestionRequest(BaseModel):
    """Request payload to invalidate one question record."""

    question_record_id: str = Field(..., min_length=1)
    reason: Optional[str] = Field(default=None, max_length=500)


class InvalidateQuestionData(BaseModel):
    """Mutation result details for an invalidation request."""

    question_record_id: str = Field(...)
    found: bool = Field(...)
    updated: bool = Field(...)
    already_invalidated: bool = Field(...)
    invalidated_at: Optional[str] = Field(default=None)


class InvalidateQuestionResponse(BaseModel):
    """Standard response envelope for question invalidation."""

    status: Literal["success", "error"] = Field(default="success")
    data: Optional[InvalidateQuestionData] = Field(default=None)
    message: str = Field(default="")
    trace_id: str = Field(default="")
