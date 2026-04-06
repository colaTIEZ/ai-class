"""Wrong-answer notebook persistence and query helpers."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Optional

from app.schemas.review import (
    ChapterMasteryData,
    ChapterMasteryItem,
    ChapterMasterySummary,
    InvalidateQuestionData,
    WrongAnswerNodeGroup,
    WrongAnswerQuestion,
    WrongAnswersData,
    WrongAnswersSummary,
)
from app.services.vector_store import get_connection

logger = logging.getLogger(__name__)

_REVIEW_TABLES_READY: set[str] = set()
_REVIEW_TABLES_LOCK = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def init_review_tables(conn: sqlite3.Connection) -> None:
    """Create review tables and indexes if they do not exist."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            attempt_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            document_id INTEGER,
            selected_node_ids TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            completed_at TEXT,
            session_id TEXT UNIQUE
        );
        """
    )

    conn.execute(
        """
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
            invalidated_at TEXT,
            FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(attempt_id),
            FOREIGN KEY (node_id) REFERENCES knowledge_nodes(node_id)
        );
        """
    )

    _ensure_column(
        conn,
        table_name="question_history",
        column_name="invalidated_at",
        column_type="TEXT",
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_question_history_user_node_validity
        ON question_history(user_id, node_id, is_correct, is_invalidated, attempted_at DESC);
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_question_history_attempt
        ON question_history(attempt_id, attempted_at DESC);
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_session
        ON quiz_attempts(user_id, session_id);
        """
    )


def _connection_identity(conn: sqlite3.Connection) -> str:
    """Build a stable identity for one SQLite database target."""

    try:
        row = conn.execute("PRAGMA database_list;").fetchone()
        if row is not None and len(row) >= 3 and row[2]:
            return str(row[2])
    except Exception:  # pragma: no cover - defensive fallback
        pass
    return f"conn:{id(conn)}"


def _ensure_column(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    column_name: str,
    column_type: str,
) -> None:
    """Add a column to an existing SQLite table if it does not exist."""

    table_info = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
    columns = {str(row[1]) for row in table_info}
    if column_name in columns:
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def ensure_review_tables_ready(conn: sqlite3.Connection) -> None:
    """Initialize review tables once per DB target to avoid repeated runtime DDL."""

    identity = _connection_identity(conn)
    if identity in _REVIEW_TABLES_READY:
        return
    with _REVIEW_TABLES_LOCK:
        if identity in _REVIEW_TABLES_READY:
            return
        init_review_tables(conn)
        _REVIEW_TABLES_READY.add(identity)


def record_answer(
    *,
    user_id: str,
    node_id: str,
    question_text: str,
    user_answer: str,
    correct_answer: str,
    is_correct: bool,
    error_type: str,
    error_severity: int = 1,
    question_type: str = "multiple_choice",
    question_id: Optional[str] = None,
    attempt_id: Optional[str] = None,
    selected_node_ids: Optional[list[str]] = None,
    invalidation_reason: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> str:
    """Persist one answer attempt and return the generated record ID."""

    own_connection = conn is None
    connection = conn or get_connection()
    try:
        ensure_review_tables_ready(connection)
        question_record_id = str(uuid.uuid4())
        resolved_attempt_id = attempt_id or question_record_id
        resolved_question_id = question_id or question_record_id
        selected_nodes_json = json.dumps(selected_node_ids or [node_id], ensure_ascii=False)

        connection.execute(
            """
            INSERT INTO quiz_attempts (
                attempt_id, user_id, selected_node_ids, session_id, completed_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(attempt_id) DO UPDATE SET
                user_id = excluded.user_id,
                selected_node_ids = excluded.selected_node_ids,
                session_id = excluded.session_id,
                completed_at = excluded.completed_at
            """,
            (
                resolved_attempt_id,
                user_id,
                selected_nodes_json,
                resolved_attempt_id,
                _utc_now_iso(),
            ),
        )

        connection.execute(
            """
            INSERT INTO question_history (
                question_record_id,
                attempt_id,
                user_id,
                question_id,
                node_id,
                question_text,
                question_type,
                user_answer,
                correct_answer,
                is_correct,
                error_type,
                error_severity,
                attempted_at,
                is_invalidated,
                invalidation_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question_record_id,
                resolved_attempt_id,
                user_id,
                resolved_question_id,
                node_id,
                question_text,
                question_type,
                user_answer,
                correct_answer,
                1 if is_correct else 0,
                error_type,
                error_severity,
                _utc_now_iso(),
                0,
                invalidation_reason,
            ),
        )
        connection.commit()
        return question_record_id
    finally:
        if own_connection:
            connection.close()


def get_wrong_answers_by_node(
    *,
    user_id: str,
    node_id_filter: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> WrongAnswersData:
    """Return grouped wrong answers for a user, excluding invalidated records."""

    own_connection = conn is None
    connection = conn or get_connection()
    try:
        ensure_review_tables_ready(connection)
        params: list[str] = [user_id]
        query = [
            """
            SELECT
                qh.question_record_id,
                qh.question_id,
                qh.node_id,
                COALESCE(kn.label, qh.node_id) AS node_label,
                qh.question_text,
                qh.user_answer,
                qh.correct_answer,
                qh.error_type,
                qh.error_severity,
                qh.question_type,
                qh.attempted_at,
                qh.is_invalidated
            FROM question_history qh
            LEFT JOIN knowledge_nodes kn ON kn.node_id = qh.node_id
            WHERE qh.user_id = ?
              AND qh.is_correct = 0
              AND qh.is_invalidated = 0
            """,
        ]
        if node_id_filter:
            query.append("AND qh.node_id = ?")
            params.append(node_id_filter)
        query.append("ORDER BY qh.node_id ASC, qh.attempted_at DESC, qh.question_record_id DESC")

        rows = connection.execute("\n".join(query), params).fetchall()

        grouped: dict[str, dict[str, object]] = {}
        for row in rows:
            node_id = str(row[2])
            node_group = grouped.setdefault(
                node_id,
                {
                    "node_id": node_id,
                    "node_label": str(row[3]),
                    "questions": [],
                },
            )
            node_group["questions"].append(
                WrongAnswerQuestion(
                    question_record_id=str(row[0]),
                    question_id=str(row[1]) if row[1] is not None else None,
                    node_id=node_id,
                    question_text=str(row[4]),
                    user_answer=str(row[5]),
                    correct_answer=str(row[6]),
                    error_type=str(row[7]),
                    error_severity=int(row[8]),
                    question_type=str(row[9]),
                    attempted_at=str(row[10]),
                    is_invalidated=bool(row[11]),
                )
            )

        by_node = [
            WrongAnswerNodeGroup(
                node_id=group["node_id"],
                node_label=group["node_label"],
                total_errors=len(group["questions"]),
                questions=group["questions"],
            )
            for group in grouped.values()
        ]

        return WrongAnswersData(
            by_node=by_node,
            summary=WrongAnswersSummary(
                total_wrong_count=len(rows),
                total_nodes_with_errors=len(by_node),
            ),
        )
    finally:
        if own_connection:
            connection.close()


def get_chapter_mastery(
    *,
    user_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> ChapterMasteryData:
    """Return mastery metrics grouped by parent chapter (parent_id cluster)."""

    own_connection = conn is None
    connection = conn or get_connection()
    try:
        ensure_review_tables_ready(connection)
        rows = connection.execute(
            """
            SELECT
                COALESCE(kn.parent_id, qh.node_id) AS parent_id,
                COALESCE(parent_kn.label, kn.label, COALESCE(kn.parent_id, qh.node_id)) AS parent_label,
                COUNT(*) AS attempted_count,
                SUM(CASE WHEN qh.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count
            FROM question_history qh
            LEFT JOIN knowledge_nodes kn ON kn.node_id = qh.node_id
            LEFT JOIN knowledge_nodes parent_kn ON parent_kn.node_id = kn.parent_id
            WHERE qh.user_id = ?
              AND qh.is_invalidated = 0
            GROUP BY COALESCE(kn.parent_id, qh.node_id),
                     COALESCE(parent_kn.label, kn.label, COALESCE(kn.parent_id, qh.node_id))
            ORDER BY COALESCE(kn.parent_id, qh.node_id) ASC
            """,
            (user_id,),
        ).fetchall()

        by_parent: list[ChapterMasteryItem] = []
        total_attempted = 0
        total_correct = 0

        for row in rows:
            parent_id = str(row[0])
            parent_label = str(row[1])
            attempted_count = int(row[2])
            correct_count = int(row[3])
            mastery_score = (correct_count / attempted_count) if attempted_count else 0.0

            total_attempted += attempted_count
            total_correct += correct_count

            by_parent.append(
                ChapterMasteryItem(
                    parent_id=parent_id,
                    parent_label=parent_label,
                    attempted_count=attempted_count,
                    correct_count=correct_count,
                    mastery_score=mastery_score,
                )
            )

        overall_mastery_score = (total_correct / total_attempted) if total_attempted else 0.0

        return ChapterMasteryData(
            by_parent=by_parent,
            summary=ChapterMasterySummary(
                total_parents=len(by_parent),
                total_attempted=total_attempted,
                total_correct=total_correct,
                overall_mastery_score=overall_mastery_score,
            ),
        )
    finally:
        if own_connection:
            connection.close()


def invalidate_question_record(
    *,
    user_id: str,
    question_record_id: str,
    reason: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> InvalidateQuestionData:
    """Mark one question record invalidated for the owning user.

    This operation is idempotent. Repeating invalidation on an already invalidated
    record returns success with `already_invalidated=True`.
    """

    own_connection = conn is None
    connection = conn or get_connection()
    try:
        ensure_review_tables_ready(connection)
        row = connection.execute(
            """
            SELECT is_invalidated, invalidated_at
            FROM question_history
            WHERE question_record_id = ?
              AND user_id = ?
            """,
            (question_record_id, user_id),
        ).fetchone()

        if row is None:
            return InvalidateQuestionData(
                question_record_id=question_record_id,
                found=False,
                updated=False,
                already_invalidated=False,
                invalidated_at=None,
            )

        is_invalidated = int(row[0]) == 1
        existing_invalidated_at = str(row[1]) if row[1] is not None else None
        if is_invalidated:
            return InvalidateQuestionData(
                question_record_id=question_record_id,
                found=True,
                updated=False,
                already_invalidated=True,
                invalidated_at=existing_invalidated_at,
            )

        invalidated_at = _utc_now_iso()
        cursor = connection.execute(
            """
            UPDATE question_history
            SET is_invalidated = 1,
                invalidation_reason = COALESCE(?, invalidation_reason),
                invalidated_at = ?
            WHERE question_record_id = ?
              AND user_id = ?
              AND is_invalidated = 0
            """,
            (reason, invalidated_at, question_record_id, user_id),
        )
        updated_rows = int(cursor.rowcount)
        if updated_rows == 1:
            connection.commit()
            return InvalidateQuestionData(
                question_record_id=question_record_id,
                found=True,
                updated=True,
                already_invalidated=False,
                invalidated_at=invalidated_at,
            )

        # Another request can invalidate the row between our SELECT and UPDATE.
        # Re-read row state to preserve idempotent semantics under race conditions.
        row_after_update = connection.execute(
            """
            SELECT is_invalidated, invalidated_at
            FROM question_history
            WHERE question_record_id = ?
              AND user_id = ?
            """,
            (question_record_id, user_id),
        ).fetchone()

        if row_after_update is None:
            return InvalidateQuestionData(
                question_record_id=question_record_id,
                found=False,
                updated=False,
                already_invalidated=False,
                invalidated_at=None,
            )

        after_invalidated = int(row_after_update[0]) == 1
        after_invalidated_at = str(row_after_update[1]) if row_after_update[1] is not None else None
        if after_invalidated:
            return InvalidateQuestionData(
                question_record_id=question_record_id,
                found=True,
                updated=False,
                already_invalidated=True,
                invalidated_at=after_invalidated_at,
            )

        connection.commit()
        return InvalidateQuestionData(
            question_record_id=question_record_id,
            found=True,
            updated=False,
            already_invalidated=False,
            invalidated_at=None,
        )
    finally:
        if own_connection:
            connection.close()
