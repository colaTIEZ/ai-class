"""Guardrails node tests."""

from app.graph.nodes.guardrails import evaluate_guardrails_node
from app.graph.state import SocraticState


def _base_state(answer: str) -> SocraticState:
    return {
        "current_answer": answer,
        "conversation_history": [],
        "turn_count": 0,
        "trace_log": [],
    }


def test_guardrails_triggers_on_frustration_keyword():
    result = evaluate_guardrails_node(_base_state("I don't know this one"))
    assert result["guardrail_triggered"] is True
    assert result["escape_hatch_visible"] is True
    assert result["tutor_mode"] == "semi_transparent"
    assert "i don't know" in result["frustration_signals"]


def test_guardrails_triggers_on_turn_count_limit():
    state = _base_state("maybe")
    state["turn_count"] = 6
    result = evaluate_guardrails_node(state)
    assert result["guardrail_triggered"] is True
    assert result["tutor_mode"] == "semi_transparent"


def test_guardrails_triggers_on_stagnation_similarity():
    state: SocraticState = {
        "current_answer": "the answer is x",
        "conversation_history": [
            {"role": "student", "content": "the answer is x"},
            {"role": "student", "content": "the answer is x"},
        ],
        "trace_log": [],
    }
    result = evaluate_guardrails_node(state)
    assert result["stagnation_score"] >= 0.92
    assert result["guardrail_triggered"] is True


def test_guardrails_not_triggered_for_normal_progress():
    state: SocraticState = {
        "current_answer": "use derivative chain rule with inner function",
        "conversation_history": [
            {"role": "student", "content": "try derivative"},
            {"role": "student", "content": "differentiate inner term first"},
        ],
        "turn_count": 2,
        "trace_log": [],
    }
    result = evaluate_guardrails_node(state)
    assert result["guardrail_triggered"] is False
    assert result["tutor_mode"] == "socratic"
