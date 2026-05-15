"""Test retrieval service with tenant isolation."""

from app.services.retrieval_service import RetrievalQuery


def test_retrieval_query_structure():
    query = RetrievalQuery(
        tenant_id="tenant-acme",
        query_text="what is RAG?",
        top_k=6,
    )

    assert query.tenant_id == "tenant-acme"
    assert query.query_text == "what is RAG?"
    assert query.top_k == 6


def test_retrieval_query_defaults():
    query = RetrievalQuery(tenant_id="t1")
    assert query.query_text == ""
    assert query.top_k == 6
