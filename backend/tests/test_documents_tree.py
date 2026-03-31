import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_document_tree_not_found():
    response = client.get("/api/v1/documents/9999/tree")
    assert response.status_code == 200
    data = response.json()
    assert data["nodes"] == []
    assert data["total_nodes"] == 0
    assert data["document_id"] == 9999

def test_get_document_tree_success(monkeypatch):
    """Mock the sqlite connection and assert structure is correct"""
    import sqlite3
    
    def mock_get_document_nodes(conn, doc_id):
        # We simulate the sqlite3.Row dict-like behavior
        return [
            {"node_id": "doc_1_node_000", "label": "Chapter 1", "parent_id": None, "content_summary": "Summary 1", "depth": 0},
            {"node_id": "doc_1_node_001", "label": "Section 1.1", "parent_id": "doc_1_node_000", "content_summary": "Summary 2", "depth": 1}
        ]
        
    import app.api.v1.documents as docs_api
    monkeypatch.setattr(docs_api, "get_document_nodes", mock_get_document_nodes)

    response = client.get("/api/v1/documents/1/tree")
    assert response.status_code == 200
    
    data = response.json()
    assert data["document_id"] == 1
    assert data["total_nodes"] == 2
    assert len(data["nodes"]) == 2
    
    # Check that snake_case is preserved
    assert "node_id" in data["nodes"][0]
    assert data["nodes"][0]["node_id"] == "doc_1_node_000"
    assert data["nodes"][1]["parent_id"] == "doc_1_node_000"
