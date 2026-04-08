"""LLM runtime and token budget configuration.

Centralizes model parameters and token budgets used across graph nodes and services.
"""

from __future__ import annotations


class LLMConfig:
    """Global LLM parameters and budget limits."""

    # Runtime defaults
    TEMPERATURE = 0.3
    TIMEOUT_SECONDS = 30.0
    MAX_RETRIES = 3
    RETRY_BASE_WAIT_SECONDS = 0.2

    # Token budgets by stage
    QUESTION_CONTEXT_TOKENS = 300
    STUDENT_ANSWER_TOKENS = 200
    VALIDATION_REASONING_TOKENS = 400
    HINT_GENERATION_TOKENS = 600

    # Soft aggregate budget for one request chain
    TOTAL_TOKENS_PER_REQUEST = (
        QUESTION_CONTEXT_TOKENS
        + STUDENT_ANSWER_TOKENS
        + VALIDATION_REASONING_TOKENS
        + HINT_GENERATION_TOKENS
    )

    # Keep under practical small-context targets for reliability
    MAX_TOTAL_TOKENS = 2000

    @classmethod
    def validate(cls) -> None:
        """Validate LLM configuration at import/startup time."""
        numeric_fields = [
            "TEMPERATURE",
            "TIMEOUT_SECONDS",
            "MAX_RETRIES",
            "RETRY_BASE_WAIT_SECONDS",
            "QUESTION_CONTEXT_TOKENS",
            "STUDENT_ANSWER_TOKENS",
            "VALIDATION_REASONING_TOKENS",
            "HINT_GENERATION_TOKENS",
            "TOTAL_TOKENS_PER_REQUEST",
            "MAX_TOTAL_TOKENS",
        ]

        for field in numeric_fields:
            value = getattr(cls, field)
            if not isinstance(value, (int, float)):
                raise ValueError(f"LLMConfig.{field} must be numeric, got {type(value).__name__}")
            if field not in {"TEMPERATURE", "RETRY_BASE_WAIT_SECONDS"} and value <= 0:
                raise ValueError(f"LLMConfig.{field} must be positive, got {value}")

        if not (0.0 <= cls.TEMPERATURE <= 1.0):
            raise ValueError(f"LLMConfig.TEMPERATURE must be in [0, 1], got {cls.TEMPERATURE}")

        if cls.TOTAL_TOKENS_PER_REQUEST >= cls.MAX_TOTAL_TOKENS:
            raise ValueError(
                "LLMConfig TOTAL_TOKENS_PER_REQUEST exceeds allowed limit: "
                f"{cls.TOTAL_TOKENS_PER_REQUEST} >= {cls.MAX_TOTAL_TOKENS}"
            )


LLMConfig.validate()
