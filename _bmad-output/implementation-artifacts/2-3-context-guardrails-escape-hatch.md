# Story 2.3: Context Guardrails & Escape Hatch

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Student facing a difficult question,
I want the system to detect if I'm stuck or frustrated and offer explicit ways out,
so that I don't get trapped in an endless AI loop or waste server tokens.

## Acceptance Criteria

1. **Given** a user is stuck in a Socratic interaction loop
   **When** the user expresses negative sentiment ("I don't know", "too hard") OR the semantic similarity of their last 3 answers indicates stagnation, OR the `turn_count` > 5
   **Then** the UI explicitly displays an "Escape Hatch" (Show Answer / Skip Question) and the Tutor switches from pure Socratic to "Semi-transparent Mode" (hints become direct)

2. **Given** the user is in a stuck loop
   **When** the user chooses Skip
   **Then** the node is flagged for Epic 3 as `Needs Review`

3. **Given** repeated Socratic turns are accumulating
   **When** guardrail conditions are met
   **Then** a pruning node in LangGraph summarizes context and drops raw historical messages to reduce token/memory pressure.

## Tasks / Subtasks

- [x] Task 1: Extend state contract for guardrails and intervention controls (AC: #1, #2, #3)
  - [x] Add `turn_count`, `stagnation_score`, and `frustration_signals` fields to `backend/app/graph/state.py`
  - [x] Add `guardrail_triggered`, `escape_hatch_visible`, and `tutor_mode` (`socratic` | `semi_transparent`) fields
  - [x] Add `needs_review_node_ids` and `review_reason` fields for Epic 3 handoff
  - [x] Add `context_summary` and `pruned_message_count` fields for pruning metadata

- [x] Task 2: Implement guardrail detector node (AC: #1, #3)
  - [x] Create `backend/app/graph/nodes/guardrails.py` with `evaluate_guardrails_node(state: SocraticState)`
  - [x] Detect frustration with lexical cues ("i don't know", "too hard", "skip", "stuck") and language-normalized variants
  - [x] Compute answer stagnation over last 3 answers using semantic similarity service; use deterministic fallback if similarity service unavailable
  - [x] Trigger guardrail if frustration OR stagnation threshold met OR `turn_count` > 5
  - [x] Append structured metadata to `trace_log` including trigger reason(s), turn count, and threshold values

- [x] Task 3: Implement context pruning node (AC: #3)
  - [x] Create `backend/app/graph/nodes/prune.py` with `prune_context_node(state: SocraticState)`
  - [x] Summarize conversation history into bounded `context_summary` (token-capped)
  - [x] Replace raw historical messages with compact summary and retain only the latest N interaction turns
  - [x] Preserve correctness-critical fields (`current_question`, `validation_result`, `current_hint`) during pruning
  - [x] Record `pruned_message_count` and `summary_token_count` in trace metadata

- [x] Task 4: Implement escape hatch API contract and orchestration routing (AC: #1, #2)
  - [x] Update `backend/app/schemas/quiz.py` (or dedicated schema) with explicit action payload: `continue | show_answer | skip`
  - [x] Update `backend/app/api/v1/chat.py` to accept escape hatch action while preserving existing SSE envelope
  - [x] Extend `backend/app/graph/orchestrator.py` routing: `validate -> guardrails -> prune -> hint/end`
  - [x] Add routing branch for `show_answer` to emit direct explanation response with trace event
  - [x] Add routing branch for `skip` to set `Needs Review` marker and end current question flow safely

- [x] Task 5: Implement Semi-transparent tutor mode behavior (AC: #1)
  - [x] Update `backend/app/graph/nodes/hint.py` to switch prompt strategy by `tutor_mode`
  - [x] Keep pure Socratic behavior when guardrail inactive
  - [x] Produce direct but concise hints (without full answer leakage unless `show_answer`) in `semi_transparent` mode
  - [x] Emit mode-switch metadata in trace payload for frontend observer

- [x] Task 6: Frontend Escape Hatch UI and SSE state integration (AC: #1, #2)
  - [x] Update `frontend/src/stores/quiz.ts` with `escapeHatchVisible`, `guardrailReason`, `tutorMode`, and `needsReviewQueued`
  - [x] Update `frontend/src/api/quiz.ts` to send escape actions and parse new SSE content/trace payload fields
  - [x] Update `frontend/src/views/QuizView.vue` to render `Show Answer` and `Skip Question` actions conditionally
  - [x] Ensure UI transitions are deterministic across reconnects using `thread_id` checkpoint state

- [x] Task 7: Persist Epic 3 review flags in storage layer (AC: #2)
  - [x] Extend review/wrong-answer persistence flow so skipped questions are tagged `needs_review=true`
  - [x] Persist `review_reason` and `node_id` linkage for downstream notebook/mastery filtering
  - [x] Ensure this flag is excluded from mastery score until student revisits (Epic 3 compatibility)

- [x] Task 8: Comprehensive tests for guardrails, pruning, and escape hatch flow (AC: #1, #2, #3)
  - [x] Add `backend/tests/graph/nodes/test_guardrails.py` (frustration, stagnation, turn-count trigger matrix)
  - [x] Add `backend/tests/graph/nodes/test_prune.py` (summary fidelity, token cap, field preservation)
  - [x] Extend `backend/tests/graph/test_orchestrator.py` for new routing branches and deterministic outcomes
  - [x] Extend `backend/tests/api/v1/test_chat.py` for `show_answer`/`skip` action handling and SSE event validation
  - [x] Add frontend tests for escape hatch rendering and action dispatch in guardrail conditions
  - [x] Validate memory-oriented assertions remain bounded under repeated interactions

## Dev Notes

### Relevant Architecture Patterns and Constraints

- Keep node-level single responsibility: each graph node mutates only its owned state keys.
- Maintain standardized SSE event envelope with `type`, `data`, `trace_id`, `timestamp`.
- Preserve 2C2G memory discipline: summarize and prune aggressively when guardrails trigger.
- Continue `snake_case` contracts end-to-end between backend JSON and frontend state.

### Source Tree Components to Touch

- `backend/app/graph/state.py`
- `backend/app/graph/orchestrator.py`
- `backend/app/graph/nodes/guardrails.py` (new)
- `backend/app/graph/nodes/prune.py` (new)
- `backend/app/graph/nodes/hint.py`
- `backend/app/api/v1/chat.py`
- `backend/app/schemas/quiz.py` (or a dedicated escape-hatch schema)
- `backend/app/services/vector_store.py` (only if semantic similarity helper is added here)
- `frontend/src/api/quiz.ts`
- `frontend/src/stores/quiz.ts`
- `frontend/src/views/QuizView.vue`

### Testing Standards Summary

- Minimum 80% coverage across new/changed graph nodes.
- Unit tests must cover all guardrail triggers and non-trigger controls.
- Integration tests must verify full path: incorrect answer -> guardrail trigger -> prune -> semi-transparent hint.
- API tests must verify skip/show-answer actions preserve stream protocol compatibility.
- Frontend tests must verify Escape Hatch visibility and action idempotency under reconnect.

## Developer Context

### Project Structure Notes

- Follow existing graph decomposition pattern under `backend/app/graph/nodes/`.
- Keep orchestrator lean; put business logic in nodes/services.
- Reuse existing chat/SSE endpoint and avoid introducing parallel chat endpoints.

### Previous Story Intelligence

- Story 2.2 already introduced validator/tutor routing and SSE envelopes. Extend, do not replace, this flow.
- Story 2.2 review patches identified fragile routing and state type mismatches. Preserve explicit boolean/type checks; avoid loose coercion.
- Token-budget constants and truncation warnings were recently hardened in validation/hint nodes; guardrail and prune logic must honor the same budgeting discipline.
- Current trace observer is transient-by-design; do not persist verbose trace payloads server-side.

### Git Intelligence Summary

- Recent commits (`Strengthen verification nodes`, `Implement frontend SSE integration`, `Implement SSE streaming endpoint and update graph for new node`) confirm this epic is mid-flight and patterns are established.
- New work should be incremental over existing node architecture and SSE parser contracts to avoid regression churn.

### Library & Framework Requirements

- Backend: FastAPI, LangGraph, langchain-openai, Pydantic, SQLite Checkpointer
- Frontend: Vue 3, Pinia, existing streaming parser in `frontend/src/api/quiz.ts`
- Reuse existing retry and JSON parsing helpers under `backend/app/graph/nodes/llm_runtime.py`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3: 上下文防爆护栏：记忆修剪与逃生舱 (Context Guardrails & Escape Hatch)]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/prd.md#7. Functional Requirements (The Capability Contract)]
- [Source: _bmad-output/implementation-artifacts/2-2-langgraph-routing-socratic-sse-stream.md]

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- dev-story workflow execution: selected story `2-3-context-guardrails-escape-hatch`
- sprint-status transition update: `2-3-context-guardrails-escape-hatch` -> `in-progress`
- Targeted regression command: `python -m pytest backend/tests/test_guardrails_node.py backend/tests/test_prune_node.py backend/tests/test_orchestrator_guardrails.py backend/tests/test_chat_sse.py backend/tests/test_validate_hint_nodes.py` (20 passed)
- Full backend regression command: `python -m pytest backend/tests` (117 passed)
- Frontend component test command: `vitest run src/views/QuizView.spec.ts` (2 passed)
- Frontend build command: `npm run build` (passed)

### Completion Notes List

- Implemented guardrail detection node with frustration/stagnation/turn-limit triggers and trace metadata.
- Implemented context pruning node with bounded summary generation and retained recent conversation window.
- Implemented escape action handling (`continue|show_answer|skip`) with direct-answer and skip-to-review flows.
- Extended answer-feedback graph routing to `validate -> guardrails -> prune/escape -> hint/end`.
- Extended SSE payload to include guardrail/tutor/review indicators for frontend UI.
- Added persistence for skip review flags via `question_review_flags` table and storage helper.
- Added backend tests for guardrails, prune, orchestrator routing, and skip/show-answer SSE branches.
- No known blockers remain for this story.

### File List

- _bmad-output/implementation-artifacts/2-3-context-guardrails-escape-hatch.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/graph/state.py
- backend/app/graph/orchestrator.py
- backend/app/graph/nodes/guardrails.py
- backend/app/graph/nodes/prune.py
- backend/app/graph/nodes/escape.py
- backend/app/graph/nodes/hint.py
- backend/app/graph/prompts/tutor_prompts.py
- backend/app/api/v1/chat.py
- backend/app/schemas/quiz.py
- backend/app/services/vector_store.py
- backend/app/api/v1/documents.py
- backend/tests/test_guardrails_node.py
- backend/tests/test_prune_node.py
- backend/tests/test_orchestrator_guardrails.py
- backend/tests/test_chat_sse.py
- frontend/package.json
- frontend/package-lock.json
- frontend/src/api/quiz.ts
- frontend/src/stores/quiz.ts
- frontend/src/views/QuizView.spec.ts
- frontend/src/views/QuizView.vue
- frontend/vitest.config.ts

## Change Log

- 2026-04-05: Implemented Story 2.3 core backend/frontend functionality (guardrails, pruning, escape hatch, review-flag persistence), added backend regression tests, added frontend vitest coverage, and validated full backend regression.