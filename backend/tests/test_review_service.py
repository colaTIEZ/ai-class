import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from app.services.review_service import (
    get_chapter_mastery,
    invalidate_question_record,
    get_wrong_answers_by_node,
    record_answer,
)
from app.services.vector_store import get_connection, init_db


class TestReviewService:
    def test_invalidate_question_record_is_idempotent_under_concurrency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/review.db"
            setup_conn = get_connection(db_path)
            init_db(setup_conn)
            setup_conn.execute(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("node-a", 1, "Derivative basics", None, "Derivative basics", 0, "content"),
            )
            setup_conn.commit()

            record_id = record_answer(
                user_id="user-1",
                node_id="node-a",
                question_text="Q1",
                user_answer="wrong-1",
                correct_answer="right-1",
                is_correct=False,
                error_type="logic_gap",
                conn=setup_conn,
            )
            setup_conn.close()

            barrier = Barrier(2)

            def call_invalidate():
                conn = get_connection(db_path)
                try:
                    barrier.wait()
                    return invalidate_question_record(
                        user_id="user-1",
                        question_record_id=record_id,
                        reason="concurrent-report",
                        conn=conn,
                    )
                finally:
                    conn.close()

            with ThreadPoolExecutor(max_workers=2) as executor:
                first_future = executor.submit(call_invalidate)
                second_future = executor.submit(call_invalidate)
                first_result = first_future.result()
                second_result = second_future.result()

            updated_count = int(first_result.updated) + int(second_result.updated)
            already_count = int(first_result.already_invalidated) + int(second_result.already_invalidated)
            assert updated_count == 1
            assert already_count == 1

            verify_conn = get_connection(db_path)
            row = verify_conn.execute(
                "SELECT is_invalidated, invalidated_at FROM question_history WHERE question_record_id = ?",
                (record_id,),
            ).fetchone()
            assert row is not None
            assert int(row[0]) == 1
            assert isinstance(row[1], str)
            verify_conn.close()

    def test_invalidate_question_record_success_and_idempotent(self):
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
            conn.commit()

            record_id = record_answer(
                user_id="user-1",
                node_id="node-a",
                question_text="Q1",
                user_answer="wrong-1",
                correct_answer="right-1",
                is_correct=False,
                error_type="logic_gap",
                conn=conn,
            )

            first_result = invalidate_question_record(
                user_id="user-1",
                question_record_id=record_id,
                reason="hallucinated answer",
                conn=conn,
            )
            second_result = invalidate_question_record(
                user_id="user-1",
                question_record_id=record_id,
                reason="duplicate report",
                conn=conn,
            )

            assert first_result.updated is True
            assert first_result.already_invalidated is False
            assert second_result.updated is False
            assert second_result.already_invalidated is True

            row = conn.execute(
                """
                SELECT is_invalidated, invalidation_reason, invalidated_at
                FROM question_history
                WHERE question_record_id = ?
                """,
                (record_id,),
            ).fetchone()

            assert row is not None
            assert int(row[0]) == 1
            assert row[1] == "hallucinated answer"
            assert isinstance(row[2], str)
            assert row[2].endswith("Z")

            conn.close()

    def test_invalidate_question_record_rejects_wrong_owner(self):
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
            conn.commit()

            record_id = record_answer(
                user_id="owner-user",
                node_id="node-a",
                question_text="Q1",
                user_answer="wrong-1",
                correct_answer="right-1",
                is_correct=False,
                error_type="logic_gap",
                conn=conn,
            )

            result = invalidate_question_record(
                user_id="other-user",
                question_record_id=record_id,
                reason="not owner",
                conn=conn,
            )

            assert result.found is False
            assert result.updated is False
            assert result.already_invalidated is False

            row = conn.execute(
                "SELECT is_invalidated, invalidation_reason FROM question_history WHERE question_record_id = ?",
                (record_id,),
            ).fetchone()
            assert row is not None
            assert int(row[0]) == 0
            assert row[1] is None

            conn.close()

    def test_get_chapter_mastery_returns_empty_summary_when_no_attempts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)

            result = get_chapter_mastery(user_id="user-empty", conn=conn)

            assert result.by_parent == []
            assert result.summary.total_parents == 0
            assert result.summary.total_attempted == 0
            assert result.summary.total_correct == 0
            assert result.summary.overall_mastery_score == 0

            conn.close()

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

    def test_get_chapter_mastery_computes_ratio_by_parent_cluster(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)
            conn.executemany(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("chapter-1", 1, "Chapter 1", None, "c1", 0, "c1"),
                    ("chapter-2", 1, "Chapter 2", None, "c2", 0, "c2"),
                    ("n-1", 1, "Node 1", "chapter-1", "n1", 1, "n1"),
                    ("n-2", 1, "Node 2", "chapter-1", "n2", 1, "n2"),
                    ("n-3", 1, "Node 3", "chapter-2", "n3", 1, "n3"),
                ],
            )
            conn.commit()

            # Chapter 1: 2 correct / 3 attempts => 0.6667
            record_answer(
                user_id="user-1",
                node_id="n-1",
                question_text="Q1",
                user_answer="A",
                correct_answer="A",
                is_correct=True,
                error_type="no_error",
                conn=conn,
            )
            record_answer(
                user_id="user-1",
                node_id="n-2",
                question_text="Q2",
                user_answer="B",
                correct_answer="C",
                is_correct=False,
                error_type="logic_gap",
                conn=conn,
            )
            record_answer(
                user_id="user-1",
                node_id="n-2",
                question_text="Q3",
                user_answer="D",
                correct_answer="D",
                is_correct=True,
                error_type="no_error",
                conn=conn,
            )

            # Chapter 2: 0 correct / 1 attempts => 0
            record_answer(
                user_id="user-1",
                node_id="n-3",
                question_text="Q4",
                user_answer="X",
                correct_answer="Y",
                is_correct=False,
                error_type="conceptual",
                conn=conn,
            )

            result = get_chapter_mastery(user_id="user-1", conn=conn)

            by_chapter = {item.parent_id: item for item in result.by_parent}
            assert set(by_chapter.keys()) == {"chapter-1", "chapter-2"}
            assert by_chapter["chapter-1"].attempted_count == 3
            assert by_chapter["chapter-1"].correct_count == 2
            assert by_chapter["chapter-1"].mastery_score == 2 / 3
            assert by_chapter["chapter-2"].attempted_count == 1
            assert by_chapter["chapter-2"].correct_count == 0
            assert by_chapter["chapter-2"].mastery_score == 0
            assert result.summary.total_parents == 2
            assert result.summary.total_attempted == 4
            assert result.summary.total_correct == 2

            conn.close()

    def test_get_chapter_mastery_excludes_invalidated_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)
            conn.executemany(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("chapter-1", 1, "Chapter 1", None, "c1", 0, "c1"),
                    ("n-1", 1, "Node 1", "chapter-1", "n1", 1, "n1"),
                ],
            )
            conn.commit()

            valid_id = record_answer(
                user_id="user-1",
                node_id="n-1",
                question_text="Q1",
                user_answer="A",
                correct_answer="A",
                is_correct=True,
                error_type="no_error",
                conn=conn,
            )
            invalidated_id = record_answer(
                user_id="user-1",
                node_id="n-1",
                question_text="Q2",
                user_answer="B",
                correct_answer="C",
                is_correct=False,
                error_type="logic_gap",
                conn=conn,
            )
            conn.execute(
                "UPDATE question_history SET is_invalidated = 1 WHERE question_record_id = ?",
                (invalidated_id,),
            )
            conn.commit()

            result = get_chapter_mastery(user_id="user-1", conn=conn)

            assert result.summary.total_parents == 1
            assert result.summary.total_attempted == 1
            assert result.summary.total_correct == 1
            assert result.by_parent[0].attempted_count == 1
            assert result.by_parent[0].correct_count == 1
            assert result.by_parent[0].mastery_score == 1
            assert valid_id != invalidated_id

            conn.close()

    def test_get_chapter_mastery_all_correct_case(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)
            conn.executemany(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("chapter-1", 1, "Chapter 1", None, "c1", 0, "c1"),
                    ("n-1", 1, "Node 1", "chapter-1", "n1", 1, "n1"),
                    ("n-2", 1, "Node 2", "chapter-1", "n2", 1, "n2"),
                ],
            )
            conn.commit()

            for idx in range(3):
                record_answer(
                    user_id="user-1",
                    node_id="n-1" if idx % 2 == 0 else "n-2",
                    question_text=f"Q{idx}",
                    user_answer="A",
                    correct_answer="A",
                    is_correct=True,
                    error_type="no_error",
                    conn=conn,
                )

            result = get_chapter_mastery(user_id="user-1", conn=conn)

            assert result.summary.total_parents == 1
            assert result.summary.total_attempted == 3
            assert result.summary.total_correct == 3
            assert result.summary.overall_mastery_score == 1
            assert result.by_parent[0].parent_id == "chapter-1"
            assert result.by_parent[0].attempted_count == 3
            assert result.by_parent[0].correct_count == 3
            assert result.by_parent[0].mastery_score == 1

            conn.close()

    def test_get_chapter_mastery_returns_empty_when_all_records_invalidated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = get_connection(f"{tmpdir}/review.db")
            init_db(conn)
            conn.executemany(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("chapter-1", 1, "Chapter 1", None, "c1", 0, "c1"),
                    ("n-1", 1, "Node 1", "chapter-1", "n1", 1, "n1"),
                ],
            )
            conn.commit()

            record_id = record_answer(
                user_id="user-1",
                node_id="n-1",
                question_text="Q1",
                user_answer="wrong",
                correct_answer="right",
                is_correct=False,
                error_type="logic_gap",
                conn=conn,
            )

            invalidation = invalidate_question_record(
                user_id="user-1",
                question_record_id=record_id,
                reason="hallucinated",
                conn=conn,
            )
            assert invalidation.updated is True

            mastery = get_chapter_mastery(user_id="user-1", conn=conn)
            wrong_answers = get_wrong_answers_by_node(user_id="user-1", conn=conn)

            assert mastery.by_parent == []
            assert mastery.summary.total_parents == 0
            assert mastery.summary.total_attempted == 0
            assert mastery.summary.total_correct == 0
            assert mastery.summary.overall_mastery_score == 0

            assert wrong_answers.by_node == []
            assert wrong_answers.summary.total_wrong_count == 0
            assert wrong_answers.summary.total_nodes_with_errors == 0

            conn.close()
