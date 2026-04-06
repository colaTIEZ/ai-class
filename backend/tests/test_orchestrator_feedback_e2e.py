"""Minimal E2E tests for answer feedback orchestrator flow."""

from __future__ import annotations

import json
import uuid

from app.graph.orchestrator import invoke_answer_feedback
from app.schemas.hint import HintResult
from app.schemas.validation import ValidationResult


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeStructuredInvoker:
    def __init__(self, *, result=None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error

    def invoke(self, _messages):
        if self._error is not None:
            raise self._error
        return self._result


class _FakeLLM:
    def __init__(self, *, structured_result=None, structured_error: Exception | None = None, raw_payload: dict | None = None) -> None:
        self._structured_result = structured_result
        self._structured_error = structured_error
        self._raw_payload = raw_payload or {}

    def with_structured_output(self, _schema):
        return _FakeStructuredInvoker(result=self._structured_result, error=self._structured_error)

    def invoke(self, _messages):
        return _FakeResponse(json.dumps(self._raw_payload))


def test_invoke_answer_feedback_incorrect_routes_to_socratic_hint(monkeypatch):
    fake_validate_llm = _FakeLLM(
        structured_result=ValidationResult(
            is_correct=False,
            error_type="logic_gap",
            severity=1,
            confidence=0.8,
            reasoning="Missing transition from premise to conclusion.",
            key_missing_concepts=["inferential step"],
            positive_aspects=["Premise identified"],
            areas_for_improvement=["Add intermediate step"],
        )
    )
    fake_hint_llm = _FakeLLM(
        structured_result=HintResult(
            hint_text="What step links your premise to your conclusion?",
            hint_type="leading_question",
            difficulty_level="medium",
            next_step_suggestion="Write that missing step explicitly.",
            hint_session_count=1,
        )
    )

    monkeypatch.setattr("app.graph.nodes.validate._build_llm", lambda: fake_validate_llm)
    monkeypatch.setattr("app.graph.nodes.hint._build_llm", lambda: fake_hint_llm)

    result = invoke_answer_feedback(
        thread_id=str(uuid.uuid4()),
        selected_node_ids=["node-1"],
        question_type="short_answer",
        current_answer="A and C are unrelated.",
        current_question={
            "question_text": "If A=B and B=C, what is A?",
            "options": None,
            "correct_answer": "A=C",
            "current_node_id": "node-1",
        },
        escape_action="continue",
        current_node_id="node-1",
    )

    state = result["state"]
    assert state["validation_result"]["is_correct"] is False
    assert state["validation_result"]["error_type"] == "logic_gap"
    assert isinstance(state.get("current_hint"), str)
    assert state["current_hint"]

    node_names = [entry.get("node") for entry in state.get("trace_log", [])]
    validation_trace_nodes = [
        entry.get("node")
        for entry in state.get("validation_result", {}).get("trace_log", [])
        if isinstance(entry, dict)
    ]
    assert "validate" in validation_trace_nodes
    assert "guardrails" in node_names
    assert "socratic_hint" in node_names


def test_invoke_answer_feedback_correct_exits_without_hint(monkeypatch):
    fake_validate_llm = _FakeLLM(
        structured_result=ValidationResult(
            is_correct=True,
            error_type="no_error",
            severity=1,
            confidence=0.95,
            reasoning="Answer matches expected output.",
            key_missing_concepts=[],
            positive_aspects=["Correct final result"],
            areas_for_improvement=[],
        )
    )

    monkeypatch.setattr("app.graph.nodes.validate._build_llm", lambda: fake_validate_llm)

    result = invoke_answer_feedback(
        thread_id=str(uuid.uuid4()),
        selected_node_ids=["node-1"],
        question_type="short_answer",
        current_answer="A=C",
        current_question={
            "question_text": "If A=B and B=C, what is A?",
            "options": None,
            "correct_answer": "A=C",
            "current_node_id": "node-1",
        },
        escape_action="continue",
        current_node_id="node-1",
    )

    state = result["state"]
    assert state["validation_result"]["is_correct"] is True
    assert state["validation_result"]["error_type"] == "no_error"
    assert not state.get("current_hint")

    node_names = [entry.get("node") for entry in state.get("trace_log", [])]
    validation_trace_nodes = [
        entry.get("node")
        for entry in state.get("validation_result", {}).get("trace_log", [])
        if isinstance(entry, dict)
    ]
    assert "validate" in validation_trace_nodes
    assert "guardrails" in node_names
    assert "socratic_hint" not in node_names
