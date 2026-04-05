"""答案验证节点。"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.graph.nodes.llm_runtime import invoke_with_retry, parse_json_payload, truncate_tokens
from app.graph.prompts.validator_prompts import VALIDATOR_SYSTEM_PROMPT, VALIDATOR_USER_TEMPLATE
from app.graph.state import SocraticState
from app.schemas.validation import ValidationResult

LOGGER = logging.getLogger(__name__)

MAX_QUESTION_TOKENS = 300
MAX_ANSWER_TOKENS = 200
MAX_REASONING_TOKENS = 400

# Validate token budgets at module load
for _const_name, _const_val in [
    ("MAX_QUESTION_TOKENS", MAX_QUESTION_TOKENS),
    ("MAX_ANSWER_TOKENS", MAX_ANSWER_TOKENS),
    ("MAX_REASONING_TOKENS", MAX_REASONING_TOKENS),
]:
    if not isinstance(_const_val, int) or _const_val <= 0:
        raise ValueError(f"{_const_name} must be a positive integer, got {_const_val}")


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        model=settings.openai_model,
        temperature=0.3,
        timeout=10.0,
    )


def _rule_based_fallback(question_text: str, correct_answer: str, student_answer: str) -> ValidationResult:
    normalized_student = student_answer.lower()
    normalized_correct = correct_answer.lower()
    normalized_question = question_text.lower()

    if normalized_correct and normalized_student == normalized_correct:
        return ValidationResult(
            is_correct=True,
            error_type="no_error",
            severity=1,
            confidence=0.95,
            reasoning="Answer matches expected answer.",
            positive_aspects=["Correct final answer."],
        )
    if normalized_student in {"i don't know", "idk", "not sure", "pass"}:
        return ValidationResult(
            is_correct=False,
            error_type="incomplete",
            severity=1,
            confidence=0.7,
            reasoning="Student answer indicates missing completion.",
            areas_for_improvement=["State the missing key part before concluding."],
        )
    if any(token in normalized_student for token in ("because", "therefore", "so that")) and len(normalized_student) < max(
        len(normalized_correct), 12
    ):
        return ValidationResult(
            is_correct=False,
            error_type="logic_gap",
            severity=1,
            confidence=0.7,
            reasoning="Answer suggests reasoning is incomplete.",
            areas_for_improvement=["Explain the reasoning chain more fully."],
        )
    if any(ch.isdigit() for ch in normalized_student) and any(ch.isdigit() for ch in normalized_correct) and normalized_student != normalized_correct:
        return ValidationResult(
            is_correct=False,
            error_type="calculation",
            severity=2,
            confidence=0.8,
            reasoning="Numeric result does not match expected answer.",
            areas_for_improvement=["Recalculate the intermediate steps carefully."],
        )
    if normalized_question and normalized_student and normalized_student not in normalized_question and len(normalized_student.split()) <= 3:
        return ValidationResult(
            is_correct=False,
            error_type="off_topic",
            severity=1,
            confidence=0.65,
            reasoning="Answer appears unrelated or too generic for the question.",
            areas_for_improvement=["Address the specific concept asked in the question."],
        )
    return ValidationResult(
        is_correct=False,
        error_type="conceptual",
        severity=1,
        confidence=0.7,
        reasoning="Answer does not match expected answer.",
        areas_for_improvement=["Re-check core reasoning and key concept alignment."],
    )


def validate_answer_node(state: SocraticState) -> dict[str, Any]:
    trace_log = list(state.get("trace_log", []))
    error_message = state.get("error_message")
    question_raw = state.get("current_question")
    question = question_raw if isinstance(question_raw, dict) else {}
    raw_student_answer_value = state.get("current_answer")
    raw_student_answer = raw_student_answer_value if isinstance(raw_student_answer_value, str) else ""
    if raw_student_answer_value is not None and not isinstance(raw_student_answer_value, str):
        LOGGER.warning("validate_answer_node received non-string current_answer: %s", type(raw_student_answer_value).__name__)

    raw_student_answer = raw_student_answer.strip()
    student_answer_raw_truncated = truncate_tokens(raw_student_answer, MAX_ANSWER_TOKENS)
    student_answer = student_answer_raw_truncated.strip()
    answer_truncated = student_answer_raw_truncated != raw_student_answer

    question_text_raw = question.get("question_text", "") if isinstance(question.get("question_text", ""), str) else ""
    question_text = truncate_tokens(question_text_raw.strip(), MAX_QUESTION_TOKENS).strip()
    question_truncated = truncate_tokens(question_text_raw.strip(), MAX_QUESTION_TOKENS) != question_text_raw.strip()

    correct_answer_value = question.get("correct_answer", "")
    correct_answer = correct_answer_value.strip() if isinstance(correct_answer_value, str) else ""
    if correct_answer_value is not None and not isinstance(correct_answer_value, str):
        LOGGER.warning("validate_answer_node received non-string correct_answer: %s", type(correct_answer_value).__name__)

    truncation_warnings: list[str] = []
    if answer_truncated:
        truncation_warnings.append("student_answer_truncated")
        LOGGER.warning(
            "Student answer truncated from %s to %s tokens",
            len(raw_student_answer.split()),
            len(student_answer.split()),
        )
    if question_truncated:
        truncation_warnings.append("question_text_truncated")
        LOGGER.warning(
            "Question text truncated from %s to %s tokens",
            len(question_text_raw.split()),
            len(question_text.split()),
        )

    if error_message:
        trace_log.append(
            {
                "node": "validate",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "skipped": True,
                    "reason": error_message,
                    "warnings": truncation_warnings,
                },
            }
        )
        return {
            "validation_result": {
                "is_correct": False,
                "error_type": "incomplete",
                "severity": 1,
                "confidence": 0.5,
                "reasoning": f"Skipped due to previous error: {error_message}",
                "key_missing_concepts": [],
                "positive_aspects": [],
                "areas_for_improvement": [],
                "trace_log": trace_log[-20:],
            }
        }

    if raw_student_answer and not student_answer:
        fallback = ValidationResult(
            is_correct=False,
            error_type="incomplete",
            severity=1,
            confidence=0.5,
            reasoning="Student answer became empty after normalization/truncation.",
        )
        trace_log.append(
            {
                "node": "validate",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "success": True,
                    "fallback": True,
                    "reason": "student_answer_empty_after_truncation",
                    "warnings": truncation_warnings,
                },
            }
        )
        payload = fallback.model_dump()
        reasoning_value = payload.get("reasoning")
        reasoning_text = reasoning_value.strip() if isinstance(reasoning_value, str) else "Validation reasoning unavailable."
        payload["reasoning"] = truncate_tokens(reasoning_text, MAX_REASONING_TOKENS).strip() or "Validation reasoning unavailable."
        payload["trace_log"] = trace_log[-20:]
        return {"validation_result": payload}

    if not question_text or not student_answer:
        fallback = ValidationResult(
            is_correct=False,
            error_type="incomplete",
            severity=1,
            confidence=0.5,
            reasoning="Missing question or student answer.",
        )
        trace_log.append(
            {
                "node": "validate",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "success": True,
                    "fallback": True,
                    "error_type": fallback.error_type,
                    "warnings": truncation_warnings,
                },
            }
        )
        payload = fallback.model_dump()
        reasoning_value = payload.get("reasoning")
        reasoning_text = reasoning_value.strip() if isinstance(reasoning_value, str) else "Validation reasoning unavailable."
        payload["reasoning"] = truncate_tokens(reasoning_text, MAX_REASONING_TOKENS).strip() or "Validation reasoning unavailable."
        payload["trace_log"] = trace_log[-20:]
        return {"validation_result": payload}

    if not settings.embedding_ready:
        fallback = _rule_based_fallback(question_text, correct_answer, student_answer)
        trace_log.append(
            {
                "node": "validate",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "success": True,
                    "fallback": True,
                    "reason": "missing_openai_api_key",
                    "error_type": fallback.error_type,
                    "answer_truncated": answer_truncated,
                    "warnings": truncation_warnings,
                },
            }
        )
        payload = fallback.model_dump()
        reasoning_value = payload.get("reasoning")
        reasoning_text = reasoning_value.strip() if isinstance(reasoning_value, str) else "Validation reasoning unavailable."
        payload["reasoning"] = truncate_tokens(reasoning_text, MAX_REASONING_TOKENS).strip() or "Validation reasoning unavailable."
        payload["trace_log"] = trace_log[-20:]
        return {"validation_result": payload}

    user_prompt = VALIDATOR_USER_TEMPLATE.format(
        question=question_text,
        correct_answer=correct_answer,
        student_answer=student_answer,
    )

    try:
        llm = _build_llm()
        structured = llm.with_structured_output(ValidationResult)

        def _invoke_structured() -> ValidationResult:
            result = structured.invoke(
                [
                    {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )
            if isinstance(result, ValidationResult):
                return result
            if isinstance(result, dict):
                return ValidationResult.model_validate(result)
            raise ValueError("Unexpected structured output type")

        validation = invoke_with_retry(_invoke_structured)
    except Exception:
        try:
            llm = _build_llm()

            def _invoke_raw() -> ValidationResult:
                response = llm.invoke(
                    [
                        {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ]
                )
                data = parse_json_payload(str(response.content))
                return ValidationResult.model_validate(data)

            validation = invoke_with_retry(_invoke_raw)
        except (ValidationError, ValueError):
            validation = _rule_based_fallback(question_text, correct_answer, student_answer)
            trace_log.append(
                {
                    "node": "validate",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {
                        "success": True,
                        "fallback": True,
                        "reason": "llm_parse_failed",
                        "error_type": validation.error_type,
                        "answer_truncated": answer_truncated,
                        "warnings": truncation_warnings,
                    },
                }
            )
            payload = validation.model_dump()
            reasoning_value = payload.get("reasoning")
            reasoning_text = reasoning_value.strip() if isinstance(reasoning_value, str) else "Validation reasoning unavailable."
            payload["reasoning"] = truncate_tokens(reasoning_text, MAX_REASONING_TOKENS).strip() or "Validation reasoning unavailable."
            payload["trace_log"] = trace_log[-20:]
            return {"validation_result": payload}

    trace_log.append(
        {
            "node": "validate",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "success": True,
                "error_type": validation.error_type,
                "is_correct": validation.is_correct,
                "answer_truncated": answer_truncated,
                "warnings": truncation_warnings,
            },
        }
    )
    payload = validation.model_dump()
    reasoning_value = payload.get("reasoning")
    reasoning_text = reasoning_value.strip() if isinstance(reasoning_value, str) else "Validation reasoning unavailable."
    reasoning_truncated = truncate_tokens(reasoning_text, MAX_REASONING_TOKENS).strip()
    if reasoning_truncated != reasoning_text:
        LOGGER.warning(
            "Validation reasoning truncated from %s to %s tokens",
            len(reasoning_text.split()),
            len(reasoning_truncated.split()),
        )
    payload["reasoning"] = reasoning_truncated or "Validation reasoning unavailable."
    payload["trace_log"] = trace_log[-20:]
    return {"validation_result": payload}
