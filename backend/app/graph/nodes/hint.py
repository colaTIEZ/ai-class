"""苏格拉底提示节点。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.graph.nodes.llm_runtime import invoke_with_retry, parse_json_payload
from app.graph.prompts.tutor_prompts import TUTOR_SYSTEM_PROMPT, TUTOR_USER_TEMPLATE
from app.graph.state import SocraticState
from app.schemas.hint import HintResult


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        model=settings.openai_model,
        temperature=0.3,
        timeout=10.0,
    )


def _fallback_hint(error_type: str, question_text: str) -> HintResult:
    if error_type == "incomplete":
        hint_text = f"You are close. Which key part of '{question_text}' is still missing in your answer?"
        hint_type = "check_understanding"
    elif error_type == "off_topic":
        hint_text = f"Try to focus on the exact requirement in '{question_text}'. What is it asking directly?"
        hint_type = "leading_question"
    elif error_type == "calculation":
        hint_text = "Re-check your intermediate steps. Which step could have introduced the numeric error?"
        hint_type = "scaffold"
    else:
        hint_text = "Think about the core concept first. Which definition or principle best supports your conclusion?"
        hint_type = "leading_question"
    return HintResult(
        hint_text=hint_text,
        hint_type=hint_type,
        difficulty_level="medium",
        next_step_suggestion="Revise your answer using the hint and try again.",
        hint_session_count=1,
    )


def generate_hint_node(state: SocraticState) -> dict[str, Any]:
    trace_log = list(state.get("trace_log", []))
    error_message = state.get("error_message")
    validation = state.get("validation_result") or {}
    question = state.get("current_question") or {}
    student_answer = (state.get("current_answer") or "").strip()

    if error_message:
        trace_log.append(
            {
                "node": "socratic_hint",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {"skipped": True, "reason": error_message},
            }
        )
        return {"current_hint": ""}

    error_type = str(validation.get("error_type", "logic_gap"))
    question_text = str(question.get("question_text", "this question"))
    reasoning = str(validation.get("reasoning", ""))
    missing = validation.get("key_missing_concepts", [])
    if not isinstance(missing, list):
        missing = []

    if not settings.embedding_ready:
        hint = _fallback_hint(error_type, question_text)
        trace_log.append(
            {
                "node": "socratic_hint",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "success": True,
                    "fallback": True,
                    "reason": "missing_openai_api_key",
                    "error_type": error_type,
                    "hint_type": hint.hint_type,
                },
            }
        )
        return {"current_hint": hint.hint_text}

    user_prompt = TUTOR_USER_TEMPLATE.format(
        question=question_text,
        student_answer=student_answer,
        error_type=error_type,
        reasoning=reasoning,
        missing=", ".join(str(item) for item in missing),
    )

    try:
        llm = _build_llm()
        structured = llm.with_structured_output(HintResult)

        def _invoke_structured() -> HintResult:
            result = structured.invoke(
                [
                    {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )
            if isinstance(result, HintResult):
                return result
            if isinstance(result, dict):
                return HintResult.model_validate(result)
            raise ValueError("Unexpected structured output type")

        hint = invoke_with_retry(_invoke_structured)
    except Exception:
        try:
            llm = _build_llm()

            def _invoke_raw() -> HintResult:
                response = llm.invoke(
                    [
                        {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ]
                )
                data = parse_json_payload(str(response.content))
                return HintResult.model_validate(data)

            hint = invoke_with_retry(_invoke_raw)
        except (ValidationError, ValueError):
            hint = _fallback_hint(error_type, question_text)
            trace_log.append(
                {
                    "node": "socratic_hint",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {
                        "success": True,
                        "fallback": True,
                        "reason": "llm_parse_failed",
                        "error_type": error_type,
                        "hint_type": hint.hint_type,
                    },
                }
            )
            return {"current_hint": hint.hint_text}

    trace_log.append(
        {
            "node": "socratic_hint",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"success": True, "error_type": error_type, "hint_type": hint.hint_type},
        }
    )
    return {"current_hint": hint.hint_text}
