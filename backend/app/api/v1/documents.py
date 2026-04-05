"""文档操作路由 - 处理上传等"""

import asyncio
import sqlite3
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, status

from app.core.config import settings
from app.services.processing_queue import processing_queue
from app.schemas.queue import QueueResponse, QueueItemData
from app.core.exceptions import AppException
from app.schemas.knowledge_tree import KnowledgeTree, KnowledgeNode
from app.services.vector_store import get_connection, get_document_nodes

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_pdf_magic_bytes(file: UploadFile) -> bool:
    pos = file.file.tell()
    file.file.seek(0)
    signature = file.file.read(4)
    file.file.seek(pos)
    return signature == b"%PDF"

def sync_save_file(temp_path: Path, content: bytes):
    """同步阻塞的写文件包装器，给 asyncio.to_thread 调度以释放事件循环"""
    try:
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(content)
    except OSError as e:
        logger.error(f"Failed to write disk for file {temp_path}: {e}")
        raise AppException(
            message="Internal server error: Disk IO failure.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=QueueResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传 PDF 并加入全局单例处理队列"""
    if not settings.embedding_ready:
        raise AppException(
            message="Embedding service unavailable: missing OPENAI_API_KEY",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # 限制 1：校验格式
    if file.content_type != "application/pdf":
        raise AppException(
            message="Only PDF files are allowed",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )

    if not validate_pdf_magic_bytes(file):
        raise AppException(
            message="Invalid PDF file: magic bytes mismatch",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
        
    # 限制 2：校验大小 (Seek 到结尾，获取位置，复位)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise AppException(
            message=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE / (1024*1024):.0f} MB",
            status_code=status.HTTP_413_CONTENT_TOO_LARGE
        )
        
    job_id = str(uuid.uuid4())
    upload_dir = Path(settings.database_path).parent / "uploads"
    temp_path = upload_dir / f"{job_id}.pdf"
    
    try:
        # 读取到内存
        content = await file.read()
        
        # 将阻塞磁盘 IO 移交独立线程
        await asyncio.to_thread(sync_save_file, temp_path, content)
            
        # 打包进内存队列 + DB SQLite 事实源
        position = await processing_queue.enqueue(job_id=job_id, file_path=str(temp_path))
        
        return QueueResponse(
            data=QueueItemData(
                job_id=job_id,
                status="queued",
                position=position
            ),
            message="File accepted and queued for processing"
        )
    except Exception as e:
        # 错误清理，应对 Client Disconnect 等不可期异常产生的孤儿垃圾
        logger.error(f"Upload failed for job {job_id}: {e}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as inner_e:
                logger.error(f"Failed to clean up isolated stub file {temp_path}: {inner_e}")
                
        if isinstance(e, AppException):
            raise e
        raise AppException("Internal error while processing upload.", status_code=500)


@router.get("/upload/{job_id}", status_code=status.HTTP_200_OK, response_model=QueueResponse)
async def get_document_status(job_id: str):
    """轮询任务状态 (支持 AC 5 排位降级机制)"""
    status_str, pos = await processing_queue.get_status(job_id)
    
    if status_str == "not_found":
        raise AppException(
            message="Job ID not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )
        
    msg = "Job is queued" if status_str == "queued" else f"Job is {status_str}"
    
    return QueueResponse(
        data=QueueItemData(
            job_id=job_id,
            status=status_str,
            position=pos
        ),
        message=msg
    )

@router.get("/{document_id}/tree", status_code=status.HTTP_200_OK, response_model=KnowledgeTree)
async def get_document_tree(document_id: int):
    """获取文档的层级知识树 (用于前端图谱渲染与边界选圈)"""
    def fetch_tree(doc_id: int):
        conn = get_connection()
        try:
            return get_document_nodes(conn, doc_id)
        finally:
            conn.close()
            
    try:
        nodes_rows = await asyncio.to_thread(fetch_tree, document_id)
        
        # Schema matching check: make sure empty lists are correctly returned instead of 404
        if not nodes_rows:
            return KnowledgeTree(document_id=document_id, nodes=[], total_nodes=0)
            
        nodes_dict_list = [dict(row) for row in nodes_rows]
        nodes = [KnowledgeNode(**nd) for nd in nodes_dict_list]
        return KnowledgeTree(
            document_id=document_id,
            nodes=nodes,
            total_nodes=len(nodes)
        )
    except sqlite3.OperationalError as e:
        if "no such table: knowledge_nodes" in str(e):
            return KnowledgeTree(document_id=document_id, nodes=[], total_nodes=0)
        logger.error(f"Failed to fetch tree for document {document_id}: {e}")
        raise AppException("Internal error while fetching knowledge tree.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Failed to fetch tree for document {document_id}: {e}")
        raise AppException("Internal error while fetching knowledge tree.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
