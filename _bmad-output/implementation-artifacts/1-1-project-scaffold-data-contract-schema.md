# Story 1.1: Project Scaffold & Data Contract Schema

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Developer,
I want to initialize the frontend and backend with strict predefined data schemas,
so that both sides can work independently without hallucinating formats, and the infrastructure is proven stable on limited hardware.

## Acceptance Criteria

1. **Given** a clean project directory
   **When** I run the initialization scripts
   **Then** the backend must expose a strict `schemas/knowledge_tree.py` contract enforcing fields: `node_id, label, parent_id, content_summary`
2. **And** the backend must load a local SQLite database with `sqlite-vec` extension successfully
3. **And** a dedicated "vector similarity test script" must execute and pass to prove the C-extensions for sqlite-vec are working stably on the host
4. **And** the frontend can communicate with a basic "Hello World" API endpoint.

## Tasks / Subtasks

- [x] Task 1: Initialize Backend Project (AC: 1, 2)
  - [x] Initialize Python environment and install required packages (`fastapi uvicorn langgraph langchain-openai sqlite-vec pydantic-settings python-multipart PyMuPDF`).
  - [x] Set up the backend folder structure according to the architecture document (`backend/app`, `backend/data`, etc.).
  - [x] Create `schemas/knowledge_tree.py` with `node_id`, `label`, `parent_id`, `content_summary`.
- [x] Task 2: Setup SQLite with sqlite-vec (AC: 2, 3)
  - [x] Configure SQLite connection with `sqlite-vec` extension loaded.
  - [x] Create a vector similarity test script (e.g., `backend/tests/test_vector.py`) to verify the C-extensions work.
- [x] Task 3: Initialize Frontend Project (AC: 4)
  - [x] Run Vite initialization (`npm create vite@latest frontend -- --template vue-ts`).
  - [x] Install Tailwind CSS v4.
  - [x] Set up a basic "Hello World" ping to the backend API.
- [x] Task 4: API Integration Test (AC: 4)
  - [x] Start both frontend and backend servers.
  - [x] Ensure frontend can successfully call a backend test endpoint (e.g., `/api/v1/health`), respecting the predefined JSON API envelope rules.

## Dev Notes

- **Relevant architecture patterns and constraints**: 
  - 2C2G memory limits must be strictly observed.
  - SQLite is the main database and vector store. Backend logic must be pure orchestrator.
  - Must establish rigid `snake_case` JSON responses.
  - RESTful API format with `{ "status": "success", "data": { ... }, "message": "", "trace_id": "" }` wrapper.
- **Source tree components to touch**:
  - `frontend/` (Vite + Vue 3 scaffolding)
  - `backend/app/` (FastAPI scaffolding)
  - `backend/app/schemas/` 
  - `backend/app/api/v1/`
  - `backend/data/` (SQLite storage mount)
- **Testing standards summary**:
  - Script test for vector similarity should be explicitly run.

### Project Structure Notes

- **Alignment with unified project structure**:
  - Front-end must be in `/frontend` folder.
  - Back-end must be in `/backend` folder.

### Technical Requirements
- Node.js environment required for frontend setup.
- Python 3.10+ required for backend setup.
- Data Exchange Formats: Date format must use ISO 8601 UTC string (`2026-03-31T00:00:00Z`).

### Architecture Compliance
- Strict separation of frontend (`Vue 3 + Tailwind CSS`) and backend (`FastAPI + SQLite + SQLite-VEC`).
- API formats: All non-streaming APIs must strictly return `{ "status": "...", "data": {}, "message": "", "trace_id": "" }`.
- Naming Patterns: Backend must enforce `snake_case` for all variable and file names, frontend Vue components use `PascalCase`.

### Library & Framework Requirements
- Backend: FastAPI, Uvicorn, LangGraph, langchain-openai, sqlite-vec, pydantic-settings, python-multipart, PyMuPDF.
- Frontend: Vue 3, Vite, TailwindCSS v4, TypeScript.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]

## Change Log

- 2026-03-31: Initial implementation — project scaffold, data contracts, sqlite-vec integration, frontend/backend connectivity established.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (Thinking)

### Debug Log References
- sqlite-vec KNN query requires `k = ?` constraint instead of `LIMIT` — fixed in test_vector.py

### Completion Notes List
- ✅ Backend scaffolded with full architecture-compliant directory structure
- ✅ `schemas/knowledge_tree.py` enforces strict `node_id, label, parent_id, content_summary` contract via Pydantic
- ✅ SQLite + sqlite-vec extension loads and works — KNN similarity search verified with 8 passing tests
- ✅ WAL mode enabled for SQLite concurrent access resilience
- ✅ Frontend initialized with Vue 3 + Vite + TailwindCSS v4 + TypeScript
- ✅ API proxy configured in vite.config.ts for dev server backend communication
- ✅ Health check endpoint returns standard API envelope format `{status, data, message, trace_id}`
- ✅ Frontend HealthCheck component calls backend and displays connectivity status
- ✅ TypeScript interfaces mirror backend Pydantic models (shared data contract)
- ✅ Full test suite: 24 tests pass (schemas, health endpoint, vector similarity, integration)
- ✅ Frontend TypeScript type check and production build both pass

### File List
- backend/.venv/ (Python virtual environment)
- backend/requirements.txt
- backend/data/.gitkeep
- backend/app/__init__.py
- backend/app/main.py
- backend/app/core/__init__.py
- backend/app/core/config.py
- backend/app/core/exceptions.py
- backend/app/api/__init__.py
- backend/app/api/v1/__init__.py
- backend/app/api/v1/health.py
- backend/app/api/v1/documents.py (placeholder)
- backend/app/api/v1/chat.py (placeholder)
- backend/app/graph/__init__.py (placeholder)
- backend/app/graph/nodes/__init__.py (placeholder)
- backend/app/services/__init__.py
- backend/app/services/vector_store.py
- backend/app/schemas/__init__.py
- backend/app/schemas/knowledge_tree.py
- backend/tests/__init__.py
- backend/tests/conftest.py
- backend/tests/test_health.py
- backend/tests/test_schemas.py
- backend/tests/test_vector.py
- backend/tests/test_integration.py
- frontend/vite.config.ts (modified)
- frontend/src/style.css (replaced)
- frontend/src/api/client.ts
- frontend/src/types/index.ts
- frontend/src/components/HelloWorld.vue (replaced)
- .env.example
