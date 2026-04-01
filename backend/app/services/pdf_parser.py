import os
import re
import time
import fitz
import logging
from fastapi import status
from typing import Generator, List, Dict, Any
from app.schemas.knowledge_tree import KnowledgeNodeInDB
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

def generate_embeddings(nodes: List[KnowledgeNodeInDB]) -> List[tuple[str, List[float]]]:
    """Generate OpenAI embeddings for chunks."""
    if not settings.openai_api_key:
        logger.error("OpenAI API key configuration is missing.")
        raise AppException(
            "OpenAI API key configuration is missing.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        
    try:
        embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url or None,
            model=settings.openai_model if "embedding" in settings.openai_model else "text-embedding-3-small"
        )
        texts = [node.chunk_text for node in nodes if node.chunk_text]
        node_ids = [node.node_id for node in nodes if node.chunk_text]
        
        if not texts:
            return []
            
        for attempt in range(3):
            try:
                embeddings = embeddings_model.embed_documents(texts)
                return list(zip(node_ids, embeddings))
            except Exception as e_retry:
                if attempt == 2:
                    raise
                logger.warning(f"Embedding retry {attempt + 1}: {e_retry}")
                time.sleep(2 ** attempt)
        return []
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise

def process_pdf_generator(file_path: str, chunk_size=1000, overlap=100) -> Generator[str, None, None]:
    """
    Reads a PDF file page by page and yields chunked text to stay under memory limits.
    1.5GB limit on backend demands strict generative chunking.
    """
    from pathlib import Path
    resolved_path = Path(file_path).resolve()
    if ".." in str(file_path) or not resolved_path.exists():
        raise ValueError("Invalid file path or access denied.")

    doc = fitz.open(str(resolved_path))
    try:
        current_chunk = ""
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                text = page.get_text("text")

                # Split logic by newline or spaces for simple structural maintaining
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if len(current_chunk) + len(line) > chunk_size:
                        yield current_chunk.strip()
                        # Retain last few characters for overlap context
                        overlap_trigger = len(current_chunk) - overlap
                        if overlap_trigger > 0:
                            current_chunk = current_chunk[overlap_trigger:] + " " + line
                        else:
                            current_chunk = line
                    else:
                        current_chunk += "\n" + line if current_chunk else line

            except Exception as e:
                logger.error(f"Error reading page {page_num} of {file_path}: {e}")
                continue

        if current_chunk.strip():
            yield current_chunk.strip()
    finally:
        doc.close()


def extract_hierarchy(document_id: int, chunks: List[str]) -> List[KnowledgeNodeInDB]:
    """
    Parses hierarchical structure heuristically with regex.
    Chapter -> Section -> Chunk mappings mapped to 1.1 Schema.
    """
    nodes = []
    
    # Root doc node (Depth 0)
    root_id = f"doc_{document_id}_root"
    nodes.append(KnowledgeNodeInDB(
        node_id=root_id,
        document_id=document_id,
        label="Document Root",
        parent_id=None,
        content_summary="Document overview",
        depth=0
    ))

    current_chapter_id = root_id
    current_section_id = root_id
    
    # Simple regex to identify Chapters/Sections
    chapter_pattern = re.compile(r"^(第[一二三四五六七八九十百]+章|Chapter\s*\d+|[1-9]\d*\.0?)\s*[:：\s]?\s*(.*)", re.IGNORECASE)
    section_pattern = re.compile(r"^(第[一二三四五六七八九十百]+节|Section\s*\d+|\d+\.\d+)\s*[:：\s]?\s*(.*)", re.IGNORECASE)

    seq_counter = 1

    for chunk in chunks:
        lines = chunk.split('\n')
        # Check first line of chunk to determine if it defines a new chapter/section
        if not lines:
             continue
        first_line = lines[0].strip()[:100]  # Just looking at start
        
        chapter_match = chapter_pattern.search(first_line)
        section_match = section_pattern.search(first_line)
        
        node_id = f"doc_{document_id}_node_{seq_counter:03d}"
        seq_counter += 1

        if chapter_match:
            label = chapter_match.group(2).strip()[:50]
            if not label:
                label = chapter_match.group(1).strip()
            current_chapter_id = node_id
            current_section_id = node_id # Reset section
            depth = 1
            parent_id = root_id
        elif section_match:
            label = section_match.group(2).strip()[:50]
            if not label:
                label = section_match.group(1).strip()
            current_section_id = node_id
            depth = 2
            parent_id = current_chapter_id
        else:
            # Regular chunk node
            label = first_line[:30] + "..." if len(first_line) > 30 else first_line
            if not label:
                label = "Paragraph"
            depth = 3
            parent_id = current_section_id

        summary = chunk[:100] + "..." if len(chunk) > 100 else chunk
        
        nodes.append(KnowledgeNodeInDB(
            node_id=node_id,
            document_id=document_id,
            label=label,
            parent_id=parent_id,
            content_summary=summary,
            depth=depth,
            chunk_text=chunk
        ))

    return nodes
