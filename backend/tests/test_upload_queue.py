import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

import pytest_asyncio

@pytest_asyncio.fixture
async def async_client():
    async with ASGITransport(app=app) as transport:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # the easiest way to trigger lifespan without extra deps in old httpx is calling init_db manually, actually or using httpx.ASGITransport's own lifespan mechanics?
            # Wait, httpx AsyncClient handles lifespan. But just to be sure
            from app.services.vector_store import init_db
            init_db()
            from app.services.processing_queue import processing_queue
            processing_queue.start_worker()
            yield client
            await processing_queue.stop_worker()

@pytest.mark.asyncio
async def test_single_upload_returns_202_and_format(async_client):
    file_content = b"%PDF-1.4\n" + b"A" * 1024
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "success"
    assert "job_id" in data["data"]
    assert data["data"]["status"] == "queued"
    assert data["data"]["position"] >= 1
    assert "trace_id" in data

@pytest.mark.asyncio
async def test_upload_format_validation(async_client):
    file_content = b"Not a PDF file"
    files = {"file": ("test.txt", file_content, "text/plain")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code in [400, 415, 422]  
    
@pytest.mark.asyncio
async def test_upload_size_validation(async_client):
    # File larger than 10MB (just above 10MB)
    file_content = b"%PDF-1.4\n" + b"0" * (11 * 1024 * 1024)
    files = {"file": ("large.pdf", file_content, "application/pdf")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code in [413, 400]

@pytest.mark.asyncio
async def test_concurrency_queue(async_client):
    file_content = b"%PDF-1.4\n" + b"A" * 1024
    
    async def upload():
        files = {"file": ("test.pdf", file_content, "application/pdf")}
        return await async_client.post("/api/v1/documents/upload", files=files)
    
    # Fire 5 requests concurrently
    responses = await asyncio.gather(*[upload() for _ in range(5)])
    
    for r in responses:
        assert r.status_code == 202
    
    positions = [r.json()["data"]["position"] for r in responses]
    assert len(positions) == 5
    assert max(positions) >= 4

@pytest.mark.asyncio
async def test_get_upload_status(async_client):
    file_content = b"%PDF-1.4\n" + b"A" * 1024
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 202
    job_id = response.json()["data"]["job_id"]
    
    # query status
    status_response = await async_client.get(f"/api/v1/documents/upload/{job_id}")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["data"]["job_id"] == job_id
    assert data["data"]["status"] in ["queued", "processing", "done"]
    assert data["data"]["position"] >= 0
