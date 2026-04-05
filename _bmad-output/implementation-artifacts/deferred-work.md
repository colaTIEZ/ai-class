## Deferred from: code review of 1-5-epic1-hotfix-zombie-tasks-security (2026-04-1)

- Test DB isolation still uses shared default SQLite path in `backend/tests/conftest.py`; pre-existing test architecture issue and not introduced by this hotfix.

## Deferred from: code review of 2-2-langgraph-routing-socratic-sse-stream (2026-04-04)

- `backend/app/api/v1/chat.py:202`: `content` 事件的 `hint_type` 仍使用固定值，可能与 tutor 实际输出不一致；该问题为本次改动前已有行为，暂不在本轮修复。
- `backend/app/api/v1/chat.py:156`: async SSE 生成器内同步执行 answer-feedback 图调用，在高并发下可能阻塞事件循环；属于既有架构风险，建议后续专项优化。

## Deferred from: code review of 2-2-langgraph-routing-socratic-sse-stream (2026-04-04, second review)

- **Token budget inconsistency suggests missing requirements**: MAX_ANSWER_TOKENS reduced from 300→200, MAX_QUESTION_TOKENS=300, MAX_HINT_TOKENS=600, MAX_REASONING_TOKENS=400. No explanation for why hints get 3× answer budget. Arbitrary limits without documented rationale suggest spec clarification needed.
- **Settings.openai_api_key read with side effects during property access**: Tests modify settings.openai_api_key directly but embedding_ready property reads it. Architectural test pattern issue requiring global fixture refactor.
- **SSE Generator Blocks Event Loop**: The team acknowledges the SSE generator synchronously executes graph calls, which may block the event loop under high concurrency. Deferred as specialized optimization area (already documented in prior review).
- **Hardcoded Hint Type Not Aligned with Tutor Output**: AC3 requires hints to be based on error_type. The deferred work log explicitly documents that hint_type is hardcoded and not synchronized with tutor output (already documented in prior review).
- **Missing Evidence: Conversation History Limit (20 messages)**: Explicit requirement to limit history to 20 messages. The diff does not address conversation_history management. This task item may be out of scope for this change.
- **Missing Evidence: Trace Log Accumulation Prevention**: Trace logs must not accumulate in memory. Architectural issue requiring write-to-DB or streaming mechanism.
- **Missing Evidence: LLM Response Streaming**: LLM outputs must stream. Cannot verify from diff whether LLM responses are streamed. Out of scope for token budget enforcement work.

## Deferred from: code review of 3-1-knowledge-point-wrong-answer-notebook (2026-04-05)

- 基于 `X-User-ID` 的客户端可控身份方案存在越权风险（`backend/app/api/v1/review.py:37`）；该方案与当前 MVP 无鉴权约束一致，判定为既有架构决策，后续在认证体系落地时统一治理。
