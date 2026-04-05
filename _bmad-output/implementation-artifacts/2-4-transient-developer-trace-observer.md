# Story 2.4: Transient Developer Trace Observer

Status: done

## Story

As a Technical Interviewer,
I want to see the behind-the-scenes decision logic of the agents without burning server memory,
so that I can verify the complexity of the LangGraph state machine without violating 2C2G constraints.

## Acceptance Criteria

1. **Given** the AI is processing an answer
   **When** the graph transitions between nodes
   **Then** the backend must emit `type: trace` SSE pulses containing only the current node name and lightweight metadata, without persisting bulky trace blobs in long-lived backend storage

2. **Given** trace pulses are received by the browser
   **When** the Vue 3 quiz screen renders the stream
   **Then** the frontend must accumulate the pulses in a local reactive trace array and render a readable trace log for the current session only

## Tasks / Subtasks

- [x] Task 1: Tighten backend trace pulse projection (AC: #1)
  - [x] Add a small helper in `backend/app/api/v1/chat.py` that projects trace entries down to `node_name` and `metadata`
  - [x] Keep SSE trace events lightweight and skip any non-dict or non-essential payload fields
  - [x] Preserve existing `content` and `error` event behavior while keeping trace emission transient

- [x] Task 2: Normalize trace pulses in the Vue store and UI (AC: #2)
  - [x] Update `frontend/src/stores/quiz.ts` to store trace pulses as a local reactive array of `{ node_name, metadata }` entries
  - [x] Render the trace log in `frontend/src/views/QuizView.vue` as a readable list instead of a raw serialized blob
  - [x] Reset the local trace buffer on new quiz sessions and answer submissions

- [x] Task 3: Add regression tests for transient trace handling (AC: #1, #2)
  - [x] Extend `backend/tests/test_chat_sse.py` to assert trace SSE payloads contain the projected lightweight fields
  - [x] Extend `frontend/src/views/QuizView.spec.ts` to verify trace entries render from the local store state
  - [x] Keep existing escape-hatch and SSE coverage intact

## Dev Notes

### Relevant Architecture Patterns and Constraints

- SSE remains the transport for trace pulses; do not introduce a separate polling channel.
- Trace data should stay ephemeral and bounded; avoid loading or storing large trace payloads in the browser or backend.
- Keep `snake_case` field names in backend JSON and project only the data the UI needs.

### Source Tree Components to Touch

- `backend/app/api/v1/chat.py`
- `frontend/src/stores/quiz.ts`
- `frontend/src/views/QuizView.vue`
- `frontend/src/views/QuizView.spec.ts`
- `backend/tests/test_chat_sse.py`

### Testing Standards Summary

- Backend trace tests should validate SSE event shape, not internal implementation details.
- Frontend tests should verify local accumulation and rendering of trace entries.
- Preserve existing streaming and guardrail regression coverage.

## Developer Context

### Project Structure Notes

- Story 2.2 already established the SSE parser and trace log display path.
- Story 2.3 added guardrail and escape hatch flows; do not regress those event fields.
- Keep the trace observer transient and session-scoped; it is an observability aid, not durable learning data.

### Previous Story Intelligence

- The current quiz flow already emits `type: trace` events and stores them in the frontend store.
- The remaining work is to make the payload projection explicit and the trace rendering more intentional.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4: 瞬时推送的追溯透明窗 (Transient Developer Trace Observer)]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/implementation-artifacts/2-3-context-guardrails-escape-hatch.md]

## Dev Agent Record

### Agent Model Used

GPT-5.4 mini

### Debug Log References

- Story created from sprint backlog entry `2-4-transient-developer-trace-observer`

### Completion Notes List

- Backend trace SSE emits lightweight `node_name` + `metadata` pulses and skips non-dict payloads.
- Frontend normalizes trace pulses into a local reactive array and renders a readable session-only trace log.
- Added backend and frontend regression coverage for the transient trace observer path.
- Verified with full backend pytest and frontend build/test runs.
- Resolved review follow-ups by switching answer feedback to incremental graph streaming, restoring `socratic_hint` trace emission, and hardening malformed trace payload handling in the Vue store.
- Code review completed with no remaining blockers; approved for done state.

## File List

- _bmad-output/implementation-artifacts/2-4-transient-developer-trace-observer.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/api/v1/chat.py
- backend/tests/test_chat_sse.py
- backend/app/graph/nodes/hint.py
- frontend/src/stores/quiz.ts
- frontend/src/views/QuizView.spec.ts
- frontend/src/views/QuizView.vue

## Change Log

- 2026-04-05: Implemented transient trace projection, normalized frontend trace accumulation, and added regression tests.
- 2026-04-05: Resolved code review findings by making trace emission incremental, restoring hint-node trace metadata, and hardening malformed-event handling.
- 2026-04-05: Completed story review and marked Story 2.4 as done.