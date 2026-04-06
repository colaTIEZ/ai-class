"""LLM prompt contracts and structured output guard tests."""

import pytest
from pydantic import ValidationError

from app.core.llm_config import LLMConfig
from app.graph.nodes.hint import MAX_HINT_TOKENS
from app.graph.nodes.validate import MAX_ANSWER_TOKENS, MAX_QUESTION_TOKENS, MAX_REASONING_TOKENS
from app.graph.prompts.question_gen_prompts import QUESTION_GEN_SYSTEM_PROMPT
from app.graph.prompts.tutor_prompts import TUTOR_SYSTEM_PROMPT
from app.graph.prompts.validator_prompts import VALIDATOR_SYSTEM_PROMPT
from app.schemas.hint import HintResult
from app.schemas.validation import ValidationResult


def test_question_prompt_has_anti_hallucination_contract() -> None:
    assert "MUST ONLY use information from the provided context" in QUESTION_GEN_SYSTEM_PROMPT
    assert "DO NOT use any external knowledge" in QUESTION_GEN_SYSTEM_PROMPT
    assert "INSUFFICIENT_CONTEXT" in QUESTION_GEN_SYSTEM_PROMPT


def test_validator_prompt_declares_all_error_types() -> None:
    required_types = [
        "no_error",
        "logic_gap",
        "conceptual",
        "calculation",
        "incomplete",
        "off_topic",
    ]
    for value in required_types:
        assert value in VALIDATOR_SYSTEM_PROMPT


def test_tutor_prompt_has_socratic_constraints() -> None:
    assert "DO NOT reveal the final answer directly" in TUTOR_SYSTEM_PROMPT
    assert "Error-type strategy" in TUTOR_SYSTEM_PROMPT
    assert "logic_gap" in TUTOR_SYSTEM_PROMPT
    assert "off_topic" in TUTOR_SYSTEM_PROMPT


def test_validation_result_rejects_invalid_error_type() -> None:
    with pytest.raises(ValidationError):
        ValidationResult(
            is_correct=False,
            error_type="invalid_type",
            severity=1,
            confidence=0.8,
            reasoning="test",
        )


def test_hint_result_rejects_invalid_hint_type() -> None:
    with pytest.raises(ValidationError):
        HintResult(
            hint_text="test",
            hint_type="invalid_hint",
            difficulty_level="medium",
            next_step_suggestion="try again",
            hint_session_count=1,
        )


def test_llm_config_budget_is_wired_to_nodes() -> None:
    assert MAX_QUESTION_TOKENS == LLMConfig.QUESTION_CONTEXT_TOKENS
    assert MAX_ANSWER_TOKENS == LLMConfig.STUDENT_ANSWER_TOKENS
    assert MAX_REASONING_TOKENS == LLMConfig.VALIDATION_REASONING_TOKENS
    assert MAX_HINT_TOKENS == LLMConfig.HINT_GENERATION_TOKENS


def test_llm_config_budget_is_safe() -> None:
    assert LLMConfig.TOTAL_TOKENS_PER_REQUEST < LLMConfig.MAX_TOTAL_TOKENS
    assert 0.0 <= LLMConfig.TEMPERATURE <= 1.0
