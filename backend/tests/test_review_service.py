import tempfile

from app.services.review_service import get_wrong_answers_by_node, record_answer
from app.services.vector_store import get_connection, init_db


class TestReviewService:
    def test_record_answer_persists_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)
            conn.execute(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "node-a",
                    1,
                    "Derivative basics",
                    None,
                    "Basics of derivatives",
                    0,
                    "Derivative content",
                ),
            )
            conn.commit()

            record_id = record_answer(
                user_id="user-1",
                node_id="node-a",
                question_text="What is f'(x)?",
                user_answer="x",
                correct_answer="2x",
                is_correct=False,
                error_type="calculation",
                error_severity=2,
                question_type="short_answer",
                question_id="question-1",
                attempt_id="attempt-1",
                selected_node_ids=["node-a"],
                conn=conn,
            )

            question_row = conn.execute(
                """
                SELECT question_record_id, attempt_id, user_id, node_id, question_text, user_answer,
                       correct_answer, is_correct, error_type, error_severity, question_type, is_invalidated
                FROM question_history
                WHERE question_record_id = ?
                """,
                (record_id,),
            ).fetchone()
            assert question_row is not None
            assert question_row[1] == "attempt-1"
            assert question_row[2] == "user-1"
            assert question_row[3] == "node-a"
            assert question_row[4] == "What is f'(x)?"
            assert question_row[5] == "x"
            assert question_row[6] == "2x"
            assert int(question_row[7]) == 0
            assert question_row[8] == "calculation"
            assert int(question_row[9]) == 2
            assert question_row[10] == "short_answer"
            assert int(question_row[11]) == 0

            attempt_row = conn.execute(
                "SELECT attempt_id, user_id, selected_node_ids FROM quiz_attempts WHERE attempt_id = ?",
                ("attempt-1",),
            ).fetchone()
            assert attempt_row is not None
            assert attempt_row[0] == "attempt-1"
            assert attempt_row[1] == "user-1"
            assert attempt_row[2] == '["node-a"]'

            conn.close()

    def test_get_wrong_answers_groups_by_node_and_filters_invalidated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)
            for node_id, label in [("node-a", "Derivative basics"), ("node-b", "Integral basics")]:
                conn.execute(
                    """
                    INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (node_id, 1, label, None, label, 0, label),
                )
            conn.commit()

            record_answer(
                user_id="user-1",
                node_id="node-a",
                question_text="Q1",
                user_answer="wrong-1",
                correct_answer="right-1",
                is_correct=False,
                error_type="logic_gap",
                error_severity=1,
                question_type="multiple_choice",
                question_id="question-1",
                attempt_id="attempt-1",
                selected_node_ids=["node-a"],
                conn=conn,
            )
            invalidated_id = record_answer(
                user_id="user-1",
                node_id="node-a",
                question_text="Q2",
                user_answer="wrong-2",
                correct_answer="right-2",
                is_correct=False,
                error_type="logic_gap",
                error_severity=2,
                question_type="multiple_choice",
                question_id="question-2",
                attempt_id="attempt-1",
                selected_node_ids=["node-a"],
                conn=conn,
            )
            record_answer(
                user_id="user-1",
                node_id="node-b",
                question_text="Q3",
                user_answer="wrong-3",
                correct_answer="right-3",
                is_correct=False,
                error_type="conceptual",
                error_severity=3,
                question_type="short_answer",
                question_id="question-3",
                attempt_id="attempt-2",
                selected_node_ids=["node-b"],
                conn=conn,
            )

            conn.execute(
                "UPDATE question_history SET is_invalidated = 1 WHERE question_record_id = ?",
                (invalidated_id,),
            )
            conn.commit()

            result = get_wrong_answers_by_node(user_id="user-1", conn=conn)

            assert result.summary.total_wrong_count == 2
            assert result.summary.total_nodes_with_errors == 2
            assert [group.node_id for group in result.by_node] == ["node-a", "node-b"]
            assert result.by_node[0].total_errors == 1
            assert result.by_node[0].questions[0].question_text == "Q1"
            assert result.by_node[1].questions[0].question_text == "Q3"
            assert all(question.is_invalidated is False for group in result.by_node for question in group.questions)

            conn.close()

    def test_get_wrong_answers_applies_node_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)
            conn.execute(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("node-a", 1, "Derivative basics", None, "Derivative basics", 0, "content"),
            )
            conn.execute(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("node-b", 1, "Integral basics", None, "Integral basics", 0, "content"),
            )
            conn.commit()

            record_answer(
                user_id="user-1",
                node_id="node-a",
                question_text="Q1",
                user_answer="wrong-1",
                correct_answer="right-1",
                is_correct=False,
                error_type="logic_gap",
                conn=conn,
            )
            record_answer(
                user_id="user-1",
                node_id="node-b",
                question_text="Q2",
                user_answer="wrong-2",
                correct_answer="right-2",
                is_correct=False,
                error_type="conceptual",
                conn=conn,
            )

            result = get_wrong_answers_by_node(user_id="user-1", node_id_filter="node-a", conn=conn)

            assert result.summary.total_wrong_count == 1
            assert result.summary.total_nodes_with_errors == 1
            assert result.by_node[0].node_id == "node-a"
            assert result.by_node[0].questions[0].question_text == "Q1"

            conn.close()
