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


def _normalize_title_line(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _is_sentence_like(text: str) -> bool:
    cleaned = _normalize_title_line(text)
    if not cleaned:
        return True
    return cleaned.endswith(("。", "，", ",", ".", "!", "?", "？", ";", "；"))


def _detect_chapter_title(line: str) -> tuple[str, str] | None:
    cleaned = _normalize_title_line(line)
    if not cleaned:
        return None

    match = re.match(r"^(第[一二三四五六七八九十百]+章|Chapter\s*\d+|Chapter\s*[IVXLC]+|\d+(?:\.0+)?)(?:\s*[:：\-—]\s*|\s+)(.+)$", cleaned, re.IGNORECASE)
    if match:
        title = _normalize_title_line(match.group(2))
        if title:
            return match.group(1).strip(), title[:80]

    # Strong fallback only for short, non-sentence, title-like lines.
    if 8 <= len(cleaned) <= 60 and not _is_sentence_like(cleaned):
        if re.match(r"^\d+\.\d+", cleaned):
            return None
        word_count = len(cleaned.split())
        if word_count <= 8 or re.search(r"[\u4e00-\u9fff]", cleaned):
            return "Chapter", cleaned[:80]

    return None


def _detect_section_title(line: str) -> tuple[str, str] | None:
    cleaned = _normalize_title_line(line)
    if not cleaned:
        return None

    match = re.match(r"^(第[一二三四五六七八九十百]+节|Section\s*\d+(?:\.\d+)*|\d+\.\d+(?:\.\d+)*)(?:\s*[:：\-—]\s*|\s+)(.+)$", cleaned, re.IGNORECASE)
    if match:
        title = _normalize_title_line(match.group(2))
        if title:
            return match.group(1).strip(), title[:80]

    return None


def _make_summary(text: str, limit: int = 120) -> str:
    cleaned = _normalize_title_line(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def extract_hierarchy(document_id: int, chunks: List[str]) -> List[KnowledgeNodeInDB]:
    """
    Parses hierarchical structure into a stable 3-level hierarchy: Root -> Chapter -> Section -> Paragraph.
    Prefers explicit headings and only uses conservative fallback logic for missing titles.
    """
    nodes: List[KnowledgeNodeInDB] = []

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
    current_section_id = None
    chapter_seq = 0
    section_seq = 0
    paragraph_seq = 0
    fallback_chapter_counter = 0

    def ensure_chapter(label: str, content_summary: str | None = None) -> str:
        nonlocal chapter_seq, current_chapter_id, current_section_id
        chapter_seq += 1
        chapter_id = f"doc_{document_id}_chapter_{chapter_seq:03d}"
        nodes.append(KnowledgeNodeInDB(
            node_id=chapter_id,
            document_id=document_id,
            label=label,
            parent_id=root_id,
            content_summary=content_summary or label,
            depth=1,
            chunk_text=None,
        ))
        current_chapter_id = chapter_id
        current_section_id = None
        return chapter_id

    def ensure_section(label: str, parent_id: str, content_summary: str | None = None) -> str:
        nonlocal section_seq, current_section_id
        section_seq += 1
        section_id = f"doc_{document_id}_section_{section_seq:03d}"
        nodes.append(KnowledgeNodeInDB(
            node_id=section_id,
            document_id=document_id,
            label=label,
            parent_id=parent_id,
            content_summary=content_summary or label,
            depth=2,
            chunk_text=None,
        ))
        current_section_id = section_id
        return section_id

    def add_paragraph(label: str, parent_id: str, body_text: str) -> None:
        nonlocal paragraph_seq
        paragraph_seq += 1
        paragraph_id = f"doc_{document_id}_paragraph_{paragraph_seq:03d}"
        nodes.append(KnowledgeNodeInDB(
            node_id=paragraph_id,
            document_id=document_id,
            label=label,
            parent_id=parent_id,
            content_summary=_make_summary(body_text),
            depth=3,
            chunk_text=body_text,
        ))

    def flush_paragraph_buffer(paragraph_lines: List[str], paragraph_fallback_index: int) -> None:
        nonlocal current_chapter_id, current_section_id, fallback_chapter_counter
        if not paragraph_lines:
            return

        body_text = "\n".join(paragraph_lines).strip()
        if not body_text:
            paragraph_lines.clear()
            return

        if current_chapter_id == root_id:
            fallback_chapter_counter += 1
            current_chapter_id = ensure_chapter(f"Chapter {fallback_chapter_counter}", _make_summary(paragraph_lines[0]))

        if current_section_id is None:
            current_section_id = ensure_section("Overview", current_chapter_id, _make_summary(body_text))

        paragraph_label = _make_summary(paragraph_lines[0], limit=60) or f"Paragraph {paragraph_fallback_index}"
        add_paragraph(paragraph_label, current_section_id, body_text)
        paragraph_lines.clear()

    paragraph_fallback_index = 0

    for chunk in chunks:
        if not chunk.strip():
            continue

        lines = [line.strip() for line in chunk.split("\n") if line.strip()]
        if not lines:
            continue

        paragraph_lines: List[str] = []

        for line in lines:
            normalized = _normalize_title_line(line)
            chapter_title = _detect_chapter_title(normalized)
            section_title = None if chapter_title else _detect_section_title(normalized)

            if chapter_title:
                flush_paragraph_buffer(paragraph_lines, paragraph_fallback_index)
                paragraph_fallback_index += 1
                chapter_prefix, chapter_label = chapter_title
                chapter_label = chapter_label or chapter_prefix
                current_chapter_id = ensure_chapter(chapter_label, _make_summary(line))
                current_section_id = None
                continue

            if section_title:
                flush_paragraph_buffer(paragraph_lines, paragraph_fallback_index)
                paragraph_fallback_index += 1
                if current_chapter_id == root_id:
                    fallback_chapter_counter += 1
                    current_chapter_id = ensure_chapter(f"Chapter {fallback_chapter_counter}", _make_summary(line))
                section_prefix, section_label = section_title
                section_label = section_label or section_prefix
                current_section_id = ensure_section(section_label, current_chapter_id, _make_summary(line))
                continue

            paragraph_lines.append(line)

        flush_paragraph_buffer(paragraph_lines, paragraph_fallback_index)
        paragraph_fallback_index += 1

    return nodes
