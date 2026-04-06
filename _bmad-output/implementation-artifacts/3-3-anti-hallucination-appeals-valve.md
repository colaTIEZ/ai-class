# Story 3.3: 防幻觉数据净化阀 (Anti-Hallucination Appeals Valve)

Status: done

## Story

As a Student,
I want to report if the AI made a mistake or hallucinated a question/answer,
so that the system's mistake doesn't ruin my mastery statistics.

## Acceptance Criteria

1. **Given** the user is viewing a guided answer or question review
   **When** the user clicks a discrete "Report AI Error/Hallucination" button
   **Then** the specific question record is flagged as `invalidated` in SQLite.

2. **Given** a record has been invalidated
   **When** the system renders Wrong-Answer Notebook and computes Mastery
   **Then** that record is strictly excluded from all future notebook displays and mastery calculations.

## Tasks / Subtasks

- [x] Task 1: Add invalidation write-path in backend service and schema (AC: #1)
  - [x] Add a dedicated service function in `backend/app/services/review_service.py` to mark one `question_record_id` as invalidated for the current user.
  - [x] Persist `is_invalidated = 1`, `invalidation_reason`, and an ISO 8601 timestamp field (new column if needed) in `question_history`.
  - [x] Ensure idempotent behavior: reporting an already-invalidated record returns success without side effects.

- [x] Task 2: Expose invalidation API endpoint (AC: #1)
  - [x] Add `POST /api/v1/review/invalidate` in `backend/app/api/v1/review.py` with standard envelope `{status, data, message, trace_id}`.
  - [x] Validate payload via strict Pydantic models in `backend/app/schemas/review.py` (`question_record_id`, optional `reason`).
  - [x] Enforce user scoping (`X-User-ID`): user can invalidate only their own records.

- [x] Task 3: Integrate frontend report action in review UI (AC: #1)
  - [x] Add API client method in `frontend/src/api/review.ts` for invalidation endpoint.
  - [x] In `frontend/src/views/ReviewPage.vue`, add per-question action button "Report AI Error/Hallucination".
  - [x] On success, optimistically remove invalidated question from current UI group and refresh summary counters.

- [x] Task 4: Guarantee downstream exclusion consistency (AC: #2)
  - [x] Verify wrong-answer query path (`get_wrong_answers_by_node`) still excludes invalidated records after new write-path.
  - [x] Verify mastery path (`get_chapter_mastery`) still excludes invalidated records under all edge cases (single-record cluster, all-invalidated cluster).
  - [x] Add/confirm deterministic fallback behavior in frontend when invalidation leaves an empty node group.

- [x] Task 5: Add comprehensive automated tests (AC: #1, #2)
  - [x] Backend service tests: successful invalidation, idempotent re-report, user-scope denial.
  - [x] Backend API tests: 400 for missing header, 404/403 for invalid ownership, 200 envelope on success.
  - [x] Frontend tests: report button visibility, API call wiring, immediate UI pruning after success, no regression of retry flow.

### Review Findings

- [x] [Review][Patch] Concurrent invalidation race can violate idempotent semantics [backend/app/services/review_service.py:420]
- [x] [Review][Patch] Whitespace `question_record_id` is coerced into 404 instead of input validation error [backend/app/api/v1/review.py:114]
- [x] [Review][Patch] Mastery snapshot is not refreshed after successful invalidation (AC-2 display consistency) [frontend/src/views/ReviewPage.vue:62]
- [x] [Review][Patch] Invalidation failure path is silently swallowed in UI with no user feedback [frontend/src/views/ReviewPage.vue:98]
- [x] [Review][Patch] Missing tests for concurrent invalidation and post-invalidation mastery refresh behavior [backend/tests/test_review_service.py:13]
- [x] [Review][Defer] Client-controlled `X-User-ID` identity remains spoofable without server-side auth [backend/app/api/v1/review.py:46] — deferred, pre-existing

## Dev Notes

### Technical Requirements

- Reuse existing review domain primitives before creating new abstractions:
  - `backend/app/services/review_service.py`
  - `backend/app/api/v1/review.py`
  - `backend/app/schemas/review.py`
  - `frontend/src/api/review.ts`
  - `frontend/src/views/ReviewPage.vue`
- Keep all backend/API keys in `snake_case`.
- Preserve standard response envelope (`status`, `data`, `message`, `trace_id`).
- Timestamps must be ISO 8601 UTC strings.

### Architecture Compliance

- Keep FastAPI routes thin; business logic stays in service layer.
- Maintain SQLite single-store strategy; do not introduce a new datastore for invalidation.
- Preserve 2C2G constraints: avoid heavy joins in write-path and avoid unnecessary full-table scans.

### Library & Framework Requirements

- Backend: FastAPI + Pydantic schema validation (existing stack).
- Data layer: SQLite table `question_history` with existing `is_invalidated` flag.
- Frontend: Vue 3 composition API and existing fetch-based API layer in `frontend/src/api/review.ts`.

### File Structure Requirements

- Backend write/read logic stays in `backend/app/services/review_service.py`.
- Endpoint wiring stays in `backend/app/api/v1/review.py`.
- DTO/request/response models stay in `backend/app/schemas/review.py`.
- Review UI action stays in `frontend/src/views/ReviewPage.vue`.

### Testing Requirements

- Extend `backend/tests/test_review_service.py` for invalidation mutation semantics.
- Extend `backend/tests/test_review_api.py` for endpoint contract and ownership checks.
- Add/update frontend tests adjacent to review UI specs to verify report action and pruning behavior.
- Run full backend and frontend test suites before moving status beyond `ready-for-dev`.

## Previous Story Intelligence (from 3.2)

- Story 3.2 already hardened exclusion semantics (`is_invalidated = 0`) in both wrong-answer and mastery read paths.
- Story 3.2 added graceful degradation when mastery API fails; keep this behavior unchanged after adding report flow.
- Existing review findings emphasized correctness over UI convenience; do not compromise envelope or scoping for fast delivery.

## Git Intelligence Summary

Recent commits (`62c28e4`, `6f3465b`, `58f913f`) show the review domain is active and stable in current file paths. Implement Story 3.3 by extending those exact modules, not by introducing parallel review stacks.

## Latest Tech Information

No stack upgrade is required for this story. Keep current project-locked versions and focus on safe mutation semantics plus strict read-side exclusion.

## Project Context Reference

No `project-context.md` file was found in workspace discovery. Use architecture and epics artifacts as the source of truth.

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3: 防幻觉数据净化阀 (Anti-Hallucination Appeals Valve)]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3: 净水池掌握度追踪 (Clean Mastery Tracking & Wrong-Answer Review)]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Formats]
- [Source: _bmad-output/planning-artifacts/architecture.md#Pattern Categories Defined]
- [Source: _bmad-output/implementation-artifacts/3-2-structured-mastery-calculation.md]
- [Source: backend/app/services/review_service.py]
- [Source: backend/app/api/v1/review.py]
- [Source: backend/app/schemas/review.py]
- [Source: frontend/src/views/ReviewPage.vue]

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- create-story target auto-discovered from sprint-status backlog: `3-3-anti-hallucination-appeals-valve`
- artifact analysis completed: epics, architecture, prd, previous story, recent commits
- RED: `pytest backend/tests/test_review_service.py -k invalidate_question_record -q` failed (missing symbol import)
- GREEN: `pytest backend/tests/test_review_service.py -k invalidate_question_record -q` passed (2 passed)
- RED: `pytest backend/tests/test_review_api.py -k invalidate -q` failed (endpoint absent)
- GREEN: `pytest backend/tests/test_review_api.py -k invalidate -q` passed (4 passed)
- RED: `npm run test -- src/views/ReviewPage.spec.ts` failed (report button absent)
- GREEN: `npm run test -- src/views/ReviewPage.spec.ts` passed (5 passed)
- Regression: `pytest backend/tests -q` passed (142 passed)
- Regression: `npm run test` passed (11 passed)
- Quality: `npm run build` passed (vite chunk size warning only)

### Completion Notes List

- Implemented backend invalidation mutation `invalidate_question_record` with user scoping and idempotent semantics.
- Added SQLite compatibility migration for `question_history.invalidated_at` and persisted ISO 8601 invalidation timestamps.
- Added `POST /api/v1/review/invalidate` with strict request schema and standard envelope.
- Added frontend API client `invalidateQuestionRecord` and ReviewPage action button `Report AI Error/Hallucination`.
- Added optimistic UI pruning after invalidation and deterministic fallback to empty-state when a node is fully pruned.
- Verified AC-2 consistency through service-layer tests covering all-invalidated scenarios for both wrong-answer and mastery views.
- Full regression suite passed: backend `142 passed`, frontend `11 passed`, build successful.
- ✅ Resolved review finding [HIGH]: invalidation write-path now guards update with `is_invalidated = 0` and race-safe post-check for strict idempotency.
- ✅ Resolved review finding [MEDIUM]: blank `question_record_id` now returns 400 with explicit validation message.
- ✅ Resolved review finding [MEDIUM]: mastery snapshot now refreshes after successful invalidation, keeping AC-2 UI consistency.
- ✅ Resolved review finding [LOW]: invalidation failures now show user-visible feedback instead of silent swallow.
- ✅ Resolved review finding [LOW]: added tests for concurrent invalidation behavior and post-invalidation mastery refresh/feedback.
- Review-fix regression passed: backend `144 passed`, frontend `13 passed`, build successful.

### File List

- _bmad-output/implementation-artifacts/3-3-anti-hallucination-appeals-valve.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/services/review_service.py
- backend/app/schemas/review.py
- backend/app/api/v1/review.py
- backend/tests/test_review_service.py
- backend/tests/test_review_api.py
- frontend/src/api/review.ts
- frontend/src/views/ReviewPage.vue
- frontend/src/views/ReviewPage.spec.ts
- _bmad-output/implementation-artifacts/deferred-work.md

## Change Log

- 2026-04-06: Implemented Story 3.3 end-to-end (backend invalidation mutation + API, frontend report action and pruning UX), added automated tests, and passed full regression suite; status moved to review.
- 2026-04-06: Applied code-review patch findings in batch mode and revalidated full regression; story moved to done.
