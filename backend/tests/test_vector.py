"""sqlite-vec 向量功能验证测试

证明 C 扩展在宿主机上稳定工作，
包括向量插入、余弦相似度检索等核心操作。
"""

import sqlite3
import struct
import os
import tempfile

import pytest
import sqlite_vec


def _serialize_float32(vector: list[float]) -> bytes:
    """将 Python float 列表序列化为 sqlite-vec 需要的二进制格式"""
    return struct.pack(f"{len(vector)}f", *vector)


@pytest.fixture
def vec_conn():
    """创建一个临时的内存数据库连接并加载 sqlite-vec"""
    conn = sqlite3.connect(":memory:")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


class TestSqliteVecExtension:
    """验证 sqlite-vec C 扩展基础功能"""

    def test_extension_loads_successfully(self, vec_conn):
        """验证 sqlite-vec 扩展能够成功加载"""
        # 如果能走到这里，说明扩展加载成功
        result = vec_conn.execute("SELECT vec_version()").fetchone()
        assert result is not None
        assert len(result[0]) > 0  # 版本字符串非空

    def test_vec_version_is_string(self, vec_conn):
        """验证版本函数返回合法字符串"""
        version = vec_conn.execute("SELECT vec_version()").fetchone()[0]
        # 版本号格式: X.Y.Z
        parts = version.split(".")
        assert len(parts) >= 2

    def test_create_virtual_table(self, vec_conn):
        """验证能创建向量虚拟表"""
        vec_conn.execute("""
            CREATE VIRTUAL TABLE test_vectors USING vec0(
                id TEXT PRIMARY KEY,
                embedding float[4]
            );
        """)
        # 如果没有抛出异常即通过
        assert True


class TestVectorSimilarity:
    """验证向量相似度检索核心功能"""

    @pytest.fixture(autouse=True)
    def setup_table(self, vec_conn):
        """每个测试前创建并填充测试向量表"""
        self.conn = vec_conn
        self.conn.execute("""
            CREATE VIRTUAL TABLE test_vecs USING vec0(
                id TEXT PRIMARY KEY,
                embedding float[4]
            );
        """)

        # 插入测试向量
        test_data = [
            ("vec_a", [1.0, 0.0, 0.0, 0.0]),
            ("vec_b", [0.0, 1.0, 0.0, 0.0]),
            ("vec_c", [0.9, 0.1, 0.0, 0.0]),  # 与 vec_a 高度相似
            ("vec_d", [0.0, 0.0, 1.0, 0.0]),
        ]
        for vec_id, embedding in test_data:
            self.conn.execute(
                "INSERT INTO test_vecs(id, embedding) VALUES (?, ?)",
                (vec_id, _serialize_float32(embedding)),
            )

    def test_vector_insert_and_count(self):
        """验证向量能正确插入并统计"""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM test_vecs"
        ).fetchone()[0]
        assert count == 4

    def test_knn_similarity_search(self):
        """验证 K 近邻相似度检索返回最近的向量"""
        query_vec = _serialize_float32([1.0, 0.0, 0.0, 0.0])

        results = self.conn.execute(
            """
            SELECT id, distance
            FROM test_vecs
            WHERE embedding MATCH ? AND k = 3
            ORDER BY distance
            """,
            (query_vec,),
        ).fetchall()

        assert len(results) == 3
        # 与 query [1,0,0,0] 最近的应该是 vec_a（完全匹配）
        assert results[0][0] == "vec_a"
        assert results[0][1] == pytest.approx(0.0, abs=1e-6)

    def test_similarity_ranking_order(self):
        """验证相似度排序正确性：vec_a > vec_c > vec_b/vec_d"""
        query_vec = _serialize_float32([1.0, 0.0, 0.0, 0.0])

        results = self.conn.execute(
            """
            SELECT id, distance
            FROM test_vecs
            WHERE embedding MATCH ? AND k = 4
            ORDER BY distance
            """,
            (query_vec,),
        ).fetchall()

        ids = [r[0] for r in results]
        # vec_a 应排第一（完全匹配），vec_c 应排第二（高度相似）
        assert ids[0] == "vec_a"
        assert ids[1] == "vec_c"


class TestVectorStoreService:
    """验证 vector_store 服务层功能"""

    def test_get_connection_with_custom_path(self):
        """验证自定义路径创建连接"""
        from app.services.vector_store import get_connection

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            conn = get_connection(db_path)

            # 验证 sqlite-vec 已加载
            version = conn.execute("SELECT vec_version()").fetchone()[0]
            assert version is not None

            conn.close()

    def test_init_db_creates_tables(self):
        """验证 init_db 正确创建所有必要表"""
        from app.services.vector_store import get_connection, init_db

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            conn = get_connection(db_path)
            init_db(conn)

            # 验证 knowledge_nodes 表存在
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_nodes'"
            ).fetchone()
            assert result is not None

            # 验证 documents 表存在
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
            ).fetchone()
            assert result is not None

            # 验证 vec_embeddings 虚拟表存在
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vec_embeddings'"
            ).fetchone()
            assert result is not None

            # 验证 review 相关表存在
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_attempts'"
            ).fetchone()
            assert result is not None

            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='question_history'"
            ).fetchone()
            assert result is not None

            conn.close()
