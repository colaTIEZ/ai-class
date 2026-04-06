"""Wrong-answer notebook API endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.schemas.review import ChapterMasteryResponse, WrongAnswersResponse
from app.services.review_service import get_chapter_mastery, get_wrong_answers_by_node

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])


def _error_response(status_code: int, message: str, trace_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "data": None,
            "message": message,
            "trace_id": trace_id,
        },
    )


@router.get(
    "/wrong-answers",
    response_model=WrongAnswersResponse,
    summary="Get wrong answers grouped by knowledge node",
)
async def get_wrong_answers(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    node_id_filter: str | None = Query(default=None),
) -> WrongAnswersResponse | JSONResponse:
    """Return the review notebook grouped by node_id."""

    trace_id = str(uuid.uuid4())
    if not x_user_id or not x_user_id.strip():
        return _error_response(400, "Missing X-User-ID header", trace_id)

    try:
        data = get_wrong_answers_by_node(
            user_id=x_user_id.strip(),
            node_id_filter=node_id_filter.strip() if node_id_filter else None,
        )
        return WrongAnswersResponse(
            status="success",
            data=data,
            message="",
            trace_id=trace_id,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Failed to fetch wrong answers: %s", exc)
        return _error_response(500, "Internal server error", trace_id)


@router.get(
    "/chapter-mastery",
    response_model=ChapterMasteryResponse,
    summary="Get chapter mastery grouped by parent_id cluster",
)
async def get_chapter_mastery_endpoint(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> ChapterMasteryResponse | JSONResponse:
    """Return chapter-level mastery metrics for the current user."""

    trace_id = str(uuid.uuid4())
    if not x_user_id or not x_user_id.strip():
        return _error_response(400, "Missing X-User-ID header", trace_id)

    try:
        data = get_chapter_mastery(user_id=x_user_id.strip())
        return ChapterMasteryResponse(
            status="success",
            data=data,
            message="",
            trace_id=trace_id,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Failed to fetch chapter mastery: %s", exc)
        return _error_response(500, "Internal server error", trace_id)
