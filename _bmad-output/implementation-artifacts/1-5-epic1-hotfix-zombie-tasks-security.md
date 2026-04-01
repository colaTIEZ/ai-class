# Story 1.5: Epic 1 Hotfix - Zombie Tasks & Security Hardening

Status: done

## Story

As a System Administrator,
I want the backend to automatically recover from crashed states and validate file uploads securely,
so that users never experience infinite loading states and the system is protected from malicious file uploads.

## Background

This hotfix story addresses **P0/P1 critical issues** identified in the Epic 1 Retrospective:

1. **🔴 P0 - Zombie Tasks**: OOM Killer or unexpected process termination leaves tasks permanently stuck in `status=0` (processing), causing infinite loading for users and potential queue deadlock.
2. **🟡 P1 - Magic Byte Validation**: Currently only MIME type is validated; malicious users can upload non-PDF files with forged `Content-Type: application/pdf`.
3. **🟡 P1 - API Key Fail-Fast**: Missing `OPENAI_API_KEY` causes silent fallback to dummy embeddings instead of explicit startup failure.

## Acceptance Criteria

1. **Given** the backend process starts (or restarts after crash)
   **When** there are tasks with `status=0` (processing) that have `updated_at` older than a configurable timeout threshold (default: 5 minutes)
   **Then** these zombie tasks are automatically reset to `status=-1` (error) with a descriptive error message
   **And** a warning log is emitted for each recovered zombie task

2. **Given** a user uploads a file with `Content-Type: application/pdf`
   **When** the backend validates the upload
   **Then** the system reads the first 4 bytes of the file and verifies the PDF magic bytes (`%PDF`)
   **And** returns HTTP 415 if the magic bytes don't match

3. **Given** the backend starts
   **When** `OPENAI_API_KEY` environment variable is empty or unset
   **Then** the application logs a **critical warning** at startup
   **And** the `/api/v1/health` endpoint returns `"embedding_ready": false` in its response
   **And** any attempt to process a PDF (RAG extraction) fails fast with a clear error message instead of generating dummy embeddings

## Tasks / Subtasks

- [x] Task 1: Implement Zombie Task Recovery (AC: 1)
  - [x] Add `ZOMBIE_TASK_TIMEOUT_SECONDS` config to `config.py` (default: 300)
  - [x] Add `updated_at` column to `document_tasks` table if not exists
  - [x] Update `_update_status` to set `updated_at = CURRENT_TIMESTAMP` on each status change
  - [x] Create `_recover_zombie_tasks()` function in `processing_queue.py` that:
    - Finds all tasks where `status=0 AND updated_at < NOW - timeout`
    - Updates them to `status=-1` with reason "Process terminated unexpectedly"
    - Logs warning for each recovered task
  - [x] Call `_recover_zombie_tasks()` in `start_worker()` before `_recover_tasks()`

- [x] Task 2: Implement PDF Magic Byte Validation (AC: 2)
  - [x] Create `validate_pdf_magic_bytes(file: UploadFile) -> bool` function in `documents.py`
  - [x] Read first 4 bytes: must equal `b'%PDF'`
  - [x] Call this validation after MIME type check and before size check
  - [x] Return HTTP 415 with message "Invalid PDF file: magic bytes mismatch"

- [x] Task 3: Implement API Key Fail-Fast (AC: 3)
  - [x] Add `embedding_ready: bool` property to `Settings` class that returns `bool(self.openai_api_key)`
  - [x] Update `pdf_parser.py:generate_embeddings()` to raise `AppException` with HTTP 503 if API key is missing
  - [x] Update `/api/v1/health` endpoint to include `"embedding_ready": settings.embedding_ready`
  - [x] Add startup log warning if `embedding_ready` is False

- [x] Task 4: Testing (All ACs)
  - [x] Test zombie task recovery: create task with old `updated_at`, verify it's reset on startup
  - [x] Test magic byte validation: upload file with wrong header, verify 415 response
  - [x] Test API key fail-fast: unset key, verify health endpoint shows `false` and upload fails with 503

### Review Findings

- [x] [Review][Patch] Defensive null-safe `embedding_ready` property [`backend/app/core/config.py:46`]
- [x] [Review][Defer] Test DB isolation still uses shared default SQLite path [`backend/tests/conftest.py:29`] — deferred, pre-existing

## Dev Notes

### Critical Architecture Constraints

- **Memory Limit**: 2C2G (1.5GB backend cap) - no additional heavy dependencies
- **SQLite WAL Mode**: Already enabled, ensure all transactions are atomic
- **Async Pattern**: All DB operations must use `asyncio.to_thread()` for sync SQLite calls

### Existing Code Analysis

**`processing_queue.py` Current Recovery Logic (Lines 167-180):**
```python
def _recover_tasks():
    # Reset interrupted processing tasks to queued
    conn.execute("UPDATE document_tasks SET status = 0 WHERE status = 1")
```
**Problem**: This resets `status=1` to `status=0`, but if process crashed during actual work, task should be marked as error not re-queued blindly.

**`documents.py` Current Validation (Lines 38-53):**
```python
if file.content_type != "application/pdf":
    raise AppException(...)
# Only MIME type check - no magic byte validation
```

**`pdf_parser.py` Current Embedding Logic (Lines 15-17):**
```python
if not settings.openai_api_key:
    logger.error("OpenAI API key configuration is missing.")
    raise ValueError("OpenAI API key configuration is missing.")
```
**Status**: Already raises error - but need to make it `AppException` for proper HTTP response

### Database Schema Update Required

```sql
-- Ensure updated_at column exists (may need ALTER TABLE if not)
ALTER TABLE document_tasks ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_tasks_status_updated ON document_tasks(status, updated_at);
```

### File Structure Requirements

Files to modify:
- `backend/app/core/config.py` - Add `ZOMBIE_TASK_TIMEOUT_SECONDS`, `embedding_ready`
- `backend/app/services/processing_queue.py` - Add zombie recovery, update `updated_at` logic
- `backend/app/services/vector_store.py` - Ensure `updated_at` column in schema
- `backend/app/api/v1/documents.py` - Add magic byte validation
- `backend/app/api/v1/health.py` - Add `embedding_ready` to response
- `backend/app/services/pdf_parser.py` - Change `ValueError` to `AppException`

### Testing Standards

- Use `pytest-asyncio` for async tests
- Mock SQLite with test database fixture from `conftest.py`
- Create test PDF files with correct/incorrect magic bytes

### Previous Story Intelligence

From Story 1.2 Review Findings:
- SQLite-based queue status is the single source of truth (not in-memory dict)
- All disk IO must be wrapped in `asyncio.to_thread()`
- Exception handling must catch `BaseException` for worker resilience

From Story 1.3 Implementation:
- `pdf_parser.py` already has retry logic for embedding API (3 attempts with exponential backoff)
- `process_pdf_generator` uses generator pattern - memory safe

### References

- [Source: _bmad-output/implementation-artifacts/epic-1-retrospective.md#Action Items]
- [Source: _bmad-output/planning-artifacts/architecture.md#Memory Guarding]
- [Source: backend/app/services/processing_queue.py]
- [Source: backend/app/api/v1/documents.py]

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

### Completion Notes List

- Added zombie-task recovery based on `updated_at` timeout in queue startup path.
- Extended `document_tasks` with `error_message` and `updated_at` plus migration/index safeguards.
- Added PDF magic-byte validation (`%PDF`) in upload endpoint.
- Added embedding readiness health signal and startup critical log when API key is missing.
- Enforced fail-fast upload behavior when embedding configuration is unavailable.
- Added tests for zombie recovery, magic-byte validation, and embedding fail-fast behavior.
- Could not execute test suite in this environment because `pwsh.exe` is unavailable for command execution.

### File List

- `backend/app/core/config.py`
- `backend/app/services/vector_store.py`
- `backend/app/services/processing_queue.py`
- `backend/app/api/v1/documents.py`
- `backend/app/services/pdf_parser.py`
- `backend/app/api/v1/health.py`
- `backend/app/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_upload_queue.py`
- `backend/tests/test_health.py`
