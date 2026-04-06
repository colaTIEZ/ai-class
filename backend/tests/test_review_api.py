import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
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

    def test_chapter_mastery_requires_user_header(self):
        client = TestClient(app)
        response = client.get('/api/v1/review/chapter-mastery')

        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert data['message'] == 'Missing X-User-ID header'

    def test_chapter_mastery_success_response(self):
        client = TestClient(app)
        payload = ChapterMasteryData(
            by_parent=[
                ChapterMasteryItem(
                    parent_id='chapter-1',
                    parent_label='Chapter 1',
                    attempted_count=3,
                    correct_count=2,
                    mastery_score=2 / 3,
                )
            ],
            summary=ChapterMasterySummary(
                total_parents=1,
                total_attempted=3,
                total_correct=2,
                overall_mastery_score=2 / 3,
            ),
        )

        with patch('app.api.v1.review.get_chapter_mastery', return_value=payload) as mock_service:
            response = client.get('/api/v1/review/chapter-mastery', headers={'X-User-ID': 'user-1'})

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['data']['by_parent'][0]['parent_id'] == 'chapter-1'
        assert data['data']['by_parent'][0]['attempted_count'] == 3
        assert data['data']['summary']['total_parents'] == 1
        mock_service.assert_called_once_with(user_id='user-1')

    def test_invalidate_requires_user_header(self):
        client = TestClient(app)
        response = client.post(
            '/api/v1/review/invalidate',
            json={'question_record_id': 'q-1', 'reason': 'hallucinated'},
        )

        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert data['message'] == 'Missing X-User-ID header'

    def test_invalidate_returns_not_found_for_wrong_owner(self):
        client = TestClient(app)
        payload = InvalidateQuestionData(
            question_record_id='q-1',
            found=False,
            updated=False,
            already_invalidated=False,
            invalidated_at=None,
        )

        with patch('app.api.v1.review.invalidate_question_record', return_value=payload):
            response = client.post(
                '/api/v1/review/invalidate',
                headers={'X-User-ID': 'user-1'},
                json={'question_record_id': 'q-1', 'reason': 'hallucinated'},
            )

        assert response.status_code == 404
        data = response.json()
        assert data['status'] == 'error'

    def test_invalidate_success_response(self):
        client = TestClient(app)
        payload = InvalidateQuestionData(
            question_record_id='q-1',
            found=True,
            updated=True,
            already_invalidated=False,
            invalidated_at='2026-04-06T12:00:00Z',
        )

        with patch('app.api.v1.review.invalidate_question_record', return_value=payload) as mock_service:
            response = client.post(
                '/api/v1/review/invalidate',
                headers={'X-User-ID': 'user-1'},
                json={'question_record_id': 'q-1', 'reason': 'hallucinated'},
            )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['data']['question_record_id'] == 'q-1'
        assert data['data']['updated'] is True
        assert data['data']['already_invalidated'] is False
        mock_service.assert_called_once_with(
            user_id='user-1',
            question_record_id='q-1',
            reason='hallucinated',
        )

    def test_invalidate_already_invalidated_is_idempotent_success(self):
        client = TestClient(app)
        payload = InvalidateQuestionData(
            question_record_id='q-1',
            found=True,
            updated=False,
            already_invalidated=True,
            invalidated_at='2026-04-06T12:00:00Z',
        )

        with patch('app.api.v1.review.invalidate_question_record', return_value=payload):
            response = client.post(
                '/api/v1/review/invalidate',
                headers={'X-User-ID': 'user-1'},
                json={'question_record_id': 'q-1', 'reason': 'duplicate'},
            )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['data']['updated'] is False
        assert data['data']['already_invalidated'] is True

    def test_invalidate_rejects_blank_question_record_id(self):
        client = TestClient(app)
        response = client.post(
            '/api/v1/review/invalidate',
            headers={'X-User-ID': 'user-1'},
            json={'question_record_id': '   ', 'reason': 'blank id'},
        )

        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert data['message'] == 'question_record_id must not be blank'
