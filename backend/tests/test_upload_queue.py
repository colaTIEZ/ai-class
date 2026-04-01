import pytest
import asyncio
from app.core.config import settings
from app.services.vector_store import get_connection

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


@pytest.mark.asyncio
async def test_upload_magic_byte_validation(async_client):
    file_content = b"NOTP" + b"A" * 512
    files = {"file": ("fake.pdf", file_content, "application/pdf")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 415
    assert response.json()["message"] == "Invalid PDF file: magic bytes mismatch"


@pytest.mark.asyncio
async def test_start_worker_marks_zombie_queued_tasks_as_error(async_client):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO document_tasks (job_id, file_path, status, updated_at) "
            "VALUES (?, ?, 0, '2000-01-01 00:00:00')",
            ("zombie-queued-job", "dummy.pdf"),
        )
        conn.commit()
    finally:
        conn.close()

    old_timeout = settings.zombie_task_timeout_seconds
    settings.zombie_task_timeout_seconds = 1
    try:
        from app.services.processing_queue import processing_queue
        if processing_queue.worker_task and not processing_queue.worker_task.done():
            processing_queue.worker_task.cancel()
            await processing_queue.worker_task
        while not processing_queue.queue.empty():
            processing_queue.queue.get_nowait()
            processing_queue.queue.task_done()
        processing_queue.start_worker()
    finally:
        settings.zombie_task_timeout_seconds = old_timeout

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status, error_message FROM document_tasks WHERE job_id = ?",
            ("zombie-queued-job",),
        ).fetchone()
        assert row is not None
        assert row["status"] == -1
        assert row["error_message"] == "Process terminated unexpectedly"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_upload_returns_503_when_embedding_not_ready(async_client):
    old_key = settings.openai_api_key
    settings.openai_api_key = ""
    try:
        file_content = b"%PDF-1.4\n" + b"A" * 1024
        files = {"file": ("test.pdf", file_content, "application/pdf")}
        response = await async_client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 503
        assert "Embedding service unavailable" in response.json()["message"]
    finally:
        settings.openai_api_key = old_key
