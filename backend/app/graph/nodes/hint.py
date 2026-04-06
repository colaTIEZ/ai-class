"""苏格拉底提示节点。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.core.llm_config import LLMConfig
from app.graph.nodes.llm_runtime import invoke_with_retry, parse_json_payload, truncate_tokens
from app.graph.prompts.tutor_prompts import TUTOR_SYSTEM_PROMPT, TUTOR_USER_TEMPLATE
from app.graph.state import SocraticState
from app.schemas.hint import HintResult


MAX_HINT_TOKENS = LLMConfig.HINT_GENERATION_TOKENS

# Validate token budget at module load
if not isinstance(MAX_HINT_TOKENS, int) or MAX_HINT_TOKENS <= 0:
    raise ValueError(f"MAX_HINT_TOKENS must be a positive integer, got {MAX_HINT_TOKENS}")


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        model=settings.openai_model,
        temperature=LLMConfig.TEMPERATURE,
        timeout=LLMConfig.TIMEOUT_SECONDS,
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
    tutor_mode = state.get("tutor_mode", "socratic")
    if tutor_mode not in {"socratic", "semi_transparent"}:
        tutor_mode = "socratic"

    if error_message:
        trace_log.append(
            {
                "node": "socratic_hint",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {"skipped": True, "reason": error_message},
            }
        )
        return {"current_hint": "", "trace_log": trace_log}

    validation_error_type = validation.get("error_type")
    if not isinstance(validation_error_type, str):
        validation_error_type = str(validation_error_type) if validation_error_type else "logic_gap"
    error_type = validation_error_type
    
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
        return {"current_hint": truncate_tokens(hint.hint_text, MAX_HINT_TOKENS), "trace_log": trace_log}

    user_prompt = TUTOR_USER_TEMPLATE.format(
        question=question_text,
        student_answer=student_answer,
        error_type=error_type,
        reasoning=reasoning,
        missing=", ".join(str(item) for item in missing),
        tutor_mode=tutor_mode,
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

        hint = invoke_with_retry(
            _invoke_structured,
            max_attempts=LLMConfig.MAX_RETRIES,
            base_delay_seconds=LLMConfig.RETRY_BASE_WAIT_SECONDS,
        )
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

            hint = invoke_with_retry(
                _invoke_raw,
                max_attempts=LLMConfig.MAX_RETRIES,
                base_delay_seconds=LLMConfig.RETRY_BASE_WAIT_SECONDS,
            )
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
                        "tutor_mode": tutor_mode,
                    },
                }
            )
            return {"current_hint": truncate_tokens(hint.hint_text, MAX_HINT_TOKENS), "trace_log": trace_log}

    if tutor_mode == "semi_transparent":
        # Semi-transparent mode gives direct direction but still avoids dumping full derivations.
        hint_text = hint.hint_text.strip()
        if hint_text:
            hint.hint_text = f"Direct guidance: {hint_text}"

    trace_log.append(
        {
            "node": "socratic_hint",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"success": True, "error_type": error_type, "hint_type": hint.hint_type, "tutor_mode": tutor_mode},
        }
    )
    return {"current_hint": truncate_tokens(hint.hint_text, MAX_HINT_TOKENS), "trace_log": trace_log}
