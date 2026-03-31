# Story 1.4: 基于数据契约的大纲可视化与范围圈选 (Contract-Driven Outline Scope Selection)

Status: done

## Story

As a Student,
I want to see a visual tree of my course material and select specific nodes,
So that I can constrain the RAG context for the Quiz Engine and trigger the actual test phase.

## Acceptance Criteria

1. **Given** the backend has populated the SQLite database according to the `knowledge_tree` schema
2. **When** the user accesses the document view
3. **Then** the Vue 3 frontend strictly consumes the `node_id`, `label`, `parent_id` fields to render an interactive AntV G6 hierarchy graph
4. **And** I can visually select specific leaf nodes or parent branches
5. **And** clicking "Start Quiz" persists the selected `node_id` array to the active session state and routes the user to the pending Epic 2 Quiz UI.

## Tasks / Subtasks

- [x] Task 1: Backend API for Hierarchical Knowledge Tree
  - [x] Implement `GET /api/v1/documents/{document_id}/tree` in `documents.py` to recursively fetch or flat-fetch `knowledge_nodes`.
  - [x] Ensure JSON response keys are `snake_case` (`node_id`, `label`, `parent_id`).
  - [x] Write unit tests for API behavior in `backend/tests/`.
- [x] Task 2: Frontend State & API Integration
  - [x] Create `frontend/src/api/documents.ts` with typed definitions for tree fetching.
  - [x] Create `frontend/src/stores/quiz.ts` Pinia store for tracking selected `node_id`s.
- [x] Task 3: AntV G6 Knowledge Graph Component
  - [x] Create `frontend/src/components/graph/KnowledgeGraph.vue`.
  - [x] Render fetched data using AntV G6 5.x TreeGraph or similar layout.
  - [x] Implement node selection logic (visual feedback + cascading selection if parent is clicked).
- [x] Task 4: UI Assembly & Routing
  - [x] Integrate `KnowledgeGraph.vue` in document view page.
  - [x] Add "Start Quiz" button. Sync button disabled state with Pinia selection state.
  - [x] Add Vue Router navigation to Epic 2 UI upon clicking button.

## Developer Context

### Technical Requirements
- The frontend must retrieve the parsed knowledge tree from the backend via an API (e.g., `GET /api/v1/documents/{document_id}/tree`).
- The rendering should use AntV G6 (Version 5.0+) for hierarchical tree layout. (Preferably an indented tree or mindmap layout suitable for course outlines).
- The user must be able to select one or multiple nodes (checkboxes or node click states).
- If a parent node is selected, visually indicate that all child nodes are included.
- The selected nodes' IDs must be saved in Pinia store (e.g., `useQuizStore`) to be used as context boundary constraints for Epic 2.
- The UI should have a "Start Quiz" button that is enabled only when at least one node is selected. Clicking it transitions to the Quiz UI.

### Architecture Compliance
- Vue 3 CSR architecture. All complex visualization and state persistence is offloaded to the browser.
- Pinia is strictly used for the UI session state (storing the selected `node_id`s).
- API integration must use Axios or native Fetch client under `frontend/src/api/`.
- Frontend UI must follow Tailwind CSS v4 styling matching the rest of the application.
- API requests and responses strictly adhere to `snake_case`.

### Library & Framework Requirements
- Vue 3 (Composition API, `<script setup>`)
- `@antv/g6` (5.0+) - Ensure the latest API is used for tree graphs.
- `pinia` for state management.
- `vue-router` for navigation.

### File Structure Requirements
- `frontend/src/components/graph/KnowledgeGraph.vue` (New)
- `frontend/src/stores/quiz.ts` (New)
- `frontend/src/api/documents.ts` (Modification: fetch tree endpoint)
- `backend/app/api/v1/documents.py` (Modification: provide tree structure endpoint, if not provided)

### Previous Story Intelligence
- In Story 1.3, the backend extracted the knowledge into `SQLite-vec` with `knowledge_nodes` matching the `node_id`, `label`, `parent_id` schema.
- The schema is rigorously enforced. The frontend must handle varying tree depths safely.
- All JSON keys from the backend will be in `snake_case` (e.g., `node_id`, NOT `nodeId`). Do not transform them in the frontend mapping layer; keep them as `snake_case` constants or interfaces.

### Project Context Reference
- Epic 1: 课件解析、边界圈选与高可用并发控制
- Architecture: Vue 3 CSR, Strict API Data Contract, Pinia for isolated session state handling.

> **Completion Note:** Ultimate context engine analysis completed - comprehensive developer guide created

## Dev Agent Record

### Debug Log
- N/A

### Completion Notes List
- Evaluated SQLite DB schema and added `get_document_nodes` to `vector_store.py` to fetch nodes corresponding to a `document_id`.
- Created `GET /api/v1/documents/{document_id}/tree` endpoint in `documents.py` to return the `KnowledgeTree` model containing `node_id`, `label`, `parent_id` matching our Strict Contract.
- Handled empty list correctly to return empty nodes instead of throwing 404 object not found.
- Handled async to_thread usage context properly, passing parameters safely to avoid runtime variable scope capture bugs.
- Created `frontend/src/api/documents.ts` defining fetch client and interfaces matching `snake_case` from backend (`node_id`, etc.).
- Created Vue Pinia store `useQuizStore` holding node IDs in array, logic handles recursion automatically on tree.
- Configured Vue Router, initializing the Pinia global state and the router properly in `main.ts` and `App.vue`.
- Built `KnowledgeGraph.vue` making use of AntV G6 5.x `Graph`, traversing data optimally and cascading node selection state effectively between UI states and Pinia `quizStore`.
- Implemented Mock Quiz view to correctly route User from Graph when `Start Quiz` is pressed, handling disabled buttons natively if no items selected.
- Successfully built frontend `npm run build` ensuring 100% type-checking and successful Vue-TSC compilation without issues.

### File List
- `d:\code\ai-class\backend\app\api\v1\documents.py` (Modified)
- `d:\code\ai-class\backend\app\services\vector_store.py` (Modified)
- `d:\code\ai-class\backend\tests\test_documents_tree.py` (New)
- `d:\code\ai-class\frontend\package.json` (Modified)
- `d:\code\ai-class\frontend\src\main.ts` (Modified)
- `d:\code\ai-class\frontend\src\App.vue` (Modified)
- `d:\code\ai-class\frontend\src\api\documents.ts` (New)
- `d:\code\ai-class\frontend\src\stores\quiz.ts` (New)
- `d:\code\ai-class\frontend\src\components\graph\KnowledgeGraph.vue` (New)
- `d:\code\ai-class\frontend\src\router\index.ts` (New)
- `d:\code\ai-class\frontend\src\views\DocumentView.vue` (New)
- `d:\code\ai-class\frontend\src\views\QuizView.vue` (New)

### Change Log
- Added `get_document_nodes` SQL query and `/tree` endpoint.
- Added Pinia, Vue Router, AntV G6 dependencies.
- Added `KnowledgeGraph` component and routing.
- Passed backend pytest API validation.
- Passed frontend TSC strict TS checks.
### Review Findings (Finalized)
- [x] [Review][Patch] 路径搜索检测逻辑可绕过 (pdf_parser.py:50) -> 已改为 Path.resolve() 校验
- [x] [Review][Patch] PDF 文档对象未闭合风险 (pdf_parser.py:92) -> 已改为 try/finally 闭合
- [x] [Review][Patch] UUID 哈希碰撞风险 (processing_queue.py:122) -> 已改为 8位 hex 转换 OID
- [x] [Review][Patch] 树构建无限递归风险 (KnowledgeGraph.vue:18) -> 已增加 visited Set 保护
- [x] [Review][Patch] 跨文档选中状态残留 (quiz.ts:6) -> 已增加 setActiveDocument 清理逻辑
- [x] [Review][Patch] G6 v5 事件兼容性 (KnowledgeGraph.vue:104) -> 已增强 e.target.id/itemId/item.id 获取
- [x] [Review][Patch] 排序确定性 (processing_queue.py:40) -> 已添加 ORDER BY created_at
- [x] [Review][Patch] 多根节点渲染补全 (KnowledgeGraph.vue:56) -> 已增加 root-container 封装
- [x] [Review][Patch] 存储 O(n) 性能优化 (quiz.ts:5) -> 已改为内部使用 Set
