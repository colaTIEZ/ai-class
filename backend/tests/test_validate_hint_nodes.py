"""Validator / Hint 节点测试。"""

from app.core.config import settings
from app.graph.nodes.hint import generate_hint_node
from app.graph.nodes.validate import validate_answer_node
from app.graph.state import SocraticState


def test_validate_node_correct_answer():
    old_key = settings.openai_api_key
    settings.openai_api_key = ""
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
    settings.openai_api_key = old_key


def test_validate_node_incorrect_answer():
    old_key = settings.openai_api_key
    settings.openai_api_key = ""
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
    assert result["validation_result"]["error_type"] in {"conceptual", "logic_gap", "incomplete"}
    settings.openai_api_key = old_key


def test_hint_node_generates_content():
    old_key = settings.openai_api_key
    settings.openai_api_key = ""
    state: SocraticState = {
        "validation_result": {"error_type": "logic_gap", "is_correct": False},
        "current_question": {"question_text": "Explain recursion", "options": None, "correct_answer": "x"},
        "trace_log": [],
        "error_message": None,
    }
    result = generate_hint_node(state)
    assert isinstance(result["current_hint"], str)
    assert result["current_hint"]
    settings.openai_api_key = old_key


def test_validate_node_truncates_long_answer():
    old_key = settings.openai_api_key
    settings.openai_api_key = ""
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
    settings.openai_api_key = old_key
