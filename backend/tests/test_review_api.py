import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.review import WrongAnswerNodeGroup, WrongAnswerQuestion, WrongAnswersData, WrongAnswersSummary
from app.services.vector_store import get_connection, init_db


class TestReviewApi:
    def test_missing_user_header_returns_400(self):
        client = TestClient(app)
        response = client.get('/api/v1/review/wrong-answers')

        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert data['message'] == 'Missing X-User-ID header'
        assert data['trace_id']

    def test_successful_grouped_response(self):
        client = TestClient(app)
        payload = WrongAnswersData(
            by_node=[
                WrongAnswerNodeGroup(
                    node_id='node-a',
                    node_label='Derivative basics',
                    total_errors=1,
                    questions=[
                        WrongAnswerQuestion(
                            question_record_id='q-1',
                            question_id='question-1',
                            node_id='node-a',
                            question_text='Q1',
                            user_answer='wrong',
                            correct_answer='right',
                            error_type='logic_gap',
                            error_severity=1,
                            question_type='short_answer',
                            attempted_at='2026-04-05T10:00:00Z',
                            is_invalidated=False,
                        )
                    ],
                )
            ],
            summary=WrongAnswersSummary(total_wrong_count=1, total_nodes_with_errors=1),
        )

        with patch('app.api.v1.review.get_wrong_answers_by_node', return_value=payload) as mock_service:
            response = client.get('/api/v1/review/wrong-answers', headers={'X-User-ID': 'user-1'})

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['data']['summary']['total_wrong_count'] == 1
        assert data['data']['by_node'][0]['node_id'] == 'node-a'
        assert data['data']['by_node'][0]['questions'][0]['question_text'] == 'Q1'
        mock_service.assert_called_once_with(user_id='user-1', node_id_filter=None)

    def test_node_filter_is_passed_through(self):
        client = TestClient(app)
        payload = WrongAnswersData(
            by_node=[],
            summary=WrongAnswersSummary(total_wrong_count=0, total_nodes_with_errors=0),
        )

        with patch('app.api.v1.review.get_wrong_answers_by_node', return_value=payload) as mock_service:
            response = client.get(
                '/api/v1/review/wrong-answers?node_id_filter=node-a',
                headers={'X-User-ID': 'user-1'},
            )

        assert response.status_code == 200
        mock_service.assert_called_once_with(user_id='user-1', node_id_filter='node-a')
