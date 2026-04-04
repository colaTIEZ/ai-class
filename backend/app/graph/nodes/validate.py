"""答案验证节点。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.graph.nodes.llm_runtime import invoke_with_retry, parse_json_payload, truncate_tokens
from app.graph.prompts.validator_prompts import VALIDATOR_SYSTEM_PROMPT, VALIDATOR_USER_TEMPLATE
from app.graph.state import SocraticState
from app.schemas.validation import ValidationResult

MAX_ANSWER_TOKENS = 300


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
    question = state.get("current_question") or {}
    raw_student_answer = (state.get("current_answer") or "").strip()
    student_answer = truncate_tokens(raw_student_answer, MAX_ANSWER_TOKENS).strip()
    question_text = (question.get("question_text", "") or "").strip()
    correct_answer = (question.get("correct_answer", "") or "").strip()

    if error_message:
        trace_log.append(
            {
                "node": "validate",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {"skipped": True, "reason": error_message},
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
                "metadata": {"success": True, "fallback": True, "error_type": fallback.error_type},
            }
        )
        payload = fallback.model_dump()
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
                    "answer_truncated": student_answer != raw_student_answer,
                },
            }
        )
        payload = fallback.model_dump()
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
                        "answer_truncated": student_answer != raw_student_answer,
                    },
                }
            )
            payload = validation.model_dump()
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
                "answer_truncated": student_answer != raw_student_answer,
            },
        }
    )
    payload = validation.model_dump()
    payload["trace_log"] = trace_log[-20:]
    return {"validation_result": payload}
