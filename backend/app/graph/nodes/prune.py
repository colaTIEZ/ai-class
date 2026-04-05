"""Context pruning node for guardrail-triggered flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.graph.nodes.llm_runtime import truncate_tokens
from app.graph.state import SocraticState

MAX_SUMMARY_TOKENS = 120
KEEP_RECENT_MESSAGES = 4


def _to_message_line(item: dict[str, Any]) -> str:
    role = item.get("role", "unknown")
    content = item.get("content", "")
    if not isinstance(content, str):
        content = ""
    return f"{role}: {content.strip()}".strip()


def prune_context_node(state: SocraticState) -> dict[str, Any]:
    trace_log = list(state.get("trace_log", []))
    history = state.get("conversation_history", [])
    guardrail_triggered = state.get("guardrail_triggered") is True

    if not isinstance(history, list):
        history = []

    if not guardrail_triggered or len(history) <= KEEP_RECENT_MESSAGES:
        trace_log.append(
            {
                "node": "prune",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "success": True,
                    "skipped": True,
                    "reason": "guardrail_not_triggered_or_small_history",
                    "history_size": len(history),
                },
            }
        )
        return {
            "context_summary": state.get("context_summary"),
            "pruned_message_count": 0,
            "trace_log": trace_log,
        }

    old_messages = history[:-KEEP_RECENT_MESSAGES]
    retained_messages = history[-KEEP_RECENT_MESSAGES:]

    summary_lines: list[str] = []
    for entry in old_messages:
        if isinstance(entry, dict):
            line = _to_message_line(entry)
            if line:
                summary_lines.append(line)

    raw_summary = " | ".join(summary_lines)
    summary = truncate_tokens(raw_summary, MAX_SUMMARY_TOKENS).strip()
    summary_token_count = len(summary.split()) if summary else 0

    trace_log.append(
        {
            "node": "prune",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "success": True,
                "history_before": len(history),
                "history_after": len(retained_messages),
                "pruned_message_count": len(old_messages),
                "summary_token_count": summary_token_count,
            },
        }
    )

    return {
        "conversation_history": retained_messages,
        "context_summary": summary or None,
        "pruned_message_count": len(old_messages),
        "trace_log": trace_log,
    }
