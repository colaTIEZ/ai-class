"""Prune node tests."""

from app.graph.nodes.prune import prune_context_node
from app.graph.state import SocraticState


def test_prune_skips_when_guardrail_not_triggered():
    state: SocraticState = {
        "guardrail_triggered": False,
        "conversation_history": [{"role": "student", "content": "a"}],
        "trace_log": [],
    }
    result = prune_context_node(state)
    assert result["pruned_message_count"] == 0


def test_prune_reduces_history_and_creates_summary():
    history = [
        {"role": "student", "content": f"answer {i}"} for i in range(8)
    ]
    state: SocraticState = {
        "guardrail_triggered": True,
        "conversation_history": history,
        "trace_log": [],
    }
    result = prune_context_node(state)
    assert result["pruned_message_count"] == 4
    assert len(result["conversation_history"]) == 4
    assert isinstance(result["context_summary"], str)
    assert result["context_summary"]
