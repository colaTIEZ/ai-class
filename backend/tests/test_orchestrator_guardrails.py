"""Orchestrator guardrail routing tests."""

from app.graph.orchestrator import build_answer_feedback_graph
from app.graph.state import SocraticState


def _state(**overrides) -> SocraticState:
    base: SocraticState = {
        "current_question": {
            "question_text": "2+2?",
            "options": None,
            "correct_answer": "4",
        },
        "current_answer": "5",
        "question_type": "short_answer",
        "selected_node_ids": ["n1"],
        "trace_log": [],
        "validation_result": {"is_correct": False, "error_type": "conceptual"},
        "escape_action": "continue",
        "guardrail_triggered": False,
        "conversation_history": [],
    }
    base.update(overrides)
    return base


def test_build_answer_feedback_graph_compiles():
    workflow = build_answer_feedback_graph()
    graph = workflow.compile()
    assert graph is not None


def test_escape_action_route_to_end_after_node(force_no_openai_key):
    workflow = build_answer_feedback_graph()
    graph = workflow.compile()
    state = _state(escape_action="show_answer", current_answer="too hard")
    result = graph.invoke(state)
    assert isinstance(result.get("current_hint"), str)
    assert "Direct answer:" in result.get("current_hint", "")


def test_escape_action_rejected_without_guardrail(force_no_openai_key):
    workflow = build_answer_feedback_graph()
    graph = workflow.compile()
    state = _state(escape_action="show_answer", current_answer="5")
    result = graph.invoke(state)
    assert result.get("error_message") == "Escape hatch is only available after guardrail is triggered."
