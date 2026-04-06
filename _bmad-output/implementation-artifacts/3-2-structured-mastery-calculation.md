# Story 3.2: Structured Mastery Calculation

Status: done

## Story

As a Student,
I want the system to calculate a mastery score for each course chapter,
so that I have a quantifiable metric of my study progress.

## Acceptance Criteria

1. **Given** the user has answered questions
   **When** the system calculates stats
   **Then** a mastery score (percentage) is computed dynamically based on the ratio of successfully answered questions per `parent_id` cluster

2. **Given** mastery scores are available
   **When** the course outline graph renders in the UI
   **Then** the AntV G6 outline graph must show color-coded nodes based on mastery score bands (for example, red for low mastery and green for high mastery)

## Tasks / Subtasks

- [x] Task 1: Add backend mastery aggregation service (AC: #1)
  - [x] Implement a service function in `backend/app/services/review_service.py` (or a dedicated mastery service) to compute chapter-level mastery using `question_history` joined with `knowledge_nodes.parent_id`
  - [x] Enforce exclusion of invalidated records (`is_invalidated = 0`) and keep parity with Story 3.1 filtering semantics
  - [x] Return deterministic mastery payload per chapter cluster: attempted_count, correct_count, mastery_score

- [x] Task 2: Expose mastery API endpoint (AC: #1)
  - [x] Add a REST endpoint under `backend/app/api/v1/review.py` (or `documents.py`) that returns chapter mastery for the current user in standard envelope format `{ status, data, message, trace_id }`
  - [x] Keep API response keys in `snake_case` and timestamps in ISO 8601 when present
  - [x] Add/extend schemas in `backend/app/schemas/review.py` for strict response validation

- [x] Task 3: Integrate mastery into graph rendering (AC: #2)
  - [x] Load mastery map in the frontend graph flow and merge by node/chapter identity before rendering
  - [x] Update G6 node style mapping in `frontend/src/components/graph/KnowledgeGraph.vue` to apply consistent color bands based on mastery score
  - [x] Preserve existing selected-node interactions and recursive child-selection behavior

- [x] Task 4: Add frontend mastery visibility on review page (AC: #2)
  - [x] Surface chapter mastery metric in `frontend/src/views/ReviewPage.vue` for learning feedback continuity
  - [x] Keep UX non-blocking when mastery API is empty or partial; render graceful fallback state

- [x] Task 5: Add automated tests (AC: #1, #2)
  - [x] Backend unit tests for mastery computation edge cases: zero attempts, all wrong, all correct, mixed validity
  - [x] Backend API tests for envelope shape, user scoping, and invalidated exclusion
  - [x] Frontend tests for color-band rendering and fallback behavior when mastery payload is missing

### Review Findings

- [x] [Review][Patch] Mastery API failure currently blocks wrong-answer notebook rendering [frontend/src/views/ReviewPage.vue:74]
- [x] [Review][Patch] Document tree view fails hard when chapter mastery request errors instead of graceful fallback [frontend/src/views/DocumentView.vue:25]
- [x] [Review][Patch] Overall mastery percent is displayed as unweighted average of chapters, diverging from aggregate progress semantics [frontend/src/views/ReviewPage.vue:20]
- [x] [Review][Patch] Missing explicit all-correct backend mastery test despite Task 5 edge-case requirement [backend/tests/test_review_service.py:1]

## Dev Notes

### Relevant Architecture Patterns and Constraints

- Backend and DB naming remain `snake_case`; do not introduce camelCase in API payload keys.
- Keep API routes lightweight; business logic belongs in service layer, not route handler.
- Use standard non-stream response envelope: `status`, `data`, `message`, `trace_id`.
- Story 3.2 must continue the anti-hallucination guardrail from Story 3.1 by excluding invalidated records from metrics.

### Source Tree Components to Touch

- `backend/app/services/review_service.py`
- `backend/app/schemas/review.py`
- `backend/app/api/v1/review.py`
- `backend/tests/test_review_service.py`
- `backend/tests/test_review_api.py`
- `frontend/src/components/graph/KnowledgeGraph.vue`
- `frontend/src/views/ReviewPage.vue`
- `frontend/src/views/ReviewPage.spec.ts`

### Data and Calculation Guardrails

- Canonical source table for mastery is `question_history`.
- Chapter grouping key is `knowledge_nodes.parent_id` (cluster owner).
- Suggested formula per cluster:
  - `attempted_count = count(valid answers in cluster)`
  - `correct_count = count(valid answers with is_correct = 1 in cluster)`
  - `mastery_score = correct_count / attempted_count` (0 when attempted_count = 0)
- Exclude any row where `is_invalidated = 1`.

### Testing Standards Summary

- Assert aggregation math explicitly with fixed fixtures; avoid brittle snapshot-only checks.
- Validate no regression to Story 3.1 wrong-answer grouping contracts.
- Frontend tests should verify both visual state mapping (color classes/style) and behavior continuity (selection/retry).

## Developer Context

### Project Structure Notes

- Existing review domain is already established in Story 3.1 with API, schema, service, and tests.
- Existing graph rendering is centralized in `KnowledgeGraph.vue`; this is the primary integration point for mastery color semantics.
- Keep Story 3.2 focused on read-model calculation and visualization; invalidation write-flow belongs to Story 3.3.

### Previous Story Intelligence

- Story 3.1 already persists answer history and established filtered review queries with `is_invalidated` guard.
- Story 3.1 established frontend review UX and retry entrypoint; Story 3.2 should augment, not replace, this flow.
- Review findings from Story 3.1 emphasized stable identifiers and avoiding hidden persistence failures; keep observability and deterministic IDs in mind for mastery payload joins.

### Git Intelligence Summary

Recent commits indicate active work around review notebook persistence and frontend review integration:
- `a986a58` introduced notebook database/service layer foundations.
- `58f913f` added frontend review component.

Mastery implementation should reuse these patterns and avoid duplicating data pathways.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3: 净水池掌握度追踪 (Clean Mastery Tracking & Wrong-Answer Review)]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: 结构化掌握度评估 (Structured Mastery Calculation)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Pattern Categories Defined]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Formats]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/implementation-artifacts/3-1-knowledge-point-wrong-answer-notebook.md]

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- Story created from explicit user request: `3-2-structured-mastery-calculation`
- Sprint status transition executed: `ready-for-dev` -> `in-progress` -> `review`
- Implemented chapter mastery aggregation in review service with `is_invalidated = 0` guard
- Added `GET /api/v1/review/chapter-mastery` endpoint and response schemas
- Integrated chapter mastery load into document graph and review page
- Added mastery color band helper and frontend mastery tests
- Validated with full backend pytest and frontend test/build

### Completion Notes List

- AC-1 satisfied: chapter mastery is computed per `parent_id` cluster with deterministic payload (`attempted_count`, `correct_count`, `mastery_score`), excluding invalidated records.
- AC-1 satisfied: mastery endpoint returns standard envelope (`status`, `data`, `message`, `trace_id`) with strict schema validation.
- AC-2 satisfied: AntV G6 nodes now apply mastery color bands via chapter cluster mapping while preserving existing selection cascade behavior.
- AC-2 satisfied: Review page now surfaces a chapter mastery snapshot and shows fallback text when mastery data is unavailable.
- Tests passed: backend full suite `134 passed`; frontend tests `9 passed`; frontend build succeeded.
- ✅ Resolved review finding [HIGH]: mastery fetch now fails independently and no longer blocks wrong-answer notebook rendering.
- ✅ Resolved review finding [HIGH]: document view now degrades gracefully when chapter mastery API errors.
- ✅ Resolved review finding [MEDIUM]: overall mastery now reflects backend aggregate summary semantics.
- ✅ Resolved review finding [MEDIUM]: added explicit all-correct mastery edge-case backend test.

### File List

- _bmad-output/implementation-artifacts/3-2-structured-mastery-calculation.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/services/review_service.py
- backend/app/schemas/review.py
- backend/app/api/v1/review.py
- backend/tests/test_review_service.py
- backend/tests/test_review_api.py
- frontend/src/api/review.ts
- frontend/src/components/graph/mastery.ts
- frontend/src/components/graph/mastery.spec.ts
- frontend/src/components/graph/KnowledgeGraph.vue
- frontend/src/views/DocumentView.vue
- frontend/src/views/ReviewPage.vue
- frontend/src/views/ReviewPage.spec.ts

## Change Log

- 2026-04-06: Created Story 3.2 context file and marked sprint status as ready-for-dev.
- 2026-04-06: Implemented Story 3.2 (backend mastery aggregation/API, graph color integration, review mastery snapshot, and automated tests); story moved to review.
- 2026-04-06: Addressed code review findings (4 patch items resolved) and revalidated backend/frontend test gates.
