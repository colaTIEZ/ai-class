"""Behavior-level tests for LLM-backed validate/hint nodes."""

from __future__ import annotations

import json

from app.graph.nodes.hint import generate_hint_node
from app.graph.nodes.validate import validate_answer_node
from app.graph.state import SocraticState
from app.schemas.hint import HintResult
from app.schemas.validation import ValidationResult


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeStructuredInvoker:
    def __init__(self, *, result=None, error: Exception | None = None, capture: list | None = None) -> None:
        self._result = result
        self._error = error
        self._capture = capture

    def invoke(self, messages):
        if self._capture is not None:
            self._capture.append(messages)
        if self._error is not None:
            raise self._error
        return self._result


class _FakeLLM:
    def __init__(self, *, structured_result=None, structured_error: Exception | None = None, raw_payload: dict | None = None, capture: list | None = None) -> None:
        self._structured_result = structured_result
        self._structured_error = structured_error
        self._raw_payload = raw_payload or {}
        self._capture = capture

    def with_structured_output(self, _schema):
        return _FakeStructuredInvoker(
            result=self._structured_result,
            error=self._structured_error,
            capture=self._capture,
        )

    def invoke(self, messages):
        if self._capture is not None:
            self._capture.append(messages)
        return _FakeResponse(json.dumps(self._raw_payload))


def test_validate_node_prefers_structured_output(monkeypatch) -> None:
    fake_llm = _FakeLLM(
        structured_result=ValidationResult(
            is_correct=False,
            error_type="conceptual",
            severity=2,
            confidence=0.9,
            reasoning="Core concept is misunderstood.",
            key_missing_concepts=["definition"],
            positive_aspects=["Attempted to explain"],
            areas_for_improvement=["Use precise concept terms"],
        )
    )
    monkeypatch.setattr("app.graph.nodes.validate._build_llm", lambda: fake_llm)

    state: SocraticState = {
        "current_question": {
            "question_text": "Explain recursion.",
            "options": None,
            "correct_answer": "A function calling itself with base case.",
        },
        "current_answer": "It repeats without base condition.",
        "trace_log": [],
        "error_message": None,
    }

    result = validate_answer_node(state)
    payload = result["validation_result"]

    assert payload["error_type"] == "conceptual"
    assert payload["is_correct"] is False
    assert "reasoning" in payload and payload["reasoning"]


def test_validate_node_falls_back_to_raw_json_when_structured_fails(monkeypatch) -> None:
    fake_llm = _FakeLLM(
        structured_error=RuntimeError("structured failed"),
        raw_payload={
            "is_correct": False,
            "error_type": "logic_gap",
            "severity": 1,
            "confidence": 0.75,
            "reasoning": "Inference step missing.",
            "key_missing_concepts": ["transitive step"],
            "positive_aspects": ["Identified related concept"],
            "areas_for_improvement": ["Explain transition from premise to conclusion"],
        },
    )
    monkeypatch.setattr("app.graph.nodes.validate._build_llm", lambda: fake_llm)

    state: SocraticState = {
        "current_question": {
            "question_text": "If A=B and B=C, what is A?",
            "options": None,
            "correct_answer": "A=C",
        },
        "current_answer": "A and C are unrelated.",
        "trace_log": [],
        "error_message": None,
    }

    result = validate_answer_node(state)
    payload = result["validation_result"]

    assert payload["error_type"] == "logic_gap"
    assert payload["confidence"] == 0.75


def test_hint_node_semi_transparent_prefixes_direct_guidance(monkeypatch) -> None:
    capture = []
    fake_llm = _FakeLLM(
        structured_result=HintResult(
            hint_text="Check the missing intermediate step before the conclusion.",
            hint_type="scaffold",
            difficulty_level="medium",
            next_step_suggestion="Rewrite your reasoning with one extra step.",
            hint_session_count=2,
        ),
        capture=capture,
    )
    monkeypatch.setattr("app.graph.nodes.hint._build_llm", lambda: fake_llm)

    state: SocraticState = {
        "validation_result": {
            "error_type": "logic_gap",
            "is_correct": False,
            "reasoning": "You skipped a key inference.",
            "key_missing_concepts": ["inference chain"],
        },
        "current_question": {
            "question_text": "Prove transitivity.",
            "options": None,
            "correct_answer": "A=C",
        },
        "current_answer": "A and C do not relate.",
        "trace_log": [],
        "error_message": None,
        "tutor_mode": "semi_transparent",
    }

    result = generate_hint_node(state)

    assert result["current_hint"].startswith("Direct guidance:")
    assert capture, "Expected captured LLM messages"
    user_message = capture[0][1]["content"]
    assert "error_type: logic_gap" in user_message
    assert "tutor_mode: semi_transparent" in user_message


def test_hint_node_falls_back_to_raw_json_when_structured_fails(monkeypatch) -> None:
    fake_llm = _FakeLLM(
        structured_error=RuntimeError("structured failed"),
        raw_payload={
            "hint_text": "Which term in the question defines the core concept?",
            "hint_type": "leading_question",
            "difficulty_level": "medium",
            "next_step_suggestion": "Define that term in your own words first.",
            "hint_session_count": 1,
        },
    )
    monkeypatch.setattr("app.graph.nodes.hint._build_llm", lambda: fake_llm)

    state: SocraticState = {
        "validation_result": {
            "error_type": "conceptual",
            "is_correct": False,
            "reasoning": "Concept definition is vague.",
            "key_missing_concepts": ["formal definition"],
        },
        "current_question": {
            "question_text": "Define overfitting.",
            "options": None,
            "correct_answer": "Model memorizes training data and generalizes poorly.",
        },
        "current_answer": "It means training a lot.",
        "trace_log": [],
        "error_message": None,
        "tutor_mode": "socratic",
    }

    result = generate_hint_node(state)

    assert isinstance(result["current_hint"], str)
    assert "core concept" in result["current_hint"]
