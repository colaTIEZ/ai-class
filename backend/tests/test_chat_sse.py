"""SSE 聊天接口测试。"""

import json
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.vector_store import get_connection


def _payload(answer: str) -> dict:
    return {
        "selected_node_ids": ["n1"],
        "question_type": "short_answer",
        "current_question": {
            "question_text": "2+2?",
            "options": None,
            "correct_answer": "4",
            "current_node_id": "node-1",
        },
        "current_answer": answer,
        "action": "continue",
    }


def _extract_events(body: str) -> list[dict]:
    events: list[dict] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        for line in block.splitlines():
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            events.append(json.loads(raw))
    return events


def test_submit_answer_sse_stream(force_no_openai_key):
    client = TestClient(app)
    response = client.post("/api/v1/chat/message", json=_payload("5"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _extract_events(response.text)
    assert events
    types = {event["type"] for event in events}
    assert "trace" in types
    assert "content" in types
    assert all(event.get("trace_id") for event in events)


def test_submit_answer_sse_first_byte_latency_trace_present(force_no_openai_key):
    client = TestClient(app)
    response = client.post("/api/v1/chat/message", json=_payload("5"))
    events = _extract_events(response.text)
    sse_traces = [e for e in events if e.get("type") == "trace" and e.get("data", {}).get("node_name") == "sse"]
    assert sse_traces
    latency_traces = [e for e in sse_traces if "first_byte_latency_ms" in e.get("data", {}).get("metadata", {})]
    assert latency_traces
    latency = latency_traces[-1]["data"]["metadata"]["first_byte_latency_ms"]
    assert isinstance(latency, int)
    assert latency < 3000


def test_submit_answer_sse_trace_payload_is_lightweight(force_no_openai_key):
    client = TestClient(app)
    response = client.post("/api/v1/chat/message", json=_payload("5"))
    events = _extract_events(response.text)
    trace_events = [event for event in events if event.get("type") == "trace"]

    assert trace_events
    assert trace_events[0]["data"]["node_name"] == "init_answer_feedback"
    assert any(event["data"]["node_name"] == "validate" for event in trace_events)
    assert any(event["data"]["node_name"] == "guardrails" for event in trace_events)
    assert any(event["data"]["node_name"] == "socratic_hint" for event in trace_events)
    for event in trace_events:
        data = event.get("data", {})
        assert set(data.keys()).issubset({"node_name", "metadata"})
        assert isinstance(data.get("node_name"), str)
        assert isinstance(data.get("metadata"), dict)
        assert "validation_result" not in data
        assert "current_hint" not in data


def test_submit_answer_sse_concurrent_requests_have_distinct_trace_id(force_no_openai_key):
    def _send(answer: str) -> str:
        client = TestClient(app)
        response = client.post("/api/v1/chat/message", json=_payload(answer))
        assert response.status_code == 200
        events = _extract_events(response.text)
        assert events
        return str(events[0]["trace_id"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_send, answer) for answer in ["5", "6"]]
        trace_ids: list[str] = []
        for future in futures:
            try:
                trace_ids.append(future.result(timeout=10))
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"Concurrent SSE request failed: {exc!r}")

    assert len(trace_ids) == 2
    assert trace_ids[0] != trace_ids[1]


def test_submit_answer_sse_peak_memory_under_budget(force_no_openai_key):
    client = TestClient(app)
    try:
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        _ = client.post("/api/v1/chat/message", json=_payload("5"))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
    assert peak < 1_800_000  # 1.8MB budget


def test_submit_answer_sse_show_answer_action(force_no_openai_key):
    client = TestClient(app)
    payload = _payload("too hard")
    payload["action"] = "show_answer"
    response = client.post("/api/v1/chat/message", json=payload)
    events = _extract_events(response.text)
    content_events = [e for e in events if e.get("type") == "content"]
    assert content_events
    text = str(content_events[0].get("data", {}).get("text", ""))
    assert "Direct answer:" in text


def test_submit_answer_sse_skip_action_marks_review(force_no_openai_key):
    client = TestClient(app)
    payload = _payload("too hard")
    payload["action"] = "skip"
    payload.pop("current_node_id", None)
    response = client.post("/api/v1/chat/message", json=payload)
    events = _extract_events(response.text)
    content_events = [e for e in events if e.get("type") == "content"]
    assert content_events
    needs_review = content_events[0].get("data", {}).get("needs_review_queued")
    assert bool(needs_review) is True

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT node_id, needs_review FROM question_review_flags WHERE node_id = ? ORDER BY id DESC LIMIT 1",
            ("node-1",),
        ).fetchone()
        assert row is not None
        assert row["node_id"] == "node-1"
        assert int(row["needs_review"]) == 1
    finally:
        conn.close()


def test_submit_answer_sse_skip_action_uses_question_node_id(force_no_openai_key):
    client = TestClient(app)
    payload = _payload("too hard")
    payload["action"] = "skip"
    payload.pop("current_node_id", None)
    response = client.post("/api/v1/chat/message", json=payload)
    events = _extract_events(response.text)
    content_events = [e for e in events if e.get("type") == "content"]
    assert content_events
    needs_review = content_events[0].get("data", {}).get("needs_review_queued")
    assert bool(needs_review) is True


def test_submit_answer_sse_wrong_answer_persists_with_question_node_id(force_no_openai_key):
    client = TestClient(app)
    payload = _payload("5")
    payload.pop("current_node_id", None)

    response = client.post("/api/v1/chat/message", json=payload)
    assert response.status_code == 200

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT node_id, is_correct
            FROM question_history
            WHERE question_text = ?
              AND user_answer = ?
            ORDER BY attempted_at DESC, question_record_id DESC
            LIMIT 1
            """,
            ("2+2?", "5"),
        ).fetchone()
        assert row is not None
        assert row["node_id"] == "node-1"
        assert int(row["is_correct"]) == 0
    finally:
        conn.close()


def test_submit_answer_sse_escape_action_rejected_without_guardrail(force_no_openai_key):
    client = TestClient(app)
    payload = _payload("5")
    payload["action"] = "show_answer"
    response = client.post("/api/v1/chat/message", json=payload)
    events = _extract_events(response.text)
    error_events = [e for e in events if e.get("type") == "error"]
    assert error_events
    message = str(error_events[0].get("data", {}).get("message", ""))
    assert "Escape hatch is only available after guardrail is triggered." in message


def test_submit_answer_sse_persistence_failure_emits_trace(force_no_openai_key):
    client = TestClient(app)
    with patch("app.api.v1.chat.record_answer", side_effect=RuntimeError("db down")):
        response = client.post("/api/v1/chat/message", json=_payload("5"))

    assert response.status_code == 200
    events = _extract_events(response.text)
    trace_events = [
        e
        for e in events
        if e.get("type") == "trace" and e.get("data", {}).get("node_name") == "review_persistence"
    ]
    assert trace_events
    metadata = trace_events[0].get("data", {}).get("metadata", {})
    assert metadata.get("persisted") is False
    assert metadata.get("reason") == "record_answer_failed"
