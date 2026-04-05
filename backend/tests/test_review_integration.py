import tempfile

from fastapi.testclient import TestClient

from app.main import app
from app.services.review_service import record_answer
from app.services.vector_store import get_connection, init_db


class TestReviewIntegration:
    def test_record_then_query_review_notebook(self, monkeypatch):
        client = TestClient(app)

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f'{tmpdir}/review.db'
            conn = get_connection(db_path)
            init_db(conn)
            conn.execute(
                """
                INSERT INTO knowledge_nodes (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ('node-a', 1, 'Derivative basics', None, 'Derivative basics', 0, 'content'),
            )
            conn.commit()

            record_answer(
                user_id='user-1',
                node_id='node-a',
                question_text='What is f\'(x)?',
                user_answer='x',
                correct_answer='2x',
                is_correct=False,
                error_type='calculation',
                error_severity=2,
                question_type='short_answer',
                question_id='question-1',
                attempt_id='attempt-1',
                selected_node_ids=['node-a'],
                conn=conn,
            )
            conn.close()

            def fake_get_connection(db_path=None):
                return get_connection(db_path=db_path or f'{tmpdir}/review.db')

            monkeypatch.setattr('app.services.review_service.get_connection', fake_get_connection)

            response = client.get('/api/v1/review/wrong-answers', headers={'X-User-ID': 'user-1'})

            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'success'
            assert data['data']['summary']['total_wrong_count'] == 1
            assert data['data']['by_node'][0]['node_id'] == 'node-a'
            assert data['data']['by_node'][0]['questions'][0]['correct_answer'] == '2x'
