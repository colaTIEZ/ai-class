"""Context guardrail detector node."""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from app.graph.state import SocraticState

FRUSTRATION_KEYWORDS = (
    "i don't know",
    "idk",
    "too hard",
    "skip",
    "stuck",
    "not sure",
    "不会",
    "太难",
    "跳过",
)

STAGNATION_THRESHOLD = 0.92


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _extract_recent_answers(state: SocraticState) -> list[str]:
    history = state.get("conversation_history", [])
    answers: list[str] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role == "student" and isinstance(content, str):
            normalized = _normalize(content)
            if normalized:
                answers.append(normalized)
    current = state.get("current_answer")
    if isinstance(current, str):
        normalized = _normalize(current)
        if normalized:
            answers.append(normalized)
    return answers[-3:]


def _compute_stagnation_score(answers: list[str]) -> float:
    if len(answers) < 3:
        return 0.0
    ratios = [
        SequenceMatcher(a=answers[0], b=answers[1]).ratio(),
        SequenceMatcher(a=answers[1], b=answers[2]).ratio(),
        SequenceMatcher(a=answers[0], b=answers[2]).ratio(),
    ]
    return round(sum(ratios) / len(ratios), 4)


def evaluate_guardrails_node(state: SocraticState) -> dict[str, Any]:
    trace_log = list(state.get("trace_log", []))
    history = state.get("conversation_history", [])
    current_answer = state.get("current_answer")
    escape_action = state.get("escape_action", "continue")

    turn_count = state.get("turn_count", 0)
    if not isinstance(turn_count, int) or turn_count < 0:
        turn_count = 0

    # Treat one submit as one turn even if history persistence is unavailable.
    computed_turn_count = max(turn_count, len(history) + 1)

    normalized_answer = _normalize(current_answer) if isinstance(current_answer, str) else ""
    frustration_signals = [kw for kw in FRUSTRATION_KEYWORDS if kw in normalized_answer]

    recent_answers = _extract_recent_answers(state)
    stagnation_score = _compute_stagnation_score(recent_answers)

    guardrail_triggered = bool(
        frustration_signals
        or stagnation_score >= STAGNATION_THRESHOLD
        or computed_turn_count > 5
    )
    tutor_mode = "semi_transparent" if guardrail_triggered else "socratic"

    trigger_reasons: list[str] = []
    if escape_action in {"show_answer", "skip"}:
        trigger_reasons.append(f"escape_action_requested:{escape_action}")
    if frustration_signals:
        trigger_reasons.append("frustration_detected")
    if stagnation_score >= STAGNATION_THRESHOLD:
        trigger_reasons.append("semantic_stagnation")
    if computed_turn_count > 5:
        trigger_reasons.append("turn_limit")

    trace_log.append(
        {
            "node": "guardrails",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "success": True,
                "guardrail_triggered": guardrail_triggered,
                "tutor_mode": tutor_mode,
                "turn_count": computed_turn_count,
                "stagnation_score": stagnation_score,
                "trigger_reasons": trigger_reasons,
                "frustration_signals": frustration_signals,
                "thresholds": {
                    "turn_count": 5,
                    "stagnation": STAGNATION_THRESHOLD,
                },
            },
        }
    )

    return {
        "turn_count": computed_turn_count,
        "stagnation_score": stagnation_score,
        "frustration_signals": frustration_signals,
        "guardrail_triggered": guardrail_triggered,
        "escape_hatch_visible": guardrail_triggered,
        "tutor_mode": tutor_mode,
        "trace_log": trace_log,
    }
