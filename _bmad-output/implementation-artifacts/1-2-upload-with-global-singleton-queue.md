# Story 1.2: Upload with Global Singleton Queue

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want to upload my PDF study materials and receive an instant queue position if the server is busy processing someone else's file,
so that my experience is smooth ("graceful degradation") and the 2C2G server never crashes under concurrent load.

## Acceptance Criteria

1. **Given** the backend is running on a 2C2G environment
2. **When** a user uploads a PDF file
3. **Then** the system validates the file size (max 10MB) and format (application/pdf)
4. **And** the backend routes the file to a **Global Singleton asyncio.Queue** (max 1 active worker)
5. **And** if the worker is occupied, the API immediately returns a 202 Accepted status with a payload representing the queue position (e.g., `{"status": "queued", "position": N}`) wrapped in the standard API envelope.
6. **And** the background worker processes only one file at a time, ensuring memory consumption stays below the 1.5GB cap for the backend process.

## Tasks / Subtasks

- [x] Task 1: Implement Global Singleton Processing Queue (AC: 4, 6)
  - [x] Create `backend/app/services/processing_queue.py` to manage a global `asyncio.Queue`.
  - [x] Implement a background worker thread/task that consumes from the queue one at a time.
  - [x] Use FastAPI `lifespan` in `backend/app/main.py` to initialize and gracefully shutdown the queue worker.
- [x] Task 2: Implement PDF Upload Endpoint with Queue Guard (AC: 2, 3, 5)
  - [x] Update `backend/app/api/v1/documents.py` to handle `POST /upload`.
  - [x] Implement file validation using `FastAPI.UploadFile` (Check MIME type and `file.seek(0, 2)` for size validation).
  - [x] Integrate with the `ProcessingQueue` to push the job and get the current position.
- [x] Task 3: Standardize Queue Response Format (AC: 5)
  - [x] Ensure the response uses the `202 Accepted` HTTP status code.
  - [x] Define a Pydantic schema in `backend/app/schemas/queue.py` that conforms to the standard envelope:
    ```json
    {
      "status": "success",
      "data": {
        "job_id": "uuid-string",
        "status": "queued",
        "position": 1
      },
      "message": "File accepted and queued for processing",
      "trace_id": ""
    }
    ```
- [x] Task 4: Concurrency Safety Testing (AC: 1, 6)
  - [x] Create `backend/tests/test_upload_queue.py` using `httpx.AsyncClient`.
  - [x] Simulate 5 concurrent uploads and verify that 1 starts processing while 4 are queued with positions 1, 2, 3, 4.

### Review Findings

- [x] [Review][Patch] 无限制的 jobs_status 内存增长 (使用 SQLite 方案) — `ProcessingQueue.jobs_status` 会把任务状态永远保存在内存中。将根据指示改为使用 SQLite 作为单一事实来源，完全依赖 DB 存状态和算排队次序。
- [x] [Review][Patch] 阻塞的同步文件 IO — `documents.py:79` 存在同步的 `f.write(content)`，阻塞了 FastAPI 异步事件循环。
- [x] [Review][Patch] 缺少任务状态查询 API — 未提供 `GET /upload/{job_id}` 来轮询任务状态，违背了 AC 5 要求的进度反馈机制。
- [x] [Review][Patch] 硬编码路径与内联强依赖导入 — `documents.py` 中硬编码了 `data/uploads/` 并在函数体内 `import os`。
- [x] [Review][Patch] 客户端中断导致临时文件未清理 — `documents.py:65` 处发生 `ClientDisconnect` 异常可能导致垃圾文件残留。
- [x] [Review][Patch] 磁盘满或写入异常未捕获 — `documents.py:79` 未处理 OSError 将导致服务端直接报出 500 而不是优雅的业务错误。
- [x] [Review][Patch] Worker 捕获异常不够彻底 — 可能错过被 KeyboardInterrupt 等 BaseException 使得任务永久卡住。
- [x] [Review][Defer] 缺少 Magic Byte 真实校验 — deferred, pre-existing
- [x] [Review][Defer] 服务重启后队列数据丢失 (无持久化机制) — deferred, pre-existing

## Dev Notes

- **Relevant architecture patterns and constraints**: 
  - **Memory Guarding**: 2C2G limit (2GB RAM). Total backend process must stay < 1.5GB. Global singleton queue is the primary defense against OOM during heavy RAG indexing. 
  - **AsyncIO Queue**: Use `asyncio.Queue` for the singleton. The worker should be a long-running task created during `lifespan` startup.
  - **File Stream Handling**: Use `await file.read()` in chunks or handle the SpooledTemporaryFile carefully to avoid loading the entire 10MB into RAM at once if possible (though 10MB is safe for 2GB, it's good practice).
- **Source tree components to touch**:
  - `backend/app/main.py` (lifespan registration)
  - `backend/app/api/v1/documents.py` (upload endpoint)
  - `backend/app/services/processing_queue.py` (New component)
  - `backend/app/schemas/queue.py` (New schema)
  - `backend/app/core/config.py` (Add `MAX_UPLOAD_SIZE=10485760` (10MB))
- **Testing standards summary**:
  - Use `pytest-asyncio` for testing the async queue logic.
  - Simulate heavy load to verify "Database is locked" issues (WAL mode should be active as per Story 1.1).

### Project Structure Notes

- **Alignment with unified project structure**:
  - Keep logic in `services/` and routes in `api/v1/`.
  - Background worker should be isolated to prevent blocking the main event loop.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Additional Requirements]
- [Source: _bmad-output/planning-artifacts/architecture.md#Memory Guarding]

## Dev Agent Record

### Agent Model Used

Gemini 3 Flash (Antigravity)

### Debug Log References
- Addressed `UploadFile.seek()` receiving 3 arguments due to starlette's async wrapper structure by bypassing to `file.file.seek(0, 2)` underlying standard library file objects for accurate size calculations directly.
- Overwrote older `HTTP_413_REQUEST_ENTITY_TOO_LARGE` FastAPI deprecation correctly to `HTTP_413_CONTENT_TOO_LARGE`.
- Ensured tests use asyncio `gather` with `httpx.AsyncClient` correctly to emulate real HTTP concurrent processing blocking conditions efficiently under ASGITransport.

### Completion Notes List
- ✅ Created queue service with async `asyncio.Queue` worker restricted to process single items consecutively. Attached to FastAPI lifespan.
- ✅ Exposed endpoint `POST /api/v1/documents/upload` fulfilling architecture envelope standards and Pydantic models.
- ✅ Size limitation and single content type guards function properly within route.
- ✅ All regression constraints observed and 5x simulation concurrency checks completed returning 202 Accepted.
- ✅ 100% of tasks completed. Test coverage added successfully with 28 passing integration and unit tests total.

### File List
- `backend/app/services/processing_queue.py` (New: Single worker queue manager)
- `backend/app/schemas/queue.py` (New: Envelope model definitions)
- `backend/app/api/v1/documents.py` (Modified: Upload PDF handler logic)
- `backend/app/core/config.py` (Modified: Upload & queue restrictions)
- `backend/app/main.py` (Modified: Lifespan queue execution)
- `backend/tests/test_upload_queue.py` (New: Safety/unit testing suite)
- `backend/requirements.txt` (Modified: pytest-asyncio and httpx added for HTTP integration validation)
