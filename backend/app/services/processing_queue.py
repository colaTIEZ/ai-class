"""处理队列服务 - 由 SQLite 支撑的单例队列保护机制"""

import asyncio
import logging
from typing import Optional, Dict, Tuple
from app.services.vector_store import get_connection

logger = logging.getLogger(__name__)

class ProcessingQueue:
    """全局单例保护任务异步队列实现 (基于 SQLite 的单一事实源)"""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ProcessingQueue, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization 
        if not hasattr(self, "initialized"):
            self.queue = asyncio.Queue()
            self.worker_task: Optional[asyncio.Task] = None
            self.initialized = True

    def _get_queue_position(self, job_id: str, conn) -> int:
        """从 SQLite 中快速查询某任务当前的排队次序 (1-indexed)"""
        # Finds how many tasks are queued before or at the same time as this one
        row = conn.execute(
            "SELECT created_at FROM document_tasks WHERE job_id = ?", 
            (job_id,)
        ).fetchone()
        
        if not row:
            return 1
            
        created_at = row["created_at"]
        count_row = conn.execute(
            "SELECT count(job_id) as pos FROM document_tasks WHERE status = 0 AND created_at <= ? ORDER BY created_at ASC",
            (created_at,)
        ).fetchone()
        
        return count_row["pos"] if count_row else 1

    async def enqueue(self, job_id: str, file_path: str) -> int:
        """任务打包排队，写入 DB 并返回当前排位次"""
        def _db_insert():
            # statuses: 0=queued, 1=processing, 2=done, -1=error
            conn = get_connection()
            try:
                conn.execute(
                    "INSERT INTO document_tasks (job_id, file_path, status) VALUES (?, ?, 0)",
                    (job_id, file_path)
                )
                conn.commit()
                return self._get_queue_position(job_id, conn)
            finally:
                conn.close()
                pass
                
        position = await asyncio.to_thread(_db_insert)
        await self.queue.put(job_id)
        return position

    async def get_status(self, job_id: str) -> Tuple[str, int]:
        """查询任务状态与排位"""
        def _db_query():
            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT status FROM document_tasks WHERE job_id = ?",
                    (job_id,)
                ).fetchone()
                if not row:
                    return ("not_found", 0)
                
                status_code = row["status"]
                status_map = {0: "queued", 1: "processing", 2: "done", -1: "error"}
                status_str = status_map.get(status_code, "unknown")
                
                pos = 0
                if status_code == 0:
                    pos = self._get_queue_position(job_id, conn)
                return (status_str, pos)
            finally:
                conn.close()
                
        return await asyncio.to_thread(_db_query)

    async def _worker(self):
        """异步工人循环"""
        logger.info("Processing worker started - max singleton limit 1")
        
        def _update_status(j_id: str, new_status: int):
            conn = get_connection()
            try:
                conn.execute("UPDATE document_tasks SET status = ? WHERE job_id = ?", (new_status, j_id))
                conn.commit()
            finally:
                conn.close()
                
        while True:
            try:
                job_id = await self.queue.get()
                
                await asyncio.to_thread(_update_status, job_id, 1) # processing
                logger.info(f"Processing job {job_id}")
                
                # Real Document Processing logic starts here
                from app.services.pdf_parser import process_pdf_generator, extract_hierarchy, generate_embeddings
                from app.services.vector_store import insert_document_nodes, insert_embeddings, get_connection
                
                def _process_file(j_id):
                    # Fetch file_path
                    conn = get_connection()
                    try:
                        row = conn.execute("SELECT file_path FROM document_tasks WHERE job_id = ?", (j_id,)).fetchone()
                        if not row:
                            raise ValueError(f"Job {j_id} not found")
                        fp = row["file_path"]
                        # Fix: avoid hash collisions for doc_id mapping
                        # Use first 8 characters of UUID hex as a safe integer ID for documents table referencing
                        doc_id = int(j_id.replace('-', '')[:8], 16)
                        
                        chunks = list(process_pdf_generator(fp))
                        if not chunks:
                             logger.warning(f"Job {j_id}: PDF produced no text chunks.")
                             nodes = []
                        else:
                             nodes = extract_hierarchy(doc_id, chunks)
                        
                        # Database insertion in a transaction
                        # Step 1: Save hierarchical structural relational nodes
                        insert_document_nodes(conn, nodes)
                        
                        # Step 2: Batch process Embeddings to avoid rate limits
                        batch_size = 50
                        for i in range(0, len(nodes), batch_size):
                            batch = nodes[i:i+batch_size]
                            embeddings_data = generate_embeddings(batch)
                            insert_embeddings(conn, embeddings_data)
                            
                    finally:
                        conn.close()

                # Execute synchronous heavy extraction in a separate thread securely
                await asyncio.to_thread(_process_file, job_id)
                
                await asyncio.to_thread(_update_status, job_id, 2) # done
                logger.info(f"Finished job {job_id}")
                self.queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Worker task cancelled cleanly")
                break
            except BaseException as e:
                # Catching BaseException as requested by patch finding
                logger.error(f"Error processing job {job_id}: {e}")
                try:
                    await asyncio.to_thread(_update_status, job_id, -1) # error
                    self.queue.task_done()
                except Exception as inner_e:
                    logger.error(f"Failed to update error status for {job_id}: {inner_e}")

    def start_worker(self):
        """如果不存在就启动工作循环，并处理残留任务"""
        def _recover_tasks():
            conn = get_connection()
            try:
                # Reset interrupted processing tasks to queued
                conn.execute("UPDATE document_tasks SET status = 0 WHERE status = 1")
                conn.commit()
                # Get all queued tasks ordered by creation time
                rows = conn.execute("SELECT job_id FROM document_tasks WHERE status = 0 ORDER BY created_at ASC").fetchall()
                for row in rows:
                    self.queue.put_nowait(row["job_id"])
            except Exception as e:
                logger.error(f"Error recovering tasks: {e}")
            finally:
                conn.close()
        
        # We need to initialize the db structure first, preventing race condition
        from app.services.vector_store import init_db
        init_db()

        if self.worker_task is None or self.worker_task.done():
            _recover_tasks()
            self.worker_task = asyncio.create_task(self._worker())

    async def stop_worker(self):
        """清理并且终结正在阻塞的工人"""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            
# 全局单例共享
processing_queue = ProcessingQueue()
