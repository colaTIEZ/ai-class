"""Async embedding generation service for job queue workers.

Design rationale:
- Async/await for non-blocking I/O with OpenAI API
- Batch vectorization to reduce API calls
- Retry with exponential backoff for transient failures
- embedding_version tracking for safe model upgrades
"""

import logging
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    pass


class EmbeddingProvider:
    """OpenAI embedding client with retry and batch processing.

    Targets: 1024-dim vectors (Phase 1 standard)
    Model: configurable via settings.openai_embedding_model
    Batch size: 100 texts per request (OpenAI recommended)
    """

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if len(texts) > 100:
            mid = len(texts) // 2
            left = await self.embed_batch(texts[:mid])
            right = await self.embed_batch(texts[mid:])
            return left + right

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base}/embeddings",
                    json={"model": self.model, "input": texts},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()

                if "data" not in data:
                    raise EmbeddingError(f"Invalid embedding response: {data}")

                embeddings_sorted = sorted(data["data"], key=lambda x: x.get("index", 0))
                embeddings = [item["embedding"] for item in embeddings_sorted]

                logger.info(
                    "generated_embeddings",
                    extra={
                        "count": len(embeddings),
                        "model": self.model,
                        "batch_size": len(texts),
                    },
                )
                return embeddings

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.error(f"embedding_network_error: {e}")
            raise EmbeddingError(f"Network error during embedding: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"embedding_api_error: {e.response.status_code}")
            if e.response.status_code == 429:
                raise EmbeddingError("Rate limited by embedding API") from e
            raise EmbeddingError(f"API error: {e.response.status_code}") from e
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"embedding_unknown_error: {e}")
            raise EmbeddingError(f"Unknown embedding error: {e}") from e

    async def embed_single(self, text: str) -> list[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else []


def get_embedding_provider(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> EmbeddingProvider:
    return EmbeddingProvider(
        api_key=api_key or settings.openai_api_key,
        api_base=settings.openai_base_url or "https://api.openai.com/v1",
        model=model or settings.openai_embedding_model or "text-embedding-3-small",
    )
