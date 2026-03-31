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
