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
    # sqlite-vec can parse JSON arrays into float vectors via cast
    conn.executemany(
        """
        INSERT INTO vec_embeddings(node_id, embedding) 
        VALUES (?, cast(? as float[1536]))
        """,
        [(node_id, json.dumps(vec)) for node_id, vec in embeddings_data]
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
