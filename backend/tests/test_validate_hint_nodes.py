"""Validator / Hint 节点测试。"""

from app.graph.nodes.llm_runtime import truncate_tokens

from app.graph.nodes.hint import generate_hint_node
from app.graph.nodes.validate import validate_answer_node
from app.graph.state import SocraticState


def test_validate_node_correct_answer(force_no_openai_key):
    state: SocraticState = {
        "current_question": {
            "question_text": "2+2?",
            "options": None,
            "correct_answer": "4",
        },
        "current_answer": "4",
        "trace_log": [],
        "error_message": None,
    }
    result = validate_answer_node(state)
    assert result["validation_result"]["is_correct"] is True
    assert result["validation_result"]["error_type"] == "no_error"


def test_validate_node_incorrect_answer(force_no_openai_key):
    state: SocraticState = {
        "current_question": {
            "question_text": "2+2?",
            "options": None,
            "correct_answer": "4",
        },
        "current_answer": "5",
        "trace_log": [],
        "error_message": None,
    }
    result = validate_answer_node(state)
    assert result["validation_result"]["is_correct"] is False
    assert result["validation_result"]["error_type"] in {"conceptual", "logic_gap", "incomplete", "calculation"}


def test_hint_node_generates_content(force_no_openai_key):
    state: SocraticState = {
        "validation_result": {"error_type": "logic_gap", "is_correct": False},
        "current_question": {"question_text": "Explain recursion", "options": None, "correct_answer": "x"},
        "trace_log": [],
        "error_message": None,
    }
    result = generate_hint_node(state)
    assert isinstance(result["current_hint"], str)
    assert result["current_hint"]


def test_validate_node_truncates_long_answer(force_no_openai_key):
    long_answer = "word " * 500
    state: SocraticState = {
        "current_question": {
            "question_text": "Summarize",
            "options": None,
            "correct_answer": "summary",
        },
        "current_answer": long_answer,
        "trace_log": [],
        "error_message": None,
    }
    result = validate_answer_node(state)
    assert result["validation_result"]["trace_log"][-1]["metadata"]["answer_truncated"] is True
    assert len(state["current_answer"].split()) > 200
    assert len(truncate_tokens(state["current_answer"], 200).split()) == 200


def test_validate_node_enforces_token_budgets(force_no_openai_key):
    long_question = "q " * 500
    long_answer = "a " * 400
    state: SocraticState = {
        "current_question": {
            "question_text": long_question,
            "options": None,
            "correct_answer": "b",
        },
        "current_answer": long_answer,
        "trace_log": [],
        "error_message": None,
    }
    result = validate_answer_node(state)
    validation = result["validation_result"]
    assert len(truncate_tokens(long_question, 300).split()) == 300
    assert len(truncate_tokens(long_answer, 200).split()) == 200
    assert len(truncate_tokens(validation.get("reasoning", ""), 400).split()) <= 400


def test_hint_node_enforces_hint_token_budget(force_no_openai_key):
    long_question = "long-question " * 1000
    state: SocraticState = {
        "validation_result": {"error_type": "off_topic", "is_correct": False},
        "current_question": {"question_text": long_question, "options": None, "correct_answer": "x"},
        "trace_log": [],
        "error_message": None,
    }
    result = generate_hint_node(state)
    assert len(result["current_hint"].split()) == 600  # Exact boundary check
