# Story 2.1: Bounded Question Generation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Student,
I want the system to generate a quiz specifically from the topics I selected,
so that I am tested only on the material I am currently trying to master.

## Acceptance Criteria

1. **Given** the user has selected specific `node_id`s in the knowledge graph
2. **When** the Quiz Engine initializes
3. **Then** the backend retrieves only the text embeddings corresponding to the child clusters of the selected nodes
4. **And** the Question Gen Agent generates 1 Multiple Choice or Short Answer question grounded strictly in that retrieved context.

## Tasks / Subtasks

- [x] Task 1: LangGraph State Schema & Foundation (AC: All)
  - [x] Define `SocraticState` TypedDict in `backend/app/graph/state.py` with fields: `selected_node_ids`, `retrieved_chunks`, `current_question`, `question_type`, `trace_log`
  - [x] Create `backend/app/graph/orchestrator.py` with basic StateGraph initialization and SQLite checkpointer
  - [x] Write unit tests for state schema validation

- [x] Task 2: Context-Bounded RAG Retrieval Node (AC: 1, 3)
  - [x] Implement `retrieve_by_nodes` function in `backend/app/services/vector_store.py` to query embeddings by `node_id` list
  - [x] Create `backend/app/graph/nodes/retrieve.py` with retrieval node that populates `retrieved_chunks` in state
  - [x] Add hierarchical expansion logic: if parent node selected, include all children
  - [x] Write unit tests with mock vector data

- [x] Task 3: Question Generation Node (AC: 4)
  - [x] Create `backend/app/graph/nodes/question_gen.py` with LLM-powered question generator
  - [x] Implement prompt templates for Multiple Choice and Short Answer formats
  - [x] Ensure generated questions reference only content from `retrieved_chunks`
  - [x] Add `trace_log` entry for question generation step
  - [x] Write unit tests for question generation logic

- [x] Task 4: Quiz Initialization API Endpoint (AC: 1, 2)
  - [x] Implement `POST /api/v1/quiz/init` in `backend/app/api/v1/chat.py`
  - [x] Accept request body: `{ "selected_node_ids": ["node_1", "node_2"] }`
  - [x] Invoke LangGraph orchestrator to trigger retrieval → question generation flow
  - [x] Return response: `{ "status": "success", "data": { "question": {...}, "question_type": "..." }, "trace_id": "..." }`
  - [x] Write integration tests for the complete flow

- [x] Task 5: Frontend Quiz Initialization Integration (AC: 2)
  - [x] Create `frontend/src/api/quiz.ts` with `initQuiz(nodeIds: string[])` function
  - [x] Create `frontend/src/stores/quiz.ts` Pinia store with `selectedNodeIds`, `currentQuestion`, `questionType` state
  - [x] Update "Start Quiz" button handler in knowledge graph view to call API with selected nodes
  - [x] Create basic `frontend/src/views/QuizView.vue` to display generated question
  - [x] Write component tests for quiz initialization flow

## Dev Notes

### Relevant Architecture Patterns and Constraints

- **LangGraph State Management**: All conversational state must flow through LangGraph's `SocraticState` TypedDict. The state is persisted via SQLite Checkpointer to survive server restarts.
- **RAG Context Boundary**: Retrieval MUST be scoped to the selected `node_id`s to prevent question generation from bleeding into unrelated topics. Implement hierarchical expansion: selecting a parent node includes all descendant chunks.
- **Question Grounding**: The Question Gen Agent must be explicitly prompted to ONLY use content from `retrieved_chunks`. Include anti-hallucination instruction in system prompt.
- **SSE Foundation**: While this story focuses on synchronous question generation, the graph structure must support future SSE streaming (Epic 2.2). Design nodes to be composable for streaming workflows.
- **Memory Constraints (2C2G)**: LLM inference is outsourced to external APIs (DeepSeek/GLM). Local processing only handles text chunking and SQLite queries. No heavy in-memory operations.

### Source Tree Components to Touch

**Backend (New Files):**
- `backend/app/graph/state.py` - LangGraph state schema definition
- `backend/app/graph/orchestrator.py` - Graph compilation and execution
- `backend/app/graph/nodes/retrieve.py` - RAG retrieval node
- `backend/app/graph/nodes/question_gen.py` - Question generation node

**Backend (Modifications):**
- `backend/app/services/vector_store.py` - Add `retrieve_by_nodes()` method
- `backend/app/api/v1/chat.py` - Implement quiz initialization endpoint

**Frontend (New Files):**
- `frontend/src/api/quiz.ts` - Quiz API client
- `frontend/src/stores/quiz.ts` - Quiz state management (Pinia)
- `frontend/src/views/QuizView.vue` - Quiz interface

**Frontend (Modifications):**
- Update knowledge graph view "Start Quiz" button to call new API

### Testing Standards Summary

- **Unit Tests**: All LangGraph nodes must have isolated unit tests with mocked dependencies
- **Integration Tests**: End-to-end test from API endpoint through graph execution to question generation
- **Test Coverage**: Minimum 80% coverage for `backend/app/graph/` module
- **Test Data**: Use fixture-based test data from Story 1.3's knowledge extraction (ensure test documents have known node hierarchies)

## Developer Context

### Project Structure Notes

**Alignment with Unified Project Structure:**
- Backend graph logic follows strict separation: `backend/app/graph/` for orchestration, `backend/app/graph/nodes/` for individual node implementations
- Frontend follows Vue 3 Composition API with `<script setup>` syntax
- All API routes under `backend/app/api/v1/` namespace
- Pinia stores in `frontend/src/stores/` for client-side state management

**File Organization Principles:**
- One node = one file in `backend/app/graph/nodes/`
- Avoid monolithic graph files - keep orchestrator.py lean, delegate to node modules
- Frontend API clients in `frontend/src/api/` mirror backend route structure

### Technical Requirements

**LangGraph Implementation:**
- Use `langgraph` (latest stable version) with `StateGraph` and typed state via `TypedDict`
- Configure SQLite checkpointer: `SqliteSaver.from_conn_string(db_path)`
- State schema must include all fields needed for Epic 2 stories (question, answer validation, hints)
- Graph must support both synchronous invocation (`invoke()`) and streaming (`astream()`) for future SSE needs

**RAG Retrieval Logic:**
- Query `knowledge_nodes` table to expand selected `node_id`s to all descendants
- Use `sqlite-vec` similarity search on `chunk_embeddings` filtered by expanded node list
- Return top-k chunks (k=5 default) with relevance scores
- Implement safety check: if no chunks retrieved, return error instead of hallucinating

**Question Generation:**
- Use external LLM API (configured via `app/core/config.py`)
- Prompt structure: `[System: Only use provided context] [Context: {chunks}] [Task: Generate 1 question]`
- Support two question types: `multiple_choice` (4 options, 1 correct) and `short_answer`
- Question schema: `{ "question_text": str, "options": list[str] | null, "correct_answer": str }`

**API Design:**
- Endpoint: `POST /api/v1/quiz/init`
- Request: `{ "selected_node_ids": string[] }`
- Response: Standard envelope `{ "status": "success", "data": { "question": {...}, "question_type": "..." }, "trace_id": "..." }`
- Error handling: Return 400 if no nodes selected, 500 if LLM API fails

### Architecture Compliance

**Data Contract Adherence:**
- All backend JSON responses use `snake_case` (matching Python conventions)
- Frontend TypeScript interfaces mirror backend Pydantic models with `snake_case` keys
- No camelCase transformation in API layer - keep raw `snake_case` throughout

**State Management Boundaries:**
- **Backend (Source of Truth)**: LangGraph state persisted in SQLite
- **Frontend (Presentation Layer)**: Pinia store caches current question for UI rendering
- Frontend NEVER modifies question content - it only displays and submits answers

**Component Responsibilities:**
- **API Routes** (`backend/app/api/v1/chat.py`): Lightweight request validation, invoke graph, return response
- **Graph Orchestrator** (`backend/app/graph/orchestrator.py`): Define edges, compile graph, manage execution
- **Graph Nodes** (`backend/app/graph/nodes/*.py`): Pure functions that transform state
- **Services** (`backend/app/services/*.py`): Database and external API interactions

**Memory Safety (2C2G Constraints):**
- NO in-memory embedding generation - use external embedding API
- NO model loading - all inference via external LLM API
- Limit retrieved chunks to max 5 to constrain prompt size
- Use streaming responses for future SSE to avoid buffering

### Library & Framework Requirements

**Backend:**
- `langgraph` - State graph orchestration
- `langchain-openai` - LLM client for question generation
- `sqlite-vec` - Vector similarity search
- `pydantic` - State schema validation
- `fastapi` - API framework

**Frontend:**
- `pinia` - State management
- `axios` or `fetch` - HTTP client for API calls
- `vue-router` - Navigation to quiz view
- `typescript` - Type safety for API contracts

**Testing:**
- `pytest` - Backend unit and integration tests
- `pytest-asyncio` - Async test support
- `vitest` - Frontend component tests

### Previous Story Intelligence

**From Story 1.4 (Contract-Driven Outline Scope Selection):**
- The frontend already has Pinia store for selected `node_id`s from knowledge graph
- Knowledge graph selection logic is implemented - reuse the `selectedNodeIds` state
- AntV G6 graph view has "Start Quiz" button that needs to trigger the new quiz initialization flow

**From Story 1.3 (Memory-Safe Hierarchical RAG Extraction):**
- `knowledge_nodes` table is populated with hierarchical structure (`parent_id` relations)
- Embeddings are stored in `chunk_embeddings` virtual table using `sqlite-vec`
- Retrieval pattern: Query by `node_id`, get associated chunks and embeddings

**From Story 1.1 (Project Scaffold):**
- Backend follows strict `snake_case` naming for all variables, functions, and JSON keys
- Frontend uses Composition API with `<script setup>` syntax
- API responses wrapped in standard envelope: `{ "status": "...", "data": {...}, "message": "...", "trace_id": "..." }`

**Key Learnings:**
- Previous stories established the data contract pattern - strictly enforce schema compliance
- Memory safety is critical - use generators and streaming patterns wherever possible
- Test coverage prevents regressions - write tests BEFORE marking tasks complete

### External API Integration Notes

**LLM Provider Configuration:**
- Use environment variables for API keys (never hardcode)
- Configure via `app/core/config.py` using `pydantic-settings`
- Support multiple providers (DeepSeek, GLM) with fallback logic
- Implement retry with exponential backoff for transient failures
- Timeout: 10s for question generation (fast user feedback)

**Embedding API:**
- Reuse embedding service from Story 1.3 for consistency
- Cache embeddings in SQLite to avoid redundant API calls
- No need to re-embed at quiz time - only retrieve pre-computed embeddings

### Trace Logging for Technical Observability

- Add `trace_log` field to `SocraticState` as `list[dict]`
- Each node appends entry: `{ "node": "retrieve", "timestamp": "...", "metadata": {...} }`
- Include in API response under `trace_id` field
- Foundation for Story 2.4's real-time SSE trace streaming

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#LangGraph State Management]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/prd.md#FR5 - Question Generation]
- [Source: _bmad-output/implementation-artifacts/1-3-memory-safe-hierarchical-rag-extraction.md#RAG Retrieval Pattern]
- [Source: _bmad-output/implementation-artifacts/1-4-contract-driven-outline-scope-selection.md#Pinia State Management]

## Change Log

- 2026-04-03: Story created from Epic 2 with comprehensive context analysis
- 2026-04-03: Story implementation completed - all 5 tasks done

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4.5)

### Debug Log References

- Installed `langgraph-checkpoint-sqlite` (v3.0.3) for SQLite checkpointer support
- Fixed format_context to handle empty/whitespace-only chunk_text
- Fixed test mock paths for question_gen_node tests

### Completion Notes List

**Task 1: LangGraph State Schema & Foundation**
- Created `SocraticState` TypedDict with all required fields
- Implemented `orchestrator.py` with StateGraph and SQLite checkpointer
- Added 13 unit tests for state schema validation

**Task 2: Context-Bounded RAG Retrieval Node**
- Implemented `retrieve_by_nodes` function with hierarchical expansion (recursive CTE)
- Created `retrieve_node` LangGraph node with proper error handling
- Added 16 unit tests for retrieval logic

**Task 3: Question Generation Node**
- Implemented LLM-powered question generator with anti-hallucination prompts
- Added support for both multiple_choice and short_answer types
- Created 21 unit tests for question generation

**Task 4: Quiz Initialization API Endpoint**
- Implemented `POST /api/v1/quiz/init` endpoint with standard envelope response
- Added proper error handling and trace logging
- Created 10 integration tests for API

**Task 5: Frontend Quiz Initialization Integration**
- Created `quiz.ts` API client with TypeScript types
- Extended Pinia store with quiz state management
- Updated QuizView.vue with full quiz UI (loading, error, question display)
- Frontend build successful

### File List

**Backend (New Files):**
- backend/app/graph/state.py
- backend/app/graph/orchestrator.py
- backend/app/graph/nodes/retrieve.py
- backend/app/graph/nodes/question_gen.py
- backend/app/services/question_generator.py
- backend/app/schemas/quiz.py
- backend/tests/test_graph_state.py
- backend/tests/test_retrieve_node.py
- backend/tests/test_question_gen.py
- backend/tests/test_quiz_api.py

**Backend (Modified Files):**
- backend/app/services/vector_store.py (added retrieve_by_nodes, get_descendant_node_ids)
- backend/app/api/v1/chat.py (implemented quiz/init endpoint)
- backend/app/api/v1/__init__.py
- backend/app/graph/__init__.py
- backend/app/graph/nodes/__init__.py
- backend/app/main.py (registered chat router)

**Frontend (New Files):**
- frontend/src/api/quiz.ts

**Frontend (Modified Files):**
- frontend/src/stores/quiz.ts (extended with quiz state)
- frontend/src/views/QuizView.vue (full quiz UI)
