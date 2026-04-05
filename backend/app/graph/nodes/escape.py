"""Escape hatch action node."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.graph.state import SocraticState


def apply_escape_hatch_node(state: SocraticState) -> dict[str, Any]:
    trace_log = list(state.get("trace_log", []))
    action = state.get("escape_action", "continue")
    guardrail_triggered = state.get("guardrail_triggered") is True

    if action not in {"show_answer", "skip"}:
        trace_log.append(
            {
                "node": "escape_action",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {"success": True, "skipped": True, "action": action},
            }
        )
        return {"trace_log": trace_log}

    if not guardrail_triggered:
        trace_log.append(
            {
                "node": "escape_action",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "success": False,
                    "action": action,
                    "reason": "guardrail_not_triggered",
                },
            }
        )
        return {
            "error_message": "Escape hatch is only available after guardrail is triggered.",
            "trace_log": trace_log,
        }

    current_question = state.get("current_question") or {}
    correct_answer = current_question.get("correct_answer", "")
    if not isinstance(correct_answer, str):
        correct_answer = ""

    needs_review_node_ids = list(state.get("needs_review_node_ids", []))
    current_node_id = state.get("current_node_id")

    review_reason = None
    current_hint = ""
    if action == "show_answer":
        current_hint = (
            f"Direct answer: {correct_answer.strip() or 'Unavailable'}. "
            "Review the key concept and re-attempt a similar question."
        )
    else:
        review_reason = "user_skipped_after_guardrail"
        if isinstance(current_node_id, str) and current_node_id and current_node_id not in needs_review_node_ids:
            needs_review_node_ids.append(current_node_id)
        current_hint = "Question skipped. This node has been marked as Needs Review for follow-up."

    trace_log.append(
        {
            "node": "escape_action",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "success": True,
                "action": action,
                "review_reason": review_reason,
                "needs_review_count": len(needs_review_node_ids),
            },
        }
    )

    return {
        "current_hint": current_hint,
        "review_reason": review_reason,
        "needs_review_node_ids": needs_review_node_ids,
        "trace_log": trace_log,
    }
