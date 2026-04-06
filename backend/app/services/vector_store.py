"""SQLite + sqlite-vec 向量存储交互层

提供极轻量级的本地向量检索功能，零额外进程开销，
完全适配 2C2G 服务器环境。
"""

import sqlite3
from pathlib import Path
from typing import Optional

import sqlite_vec

from app.core.config import settings


def get_db_path() -> str:
    """获取数据库文件的绝对路径"""
    db_path = Path(settings.database_path)
    # 确保数据目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """创建并返回一个已加载 sqlite-vec 扩展的 SQLite 连接

    Args:
        db_path: 可选的自定义数据库路径，默认使用配置中的路径

    Returns:
        已配置好 WAL 模式和 sqlite-vec 扩展的连接对象
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    # 启用 WAL 模式以提升并发性能
    conn.execute("PRAGMA journal_mode=WAL;")

    # 加载 sqlite-vec C 扩展
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    return conn


def init_db(conn: Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
    """初始化数据库表结构

    Args:
        conn: 可选的已有连接。如未提供，将创建新连接。

    Returns:
        已初始化表结构的数据库连接
    """
    if conn is None:
        conn = get_connection()

    # 知识节点关系表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            node_id TEXT PRIMARY KEY,
            document_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            parent_id TEXT,
            content_summary TEXT NOT NULL,
            depth INTEGER DEFAULT 0,
            chunk_text TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );
    """)

    # 文档元信息表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_nodes INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );
    """)

    # Backward-compatible migrations for documents table
    doc_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(documents)").fetchall()
    }
    if "file_hash" not in doc_columns:
        conn.execute("ALTER TABLE documents ADD COLUMN file_hash TEXT")
    if "source_job_id" not in doc_columns:
        conn.execute("ALTER TABLE documents ADD COLUMN source_job_id TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_file_hash_status "
        "ON documents(file_hash, status, updated_at)"
    )

    # 文档处理队列任务表 (Single Source of Truth)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_tasks (
            job_id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            status INTEGER DEFAULT 0, -- 0: queued, 1: processing, 2: done, -1: error
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Backward-compatible migrations for existing DB files
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(document_tasks)").fetchall()
    }
    if "error_message" not in columns:
        conn.execute("ALTER TABLE document_tasks ADD COLUMN error_message TEXT")
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE document_tasks ADD COLUMN updated_at TIMESTAMP")
        conn.execute(
            "UPDATE document_tasks SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
        )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_tasks_status_updated_at "
        "ON document_tasks(status, updated_at)"
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS question_review_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            review_reason TEXT NOT NULL,
            needs_review INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(thread_id, node_id)
        );
    """)

    from app.services.review_service import init_review_tables

    init_review_tables(conn)

    # 向量嵌入虚拟表（使用 sqlite-vec）
    # 维度 1536 是 OpenAI text-embedding-3-small 的默认输出维度
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_embeddings USING vec0(
            node_id TEXT PRIMARY KEY,
            embedding float[1536]
        );
    """)

    conn.commit()
    return conn


def mark_node_needs_review(thread_id: str, node_id: str, review_reason: str) -> None:
    """Persist skip/guardrail review flag for Epic 3 handoff."""
    if not thread_id or not node_id:
        return

    conn = get_connection()
    try:
        init_db(conn)
        conn.execute(
            """
            INSERT INTO question_review_flags(thread_id, node_id, review_reason, needs_review)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(thread_id, node_id)
            DO UPDATE SET
                review_reason = excluded.review_reason,
                needs_review = 1
            """,
            (thread_id, node_id, review_reason or "user_skipped_after_guardrail"),
        )
        conn.commit()
    finally:
        conn.close()

def insert_document_nodes(conn: sqlite3.Connection, nodes: list) -> None:
    """批量插入知识节点和向量嵌入"""
    # Inserting into knowledge_nodes
    conn.executemany(
        """
        INSERT INTO knowledge_nodes 
        (node_id, document_id, label, parent_id, content_summary, depth, chunk_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                n.node_id, 
                n.document_id, 
                n.label, 
                n.parent_id, 
                n.content_summary, 
                n.depth, 
                n.chunk_text
            ) for n in nodes
        ]
    )

    # Note: sqlite-vec accepts raw json arrays or byte blobs. 
    # The embeddings are assigned later in process_and_store via a separate function 
    # or inserted together if already generated. We'll handle inserting the structural records here.
    conn.commit()

def insert_embeddings(conn: sqlite3.Connection, embeddings_data: list[tuple[str, list[float]]]) -> None:
    """批量插入向量嵌入到虚拟表 vec_embeddings
    
    Args:
        embeddings_data: list of tuples (node_id, embedding_vector)
    """
    import json

    normalized_rows: list[tuple[str, str]] = []
    for node_id, vec in embeddings_data:
        # Some providers may return wrapper objects or non-list sequences.
        # Normalize to a plain JSON float array that sqlite-vec accepts.
        if isinstance(vec, dict) and "embedding" in vec:
            vec = vec["embedding"]

        if not isinstance(vec, (list, tuple)):
            raise ValueError(
                f"Invalid embedding payload for node_id={node_id}: expected list/tuple, got {type(vec).__name__}"
            )

        normalized_vec = [float(x) for x in vec]
        normalized_rows.append((node_id, json.dumps(normalized_vec, ensure_ascii=False, separators=(",", ":"))))

    # sqlite-vec supports TEXT JSON arrays directly for vector columns.
    conn.executemany(
        """
        INSERT INTO vec_embeddings(node_id, embedding)
        VALUES (?, ?)
        """,
        normalized_rows,
    )
    conn.commit()

def get_document_nodes(conn: sqlite3.Connection, document_id: int) -> list[sqlite3.Row]:
    """Retrieve all knowledge nodes for a given document."""
    cursor = conn.execute(
        """
        SELECT node_id, label, parent_id, content_summary
        FROM knowledge_nodes
        WHERE document_id = ?
        ORDER BY depth, node_id
        """,
        (document_id,)
    )
    return cursor.fetchall()


def get_recent_document_ids(conn: sqlite3.Connection, limit: int = 10) -> list[int]:
    """Return recent document IDs that actually have extracted nodes."""
    cursor = conn.execute(
        """
        SELECT document_id
        FROM knowledge_nodes
        GROUP BY document_id
        ORDER BY MAX(created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [int(row[0]) for row in cursor.fetchall()]


def find_existing_document_by_hash(conn: sqlite3.Connection, file_hash: str) -> int | None:
    """Find latest completed document id by file hash for soft de-duplication."""
    row = conn.execute(
        """
        SELECT id
        FROM documents
        WHERE file_hash = ?
          AND status = 'done'
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (file_hash,),
    ).fetchone()
    if not row:
        return None
    return int(row[0])


def get_descendant_node_ids(conn: sqlite3.Connection, node_ids: list[str]) -> list[str]:
    """获取给定节点及其所有后代节点的 ID
    
    实现层级展开逻辑：选择父节点时包含所有子节点。
    
    Args:
        conn: SQLite 连接
        node_ids: 初始选择的节点 ID 列表
        
    Returns:
        包含所有后代节点的 ID 列表（包括原始节点）
    """
    if not node_ids:
        return []
    
    # 使用递归 CTE 获取所有后代节点
    placeholders = ", ".join("?" * len(node_ids))
    query = f"""
        WITH RECURSIVE descendants AS (
            -- 基础：选中的节点
            SELECT node_id FROM knowledge_nodes WHERE node_id IN ({placeholders})
            
            UNION ALL
            
            -- 递归：子节点
            SELECT kn.node_id
            FROM knowledge_nodes kn
            INNER JOIN descendants d ON kn.parent_id = d.node_id
        )
        SELECT DISTINCT node_id FROM descendants
    """
    
    cursor = conn.execute(query, node_ids)
    return [row[0] for row in cursor.fetchall()]


def retrieve_by_nodes(
    node_ids: list[str],
    top_k: int = 5,
    conn: sqlite3.Connection | None = None
) -> list[dict]:
    """根据节点 ID 列表检索相关文本块
    
    实现上下文边界 RAG 检索：
    1. 展开选定节点到所有后代节点
    2. 获取这些节点的 chunk_text
    3. 返回相关内容（按节点深度排序）
    
    Args:
        node_ids: 用户选择的知识节点 ID 列表
        top_k: 返回的最大 chunk 数量（默认 5，内存安全）
        conn: 可选的数据库连接
        
    Returns:
        检索到的文本块列表，每项包含:
        - node_id: 节点 ID
        - chunk_text: 文本内容
        - label: 节点标签
        - depth: 节点深度
        - score: 相关性分数（当前为基于深度的排序分数）
    """
    if not node_ids:
        return []
    
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    
    try:
        # 1. 展开到所有后代节点
        expanded_node_ids = get_descendant_node_ids(conn, node_ids)
        
        if not expanded_node_ids:
            return []
        
        # 2. 查询节点的 chunk_text
        placeholders = ", ".join("?" * len(expanded_node_ids))
        query = f"""
            SELECT node_id, chunk_text, label, depth
            FROM knowledge_nodes
            WHERE node_id IN ({placeholders})
            AND chunk_text IS NOT NULL
            AND chunk_text != ''
            ORDER BY depth ASC, node_id ASC
            LIMIT ?
        """
        
        cursor = conn.execute(query, expanded_node_ids + [top_k])
        rows = cursor.fetchall()
        
        # 3. 构建返回结果
        results = []
        for i, row in enumerate(rows):
            results.append({
                "node_id": row["node_id"],
                "chunk_text": row["chunk_text"],
                "label": row["label"],
                "depth": row["depth"],
                "score": 1.0 - (i * 0.1)  # 简单的排序分数
            })
        
        return results
        
    finally:
        if should_close:
            conn.close()


def retrieve_by_nodes_semantic(
    node_ids: list[str],
    query_embedding: list[float],
    top_k: int = 5,
    conn: sqlite3.Connection | None = None
) -> list[dict]:
    """按选中节点边界做向量相似度检索。

    说明：
    - 先做层级展开，限定 node_id 范围；
    - 再在 vec_embeddings 中按距离排序；
    - 最后联表返回 chunk_text。
    """
    import json

    if not node_ids:
        return []
    if not query_embedding:
        return []

    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        expanded_node_ids = get_descendant_node_ids(conn, node_ids)
        if not expanded_node_ids:
            return []

        placeholders = ", ".join("?" * len(expanded_node_ids))
        query = f"""
            SELECT
                kn.node_id,
                kn.chunk_text,
                kn.label,
                kn.depth,
                ve.distance AS score
            FROM vec_embeddings ve
            JOIN knowledge_nodes kn ON kn.node_id = ve.node_id
            WHERE kn.node_id IN ({placeholders})
              AND kn.chunk_text IS NOT NULL
              AND kn.chunk_text != ''
              AND ve.embedding MATCH cast(? as float[1536])
            ORDER BY ve.distance ASC
            LIMIT ?
        """
        params = expanded_node_ids + [json.dumps(query_embedding), top_k]
        rows = conn.execute(query, params).fetchall()

        return [
            {
                "node_id": row["node_id"],
                "chunk_text": row["chunk_text"],
                "label": row["label"],
                "depth": row["depth"],
                "score": float(row["score"]) if row["score"] is not None else None,
            }
            for row in rows
        ]
    finally:
        if should_close:
            conn.close()
