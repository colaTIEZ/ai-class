"""SSE 聊天接口测试。"""

import json
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app


def _payload(answer: str) -> dict:
    return {
        "selected_node_ids": ["n1"],
        "question_type": "short_answer",
        "current_question": {
            "question_text": "2+2?",
            "options": None,
            "correct_answer": "4",
        },
        "current_answer": answer,
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


def test_submit_answer_sse_stream():
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


def test_submit_answer_sse_first_byte_latency_trace_present():
    client = TestClient(app)
    response = client.post("/api/v1/chat/message", json=_payload("5"))
    events = _extract_events(response.text)
    sse_traces = [e for e in events if e.get("type") == "trace" and e.get("data", {}).get("node_name") == "sse"]
    assert sse_traces
    latency = sse_traces[-1]["data"]["metadata"]["first_byte_latency_ms"]
    assert isinstance(latency, int)
    assert latency < 3000


def test_submit_answer_sse_concurrent_requests_have_distinct_trace_id():
    def _send(answer: str) -> str:
        client = TestClient(app)
        response = client.post("/api/v1/chat/message", json=_payload(answer))
        events = _extract_events(response.text)
        assert events
        return str(events[0]["trace_id"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        t1, t2 = executor.map(_send, ["5", "6"])
    assert t1 != t2
