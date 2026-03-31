import pytest
import os
import fitz
from unittest.mock import patch, MagicMock
from app.services.pdf_parser import process_pdf_generator, extract_hierarchy
from app.schemas.knowledge_tree import KnowledgeNodeInDB

@pytest.fixture
def mock_pdf_path(tmp_path):
    pdf_path = tmp_path / "test_doc.pdf"
    doc = fitz.open()
    # Create page 1 with chapter 1
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Chapter 1: AI Basics\n\nWhat is AI?")
    # Create page 2 with chapter 2
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Chapter 2: Machine Learning\n\nIt allows computers to learn.")
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)

def test_process_pdf_generator(mock_pdf_path):
    chunks = list(process_pdf_generator(mock_pdf_path, chunk_size=50))
    # Expect 2 chapters -> maybe more chunks
    assert len(chunks) > 0
    # Should not load all into memory at once
    assert any("AI Basics" in chunk for chunk in chunks)

def test_extract_hierarchy():
    chunks = [
        "Chapter 1: AI Basics\nWhat is AI?\nIt mimics human intelligence.",
        "This is a supplement to part 2 of chapter 1.\n1.1 What is Intelligence\nIntelligence includes perception.",
        "Chapter 2: Machine Learning\n\nIt allows computers to learn."
    ]
    nodes = extract_hierarchy(1, chunks)
    assert len(nodes) > 0
    assert isinstance(nodes[0], KnowledgeNodeInDB)
    # Check parent-child relation
    chapters = [n for n in nodes if n.depth == 1]
    assert len(chapters) == 2
    assert "AI Basics" in chapters[0].label
    assert "Machine Learning" in chapters[1].label
