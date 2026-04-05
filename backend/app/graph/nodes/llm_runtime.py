"""LLM runtime helpers for graph nodes."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def strip_markdown_json(text: str) -> str:
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if not lines:
        return cleaned

    body = lines[1:]
    if body and body[-1].strip() == "```":
        body = body[:-1]
    return "\n".join(body).strip()


def parse_json_payload(text: str) -> dict[str, Any]:
    return json.loads(strip_markdown_json(text))


def is_timeout_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "timeout" in message or "timed out" in message


def invoke_with_retry(fn: Callable[[], T], *, max_attempts: int = 3, base_delay_seconds: float = 0.2) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: PERF203
            last_error = exc
            if attempt >= max_attempts or not is_timeout_error(exc):
                raise
            time.sleep(base_delay_seconds * (2 ** (attempt - 1)))

    if last_error is not None:
        raise last_error
    raise RuntimeError("invoke_with_retry reached unreachable state")


def truncate_tokens(text: str, max_tokens: int) -> str:
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError(f"max_tokens must be a positive integer, got {max_tokens}")
    parts = text.split()
    if len(parts) <= max_tokens:
        return text
    return " ".join(parts[:max_tokens])
