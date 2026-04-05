-- Story 3.1 migration: wrong-answer notebook tables

CREATE TABLE IF NOT EXISTS quiz_attempts (
    attempt_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    document_id INTEGER,
    selected_node_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at TEXT,
    session_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS question_history (
    question_record_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    question_id TEXT,
    node_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL DEFAULT 'multiple_choice',
    user_answer TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    error_type TEXT NOT NULL,
    error_severity INTEGER NOT NULL DEFAULT 1,
    attempted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    is_invalidated INTEGER NOT NULL DEFAULT 0,
    invalidation_reason TEXT,
    FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(attempt_id),
    FOREIGN KEY (node_id) REFERENCES knowledge_nodes(node_id)
);

CREATE INDEX IF NOT EXISTS idx_question_history_user_node_validity
    ON question_history(user_id, node_id, is_correct, is_invalidated, attempted_at DESC);

CREATE INDEX IF NOT EXISTS idx_question_history_attempt
    ON question_history(attempt_id, attempted_at DESC);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_session
    ON quiz_attempts(user_id, session_id);
