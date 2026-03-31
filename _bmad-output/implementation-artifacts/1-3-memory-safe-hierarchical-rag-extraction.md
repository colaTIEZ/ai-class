# Story 1.3: 内存安全的分层萃取引擎 (Memory-Safe Hierarchical RAG Extraction)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a System,
I need to parse PDFs using a generator pattern and extract a rigid logical hierarchy,
so that memory stays below 1.5GB and the frontend gets the precise parent-child mapping it needs for tree rendering.

## Acceptance Criteria

1. **Given** an uploaded PDF passed to the processing worker (in `backend/app/services/processing_queue.py`)
2. **When** PyMuPDF reads the file
3. **Then** the text must be chunked using a Python Generator pattern (Yielding chunks one by one) to strictly prevent loading >10MB of raw strings into memory at once
4. **And** the extraction logic must generate a hierarchical structure (Chapter -> Section -> Chunk) mapped to the schema defined in `backend/app/schemas/knowledge_tree.py` (with `parent_id` relations)
5. **And** all generated chunks and embeddings are safely committed to the local `SQLite-vec` database.

## Tasks / Subtasks

- [x] Task 1: Create Memory-Safe PDF Parser (AC: 1, 2, 3)
  - [x] Create `backend/app/services/pdf_parser.py` using PyMuPDF (`fitz`).
  - [x] Implement a generator function that yields text blocks page by page without loading the entire document's text into memory at once.
  - [x] Implement chunking logic on the text iterator matching the expected OpenAI embedding context limits (e.g., 500-1000 tokens per chunk).
- [x] Task 2: Hierarchical Node Extraction & OpenAI Embedding Integration (AC: 4, 5)
  - [x] Implement heuristic regex parsing or LLM-assisted lightweight parsing to identify "Chapters", "Sections" and standard "Chunks" from the text blocks.
  - [x] Generate unique `node_id`s in the format `doc_{doc_id}_node_{seq}` and establish `parent_id` linkages across the hierarchy.
  - [x] Integrate with `langchain-openai` (text-embedding-3-small, 1536 dim) to convert chunk text to embeddings.
- [x] Task 3: SQLite-vec Database Insertion (AC: 5)
  - [x] Create insertion functions mapped to the existing `knowledge_nodes` relational rows and `vec_embeddings` virtual table entries in `backend/app/services/vector_store.py`.
  - [x] Wrap insertions in SQL transactions to ensure consistency.
  - [x] Replace the mock logic in `ProcessingQueue._worker` with the actual parsing execution, passing the `file_path`.
- [x] Task 4: CPU-Bound Operation Delegation & Error Handling
  - [x] Ensure PyMuPDF operations are run in `asyncio.to_thread` or thread pools to prevent blocking the async event loop.
  - [x] Wrap external OpenAI API calls in robust try-catch blocks with retry fallback.

## Dev Notes

### Technical Requirements
- Initialize PyMuPDF via `fitz.open()` and iterate pages lazily `for page in doc: text = page.get_text()`. Never load all pages into memory at once via `for text in page.get_text(...)`.
- The embedding API limit: batch process chunks efficiently, keeping memory requirements low (no massive lists caching chunks).
- **CRITICAL Guardrails**: Never store all embedded vectors in a single memory array. Batches of 50-100 should be committed and memory cleared.

### Architecture Compliance
- We strictly use `snake_case` in DB and APIs.
- Refer strictly to `backend/app/schemas/knowledge_tree.py` for exact data structures representing the nodes to ensure parity with the frontend's AntV G6 hierarchy graph.

### File Structure Requirements
- `backend/app/services/pdf_parser.py` (New)
- `backend/app/services/vector_store.py` (Enhancement)
- `backend/app/services/processing_queue.py` (Integration)

### Previous Story Intelligence
- **Worker Concurrency**: The Queue implemented in 1.2 isolates jobs utilizing `asyncio.to_thread`. Since PDF parsing is CPU-bound, ensure this threading is maintained and the async loop doesn't stall.
- **Exceptions**: The `ProcessingQueue._worker` catches `BaseException` but expects descriptive errors for proper terminal error handling (`-1` status). Throw proper exceptions from the parser if corrupted PDFs are hit.

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Requirements to Structure Mapping]
- [Source: backend/app/schemas/knowledge_tree.py]
- [Source: backend/app/services/vector_store.py]

## Dev Agent Record

### Agent Model Used
Gemini 3.1 Pro (High)

### Debug Log References

### Completion Notes List
- ✅ Implemented memory-safe `process_pdf_generator` using PyMuPDF `fitz` lazy page evaluation, preventing wholesale string load into memory.
- ✅ Developed heuristic regex-based `extract_hierarchy` mapping parsed chunks to 1.1 Schema with proper parent-child linkage.
- ✅ Successfully integrated `langchain_openai` embeddings processing on batches. Handled fallback when testing locally without an API key mapping to dummy representations.
- ✅ Hooked up to synchronous SQLite-vec inserts within transactions ensuring no partially generated state corrupts the database.
- ✅ Ensured pure asynchronous compatibility by dispatching entire PDF extraction cycle inside an isolated `asyncio.to_thread` operation inside `processing_queue`.
- ✅ All regression and unit tests passing `100%`.

### File List
- `backend/app/services/pdf_parser.py` (New: PDF chunking and hierarchy mapping)
- `backend/app/services/vector_store.py` (Modified: Added batched data/vector insertions)
- `backend/app/services/processing_queue.py` (Modified: Replaced mock extraction with thread-safe live RAG pipeline)
- `backend/tests/test_pdf_parser.py` (New: Validation rules and tests for generator outputs)

### Review Findings
- [x] [Review][Decision] 缺少数据库和队列集成 — 经核实，`vector_store.py` 和 `processing_queue.py` 中已包含完整的集成逻辑。
- [x] [Review][Patch] 章节标题可能为空 — 已在 `pdf_parser.py` 中添加后备默认标签。

