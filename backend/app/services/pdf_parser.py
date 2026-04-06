import os
import re
import time
import fitz
import logging
import requests
from fastapi import status
from typing import Generator, List, Dict, Any
from app.schemas.knowledge_tree import KnowledgeNodeInDB
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def _embedding_model_candidates() -> List[str]:
    """Build ordered unique embedding model candidates from settings."""
    candidates: List[str] = []

    # 1) Explicit embedding model always wins
    if settings.openai_embedding_model:
        candidates.append(settings.openai_embedding_model.strip())

    # 2) If user puts an embedding model into openai_model, allow it as backup
    if settings.openai_model and "embedding" in settings.openai_model:
        candidates.append(settings.openai_model.strip())

    # 3) Optional fallback model from config
    if settings.openai_embedding_fallback_model:
        candidates.append(settings.openai_embedding_fallback_model.strip())

    # 4) Safe default fallback to keep backward compatibility
    candidates.append("text-embedding-v2")

    # Unique + non-empty preserving order
    deduped: List[str] = []
    for model in candidates:
        if model and model not in deduped:
            deduped.append(model)
    return deduped


def _is_model_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "model_not_found" in message or "does not exist" in message

def _generate_embeddings_dashscope(texts: List[str], model_name: str) -> List[List[float]]:
    """直接调用阿里云 DashScope embedding API,使用正确的参数格式。

    Args:
        texts: 需要生成嵌入的文本列表
        model_name: 模型名称 (如 text-embedding-v1/v2/v3)

    Returns:
        嵌入向量列表
    """
    api_url = f"{settings.openai_base_url}/embeddings"

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    # DashScope 期望的格式: input 是字符串或字符串数组
    payload = {
        "model": model_name,
        "input": texts,
    }

    response = requests.post(api_url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    result = response.json()
    # DashScope 返回格式: {"data": [{"embedding": [...], "index": 0}, ...]}
    embeddings = [item["embedding"] for item in sorted(result["data"], key=lambda x: x["index"])]
    return embeddings

def generate_embeddings(nodes: List[KnowledgeNodeInDB]) -> List[tuple[str, List[float]]]:
    """Generate OpenAI embeddings for chunks."""
    if not settings.openai_api_key:
        logger.error("OpenAI API key configuration is missing.")
        raise AppException(
            "OpenAI API key configuration is missing.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        
    texts = [node.chunk_text for node in nodes if node.chunk_text]
    node_ids = [node.node_id for node in nodes if node.chunk_text]

    if not texts:
        return []

    candidates = _embedding_model_candidates()
    last_exception: Exception | None = None

    for model_name in candidates:
        try:
            # 检测是否使用阿里云 DashScope
            is_dashscope = "dashscope" in (settings.openai_base_url or "").lower()

            if is_dashscope:
                # 使用 DashScope 兼容的 API 调用方式
                for attempt in range(3):
                    try:
                        embeddings = _generate_embeddings_dashscope(texts, model_name)
                        logger.info("成功使用模型 %s 生成 %d 个嵌入向量", model_name, len(embeddings))
                        return list(zip(node_ids, embeddings))
                    except Exception as e_retry:
                        if attempt == 2:
                            raise
                        logger.warning("嵌入重试 %d (模型=%s): %s", attempt + 1, model_name, e_retry)
                        time.sleep(2 ** attempt)
            else:
                # 对其他提供商使用标准的 LangChain OpenAIEmbeddings
                embeddings_model = OpenAIEmbeddings(
                    openai_api_key=settings.openai_api_key,
                    openai_api_base=settings.openai_base_url or None,
                    model=model_name,
                )

            for attempt in range(3):
                try:
                    embeddings = embeddings_model.embed_documents(texts)
                    logger.info("Embeddings generated with model: %s", model_name)
                    return list(zip(node_ids, embeddings))
                except Exception as e_retry:
                    # Retry transient errors on current model
                    if attempt == 2:
                        raise
                    logger.warning("Embedding retry %s (model=%s): %s", attempt + 1, model_name, e_retry)
                    time.sleep(2 ** attempt)

        except Exception as e:
            last_exception = e
            if _is_model_not_found_error(e):
                logger.warning("Embedding model unavailable, fallback to next candidate: %s", model_name)
                continue
            logger.error("Failed to generate embeddings with model %s: %s", model_name, e)
            raise

    model_list = ", ".join(candidates)
    logger.error("All embedding models failed. tried=[%s], last_error=%s", model_list, last_exception)
    raise AppException(
        message=(
            "No available embedding model for current provider. "
            "Please set OPENAI_EMBEDDING_MODEL in backend/.env to a model your API key can access. "
            f"Tried: {model_list}"
        ),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )

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
    Parses hierarchical structure heuristically with regex and fallback heuristics.
    Creates a 3-level hierarchy: Root -> Auto-Chapter -> Chunks
    Falls back to auto-grouping by content length heuristics if no explicit titles found.
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
    auto_chapter_counter = 1
    last_was_chapter = False

    for chunk_idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
            
        lines = chunk.split('\n')
        first_line = lines[0].strip()[:100]
        
        chapter_match = chapter_pattern.search(first_line)
        section_match = section_pattern.search(first_line)
        
        node_id = f"doc_{document_id}_node_{seq_counter:03d}"
        seq_counter += 1

        if chapter_match:
            # Explicit chapter found
            label = chapter_match.group(2).strip()[:50]
            if not label:
                label = chapter_match.group(1).strip()
            current_chapter_id = node_id
            current_section_id = node_id
            depth = 1
            parent_id = root_id
            nodes.append(KnowledgeNodeInDB(
                node_id=node_id,
                document_id=document_id,
                label=label,
                parent_id=parent_id,
                content_summary=chunk[:100] + "...",
                depth=depth,
                chunk_text=chunk
            ))
            last_was_chapter = True
        elif section_match:
            # Explicit section found
            label = section_match.group(2).strip()[:50]
            if not label:
                label = section_match.group(1).strip()
            current_section_id = node_id
            depth = 2
            parent_id = current_chapter_id
            nodes.append(KnowledgeNodeInDB(
                node_id=node_id,
                document_id=document_id,
                label=label,
                parent_id=parent_id,
                content_summary=chunk[:100] + "...",
                depth=depth,
                chunk_text=chunk
            ))
            last_was_chapter = False
        else:
            # No explicit title: use heuristic to auto-create chapter if needed
            # Criteria: very short lines likely indicate title or section break
            is_likely_title = (
                len(first_line) < 50 and 
                len(first_line) > 3 and
                not first_line.endswith(('。', '，', ',', '.', '!', '?', '？'))
            )
            
            if is_likely_title and not last_was_chapter:
                # Auto-create a chapter
                auto_ch_node_id = f"doc_{document_id}_chapter_{auto_chapter_counter:03d}"
                auto_chapter_counter += 1
                auto_label = first_line[:40]
                nodes.append(KnowledgeNodeInDB(
                    node_id=auto_ch_node_id,
                    document_id=document_id,
                    label=auto_label,
                    parent_id=root_id,
                    content_summary=auto_label,
                    depth=1,
                    chunk_text=None
                ))
                current_chapter_id = auto_ch_node_id
                current_section_id = auto_ch_node_id
                parent_id = auto_ch_node_id
                last_was_chapter = True
            else:
                parent_id = current_section_id
                last_was_chapter = False
            
            # Add chunk node
            label = first_line[:35] + "..." if len(first_line) > 35 else first_line
            if not label or label.strip() == "。":
                label = f"Paragraph {chunk_idx + 1}"
            
            nodes.append(KnowledgeNodeInDB(
                node_id=node_id,
                document_id=document_id,
                label=label,
                parent_id=parent_id,
                content_summary=chunk[:100] + ("..." if len(chunk) > 100 else ""),
                depth=3 if parent_id == current_section_id else 2,
                chunk_text=chunk
            ))

    return nodes
