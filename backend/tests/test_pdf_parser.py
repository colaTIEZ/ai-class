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
        "Chapter 1: AI Basics\nWhat is AI?\nIt mimics human intelligence.\n1.1 What is Intelligence\nIntelligence includes perception.",
        "1.2 What is Learning\nLearning improves performance.\nLearning from data is central.",
        "Chapter 2: Machine Learning\n2.1 Supervised Learning\nSupervised learning uses labeled data."
    ]
    nodes = extract_hierarchy(1, chunks)
    assert len(nodes) > 0
    assert isinstance(nodes[0], KnowledgeNodeInDB)

    chapters = [n for n in nodes if n.depth == 1]
    sections = [n for n in nodes if n.depth == 2]
    paragraphs = [n for n in nodes if n.depth == 3]

    assert len(chapters) == 2
    assert "AI Basics" in chapters[0].label
    assert "Machine Learning" in chapters[1].label
    assert len(sections) >= 3
    assert len(paragraphs) >= 3
    assert any(n.parent_id == chapters[0].node_id for n in sections)
    assert any(n.parent_id == chapters[1].node_id for n in sections)
