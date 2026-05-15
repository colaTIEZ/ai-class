"""Test embedding service with batch processing and retry logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.embedding_service import EmbeddingProvider, EmbeddingError


@pytest.mark.asyncio
async def test_embedding_provider_embed_batch_single():
    provider = EmbeddingProvider(
        api_key="test-key",
        api_base="https://api.test.com",
        model="test-model",
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"index": 0, "embedding": [0.1] * 1024},
            {"index": 1, "embedding": [0.2] * 1024},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_context.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.embedding_service.httpx.AsyncClient", return_value=mock_context):
        embeddings = await provider.embed_batch(["text1", "text2"])

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1024
        assert embeddings[0][0] == 0.1


@pytest.mark.asyncio
async def test_embedding_provider_embed_batch_empty():
    provider = EmbeddingProvider(api_key="test-key")
    result = await provider.embed_batch([])
    assert result == []


@pytest.mark.asyncio
async def test_embedding_provider_embed_single():
    provider = EmbeddingProvider(api_key="test-key")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"index": 0, "embedding": [0.5] * 1024}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_context.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.embedding_service.httpx.AsyncClient", return_value=mock_context):
        embedding = await provider.embed_single("hello world")
        assert len(embedding) == 1024
        assert embedding[0] == 0.5
