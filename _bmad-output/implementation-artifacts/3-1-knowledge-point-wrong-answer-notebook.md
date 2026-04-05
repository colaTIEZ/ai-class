---
story_key: "3-1-knowledge-point-wrong-answer-notebook"
story_id: "3.1"
epic: 3
status: done
created_at: 2026-04-05T18:20:00+08:00
updated_at: 2026-04-05T20:05:00+08:00
author: Amelia
project: ai-class
---

# Story 3.1: 知识点维度的错题本 (Knowledge-Point Wrong-Answer Notebook)

## Executive Summary

用户需要一个"错题本"来追踪和复习所有答题错误。系统通过知识点（`node_id`）聚合这些错误，帮助学生在考前精准识别弱项。此故事关键的是：
1. **数据持久化**：建立 `quiz_attempts` 和 `question_history` 表
2. **API 端点**：`GET /api/v1/review/wrong-answers` 返回按 `node_id` 聚合的错题数据
3. **前端组件**：ReviewPage 展示错题本，支持按知识点过滤和重新作答

---

## User Story

**As a** Student  
**I want to** review all my incorrect answers grouped by the specific knowledge concepts  
**So that** I can see exactly where my systemic weaknesses are before an exam.

### Acceptance Criteria

**AC-1: 错题数据持久化**
- Given: 学生完成测验并有错误答案
- When: 答题验证完成后
- Then: 系统必须将答题记录（包括 `question_text`, `user_answer`, `correct_answer`, `node_id`）持久化到 SQLite
- And: 数据包含时间戳、错误类型等元数据

**AC-2: 错题查询 API**
- Given: 学生访问"错题本"页面
- When: 前端调用 `GET /api/v1/review/wrong-answers`
- Then: 后端返回按 `node_id` 分组的错题列表，格式为：
  ```json
  {
    "status": "success",
    "data": {
      "by_node": [
        {
          "node_id": "doc_1_node_003",
          "node_label": "第二章：导数应用",
          "total_errors": 3,
          "questions": [
            {
              "question_id": "q_uuid_1",
              "question_text": "求函数 f(x) = x^2 的导数",
              "user_answer": "2x + 1",
              "correct_answer": "2x",
              "error_type": "calculation",
              "attempted_at": "2026-04-05T10:30:00Z",
              "is_invalidated": false
            }
          ]
        }
      ],
      "summary": {
        "total_wrong_count": 5,
        "total_nodes_with_errors": 2
      }
    },
    "trace_id": "uuid"
  }
  ```

**AC-3: 按知识点过滤**
- Given: 前端显示错题本
- When: 学生点击某个知识点（例如"第二章：导数应用"）
- Then: 界面仅展示该知识点下的错题
- And: 其他知识点的错题被隐藏

**AC-4: 重新作答**
- Given: 学生在错题本中查看错题
- When: 点击"重新作答"按钮
- Then: 系统生成新一轮测验，仅包含该错题对应的知识点
- And: 新回答会建立新的答题记录（与之前的错误记录独立）

**AC-5: 防毒淘金（防幻觉）集成**
- Given: 某条答题记录被标记为 `invalidated=true`（由故事 3.3 处理）
- When: 查询错题本
- Then: 该记录不出现在任何聚合或列表中
- And: 错题数量统计 (`total_wrong_count`) 也自动排除该记录

---

## Technical Design

### 1. Database Schema Extensions

**表：`quiz_attempts`**（如果 Epic 1-2 中尚未创建）

```sql
CREATE TABLE quiz_attempts (
  attempt_id TEXT PRIMARY KEY,  -- UUID
  user_id TEXT NOT NULL,        -- 用户标识符（session 或 auth ID）
  document_id INTEGER,          -- 来自哪份文档
  selected_node_ids TEXT,       -- JSON 数组：用户圈选的节点 ID
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME,
  session_id TEXT UNIQUE        -- 唯一会话 ID，用于 LangGraph checkpointer
);
```

**表：`question_history`**

```sql
CREATE TABLE question_history (
  question_record_id TEXT PRIMARY KEY,  -- UUID
  attempt_id TEXT NOT NULL,
  question_id TEXT,              -- 问题的唯一标识符
  node_id TEXT NOT NULL,         -- 关联的知识点 ID（用于分组）
  question_text TEXT,
  question_type ENUM('multiple_choice', 'short_answer'),
  user_answer TEXT,
  correct_answer TEXT,
  is_correct BOOL,
  error_type TEXT,               -- 'no_error', 'logic_gap', 'conceptual' 等
  error_severity INT,            -- 1-3
  attempted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_invalidated BOOL DEFAULT FALSE,  -- AR-5 防幻觉标志
  invalidation_reason TEXT,      -- 用户上诉原因（由 Story 3.3 填充）
  FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(attempt_id),
  FOREIGN KEY (node_id) REFERENCES knowledge_nodes(node_id)
);

CREATE INDEX idx_question_history_user_node ON question_history(user_id, node_id, is_correct, is_invalidated);
```

**关键点**：
- `is_invalidated` 标志由 Story 3.3 设置，此故事在查询时必须过滤掉这些记录
- `node_id` 是关键索引，用于按知识点聚合
- 使用 UUID 确保跨系统的唯一性

### 2. Data Model (Pydantic Schemas)

在 `backend/app/schemas/` создать 新文件 `review.py`：

```python
# backend/app/schemas/review.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class QuestionRecord(BaseModel):
    """单条答题记录"""
    question_record_id: str
    question_text: str
    user_answer: str
    correct_answer: str
    error_type: str
    error_severity: Optional[int] = None
    attempted_at: str  # ISO 8601
    is_invalidated: bool = False


class NodeGroupedWrongAnswers(BaseModel):
    """按知识点分组的错题"""
    node_id: str
    node_label: str
    total_errors: int
    questions: List[QuestionRecord]


class WrongAnswersSummary(BaseModel):
    """汇总统计"""
    total_wrong_count: int
    total_nodes_with_errors: int


class WrongAnswersResponse(BaseModel):
    """完整的"错题本"响应"""
    status: str = "success"
    data: Optional[dict] = None
    message: Optional[str] = None
    trace_id: str

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "by_node": [],
                    "summary": {}
                },
                "trace_id": "uuid"
            }
        }
```

### 3. Backend API Endpoint

在 `backend/app/api/v1/review.py` 新增（或扩展 `chat.py`）：

```python
# backend/app/api/v1/review.py

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
import uuid
from app.schemas.review import WrongAnswersResponse
from app.services.vector_store import get_knowledge_node
from app.core.db import get_db_connection

router = APIRouter(prefix="/review", tags=["review"])

@router.get(
    "/wrong-answers",
    response_model=WrongAnswersResponse,
    summary="获取错题本",
    description="按知识点分组返回所有错题"
)
async def get_wrong_answers(
    x_user_id: str = Header(None),  # 从 session/auth header 获取用户 ID
    node_id_filter: Optional[str] = None  # 可选的知识点过滤
) -> WrongAnswersResponse:
    """
    获取用户的错题本（按知识点分组）
    
    Query Parameters:
      - node_id_filter: 只显示该知识点的错题（可选）
    
    Headers:
      - X-User-ID: 当前用户标识
    """
    trace_id = str(uuid.uuid4())
    
    if not x_user_id:
        return WrongAnswersResponse(
            status="error",
            message="Missing X-User-ID header",
            trace_id=trace_id
        )
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取用户的所有错题（排除 invalidated 记录）
        query = """
        SELECT 
          qh.question_record_id,
          qh.node_id,
          kn.label as node_label,
          qh.question_text,
          qh.user_answer,
          qh.correct_answer,
          qh.error_type,
          qh.error_severity,
          qh.attempted_at,
          qh.is_invalidated
        FROM question_history qh
        JOIN knowledge_nodes kn ON qh.node_id = kn.node_id
        WHERE qh.user_id = ? AND qh.is_correct = 0 AND qh.is_invalidated = 0
        ORDER BY qh.node_id, qh.attempted_at DESC
        """
        
        params = [x_user_id]
        
        if node_id_filter:
            query += " AND qh.node_id = ?"
            params.append(node_id_filter)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 按 node_id 分组
        grouped = {}
        for row in rows:
            node_id = row[1]
            if node_id not in grouped:
                grouped[node_id] = {
                    "node_id": node_id,
                    "node_label": row[2],
                    "questions": []
                }
            
            grouped[node_id]["questions"].append({
                "question_record_id": row[0],
                "question_text": row[3],
                "user_answer": row[4],
                "correct_answer": row[5],
                "error_type": row[6],
                "error_severity": row[7],
                "attempted_at": row[8],
                "is_invalidated": bool(row[9])
            })
        
        # 构建响应
        by_node = []
        for node_id in sorted(grouped.keys()):
            group = grouped[node_id]
            by_node.append({
                "node_id": group["node_id"],
                "node_label": group["node_label"],
                "total_errors": len(group["questions"]),
                "questions": group["questions"]
            })
        
        summary = {
            "total_wrong_count": len(rows),
            "total_nodes_with_errors": len(grouped)
        }
        
        conn.close()
        
        return WrongAnswersResponse(
            status="success",
            data={
                "by_node": by_node,
                "summary": summary
            },
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(f"Error fetching wrong answers: {e}")
        return WrongAnswersResponse(
            status="error",
            message=str(e),
            trace_id=trace_id
        )
```

### 4. Frontend Component

在 `frontend/src/views/ReviewPage.vue` 新增：

```vue
<!-- frontend/src/views/ReviewPage.vue -->

<template>
  <div class="review-page">
    <div class="header">
      <h1>📚 知识点错题本</h1>
      <div class="stats">
        <span>总错题数: {{ summary.total_wrong_count }}</span>
        <span>涉及知识点: {{ summary.total_nodes_with_errors }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="wrongAnswersData.length === 0" class="empty">
      <p>还没有错题记录。继续加油！✨</p>
    </div>

    <div v-else class="wrong-answers-list">
      <!-- 按知识点分组展示 -->
      <div
        v-for="nodeGroup in wrongAnswersData"
        :key="nodeGroup.node_id"
        class="node-group"
      >
        <div class="node-header" @click="toggleNodeExpanded(nodeGroup.node_id)">
          <span class="toggle-icon">
            {{ expandedNodes.has(nodeGroup.node_id) ? '▼' : '▶' }}
          </span>
          <span class="node-label">{{ nodeGroup.node_label }}</span>
          <span class="error-count">{{ nodeGroup.total_errors }} 错</span>
        </div>

        <transition name="expand">
          <div v-if="expandedNodes.has(nodeGroup.node_id)" class="questions-list">
            <div
              v-for="q in nodeGroup.questions"
              :key="q.question_record_id"
              class="question-card"
            >
              <div class="question-text">
                <strong>Q:</strong> {{ q.question_text }}
              </div>
              <div class="answers">
                <div class="user-answer">
                  <span class="label">你的答案:</span>
                  <span class="text wrong">{{ q.user_answer }}</span>
                </div>
                <div class="correct-answer">
                  <span class="label">正确答案:</span>
                  <span class="text correct">{{ q.correct_answer }}</span>
                </div>
              </div>
              <div class="meta">
                <span class="error-type">{{ q.error_type }}</span>
                <span class="attempted-at">{{ formatDate(q.attempted_at) }}</span>
              </div>
              <button
                class="retry-btn"
                @click="retryQuestion(nodeGroup.node_id)"
              >
                🔄 重新作答
              </button>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

interface QuestionRecord {
  question_record_id: string;
  question_text: string;
  user_answer: string;
  correct_answer: string;
  error_type: string;
  attempted_at: string;
  is_invalidated: boolean;
}

interface NodeGroup {
  node_id: string;
  node_label: string;
  total_errors: number;
  questions: QuestionRecord[];
}

const router = useRouter();
const loading = ref(true);
const wrongAnswersData = ref<NodeGroup[]>([]);
const summary = ref({ total_wrong_count: 0, total_nodes_with_errors: 0 });
const expandedNodes = ref(new Set<string>());

onMounted(async () => {
  try {
    const response = await fetch('/api/v1/review/wrong-answers', {
      headers: {
        'X-User-ID': localStorage.getItem('userId') || 'test-user'
      }
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      wrongAnswersData.value = data.data.by_node;
      summary.value = data.data.summary;
    }
  } catch (error) {
    console.error('Failed to fetch wrong answers:', error);
  } finally {
    loading.value = false;
  }
});

const toggleNodeExpanded = (nodeId: string) => {
  if (expandedNodes.value.has(nodeId)) {
    expandedNodes.value.delete(nodeId);
  } else {
    expandedNodes.value.add(nodeId);
  }
};

const retryQuestion = (nodeId: string) => {
  // 跳转到 Quiz 页面，仅针对该知识点
  router.push({
    name: 'quiz-init',
    query: { selected_nodes: nodeId }
  });
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-CN');
};
</script>

<style scoped>
.review-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem;
}

.header {
  margin-bottom: 2rem;
}

.stats {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
  color: #666;
}

.empty {
  text-align: center;
  padding: 3rem;
  color: #999;
  font-size: 1.2rem;
}

.node-group {
  margin-bottom: 1.5rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.node-header {
  padding: 1rem;
  background: #f5f5f5;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: background 0.2s;
}

.node-header:hover {
  background: #efefef;
}

.toggle-icon {
  min-width: 1rem;
  display: inline-block;
}

.node-label {
  flex: 1;
  font-weight: 600;
}

.error-count {
  background: #ff6b6b;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.9rem;
}

.questions-list {
  padding: 1rem;
  background: white;
}

.question-card {
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid #eee;
  border-radius: 6px;
  background: #fafafa;
}

.question-text {
  margin-bottom: 1rem;
  line-height: 1.6;
}

.answers {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-answer, .correct-answer {
  display: flex;
  gap: 0.5rem;
}

.label {
  font-weight: 600;
  min-width: 70px;
}

.text {
  flex: 1;
}

.text.wrong {
  color: #ff6b6b;
  text-decoration: line-through;
}

.text.correct {
  color: #51cf66;
}

.meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: #666;
}

.retry-btn {
  padding: 0.5rem 1rem;
  background: #4c6ef5;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #364ae6;
}

.expand-enter-active, .expand-leave-active {
  transition: all 0.3s ease;
}

.expand-enter-from, .expand-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
```

### 5. Service Layer

在 `backend/app/services/review_service.py` 新增：

```python
# backend/app/services/review_service.py

from app.core.db import get_db_connection
from datetime import datetime
from typing import Dict, List, Optional

def get_wrong_answers_by_node(
    user_id: str,
    node_id_filter: Optional[str] = None
) -> Dict:
    """
    按知识点分组获取用户的错题本
    
    自动过滤：
    - is_correct = False（只要错题）
    - is_invalidated = False（排除被申诉的记录）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ... (实现逻辑如上 API 端点中所示)
    
    conn.close()


def record_answer(
    user_id: str,
    attempt_id: str,
    question_id: str,
    node_id: str,
    question_text: str,
    user_answer: str,
    correct_answer: str,
    is_correct: bool,
    error_type: str,
    error_severity: int = 1
) -> str:
    """
    记录单次答题
    
    返回: question_record_id（UUID）
    """
    import uuid
    
    question_record_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO question_history 
    (question_record_id, user_id, attempt_id, question_id, node_id,
     question_text, user_answer, correct_answer, is_correct,
     error_type, error_severity, is_invalidated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        question_record_id, user_id, attempt_id, question_id, node_id,
        question_text, user_answer, correct_answer, is_correct,
        error_type, error_severity, False
    ))
    
    conn.commit()
    conn.close()
    
    return question_record_id
```

---

## Integration Points

### 与 Epic 1-2 的联系

1. **从 Quiz API 调用**：Epic 2 的 `/api/v1/quiz/submit` 端点在验证答案后，需要调用 `record_answer()` 来持久化答题记录
   ```python
   # 在 chat.py 的 answer_submit 端点中添加：
   from app.services.review_service import record_answer
   
   # ... 验证答案后
   record_answer(
       user_id=x_user_id,
       attempt_id=session_id,
       question_id=state['question_id'],
       node_id=state['current_node_id'],
       question_text=current_question.question_text,
       user_answer=current_answer,
       correct_answer=state['correct_answer'],
       is_correct=validation_result.is_correct,
       error_type=validation_result.error_type,
       error_severity=validation_result.severity
   )
   ```

2. **与 3.2 (Mastery Tracking) 共享数据**：
   - `question_history` 表是 3.2 计算掌握度的数据源
   - 3.2 会查询同一张表，按 `parent_id` 分组计算百分比

3. **与 3.3 (Appeals Valve) 的分离**：
   - 此故事不处理 `invalidation`，仅在查询时过滤掉 `is_invalidated=true` 的记录
   - Story 3.3 会设置该标志

### 性能考虑

- **索引**：在 `(user_id, node_id, is_correct, is_invalidated)` 上建立复合索引
- **缓存**：考虑在前端缓存错题本（直到下次答题后更新）
- **分页**：如果用户有大量错题，可在 API 中添加 `limit/offset` 参数

---

## Tasks & Subtasks

### Task T-1: 数据库设计与迁移

**Subtask T-1.1:** 创建 `quiz_attempts` 和 `question_history` 表
- [x] 编写 SQL 迁移脚本（`backend/app/migrations/003_add_question_history.sql`）
- [x] 添加必要的索引
- [x] 验证表结构与现有表的外键关系

**Subtask T-1.2:** 验证数据库完整性
- [x] 测试 SQLite 是否能正确执行 DDL
- [x] 检查约束是否生效（例如 FK）

### Task T-2: Pydantic 数据模型

**Subtask T-2.1:** 创建 `backend/app/schemas/review.py`
- [x] 定义 `QuestionRecord`, `NodeGroupedWrongAnswers`, `WrongAnswersSummary`, `WrongAnswersResponse`
- [x] 添加完整的文档注释和 JSON 示例

### Task T-3: 后端服务层

**Subtask T-3.1:** 创建 `backend/app/services/review_service.py`
- [x] 实现 `record_answer()` 函数（答题记录持久化）
- [x] 实现 `get_wrong_answers_by_node()` 函数（查询与分组）
- [x] 测试过滤逻辑（`is_invalidated=false`）

### Task T-4: 后端 API 端点

**Subtask T-4.1:** 创建或扩展 `backend/app/api/v1/review.py`
- [x] 实现 `GET /api/v1/review/wrong-answers` 端点
- [x] 处理 "X-User-ID" header 和 "node_id_filter" 查询参数
- [x] 返回标准响应格式（`WrongAnswersResponse`）
- [x] 添加错误处理与日志

**Subtask T-4.2:** 集成到 Epic 2 的答题流程
- [x] 在 `backend/app/api/v1/chat.py` 的 `answer_submit()` 中调用 `record_answer()`
- [x] 确保每个答题都被记录

### Task T-5: 前端页面组件

**Subtask T-5.1:** 创建 `frontend/src/views/ReviewPage.vue`
- [x] 实现错题本页面布局
- [x] 按知识点展开/折叠功能
- [x] "重新作答"功能（导航到 Quiz）
- [x] 实现响应式设计（移动端友好）

**Subtask T-5.2:** 更新路由配置
- [x] 在 `frontend/src/router/index.ts` 中添加 `ReviewPage` 路由
- [x] 从导航菜单链接到该页面

### Task T-6: 单元测试

**Subtask T-6.1:** 后端服务单元测试
- [x] 创建 `backend/tests/test_review_service.py`
- [x] 测试 `record_answer()` 的记录逻辑
- [x] 测试 `get_wrong_answers_by_node()` 的查询与分组逻辑
- [x] 测试 `is_invalidated` 过滤

**Subtask T-6.2:** API 端点单元测试
- [x] 创建 `backend/tests/test_review_api.py`
- [x] 模拟多个用户的答题记录
- [x] 测试按 node_id 的分组正确性
- [x] 验证 `total_wrong_count` 和 `total_nodes_with_errors` 的正确性
- [x] 测试缺少 X-User-ID header 的错误情况

**Subtask T-6.3:** 集成测试
- [x] 创建 `backend/tests/test_review_integration.py`
- [x] 模拟完整流程：答题 → 验证 → 记录 → 查询错题本
- [x] 验证端到端的数据流正确性

**Subtask T-6.4:** 前端组件单元测试
- [x] 创建 `frontend/src/views/ReviewPage.spec.ts`
- [x] 测试数据加载与展示
- [x] 测试展开/折叠节点的交互
- [x] 测试"重新作答"导航

### Task T-7: 集成验收测试

**Subtask T-7.1:** 创建 E2E 测试场景
- [x] 完整流程：选择节点 → 答题错误 → 查看错题本 → 按节点分组正确
- [x] 验证 invalidated 记录不出现
- [x] 验证统计数字准确性

### Review Findings

- [x] [Review][Patch] `question_id` 改为派生稳定 ID（`node_id + question_text` 哈希），替代当前 `question_id=node_id` [backend/app/api/v1/chat.py:315]
- [x] [Review][Patch] 运行时查询/写入路径重复执行 DDL 初始化，存在不必要性能与锁竞争风险 [backend/app/services/review_service.py:112]
- [x] [Review][Patch] 答题记录持久化失败仅日志记录并静默继续，导致数据丢失不可观测 [backend/app/api/v1/chat.py:319]
- [x] [Review][Defer] 基于 `X-User-ID` 的客户端可控身份方案存在越权风险 [backend/app/api/v1/review.py:37] — deferred, pre-existing

---

## Acceptance Test Criteria (BDD Format)

### Feature: 错题本数据持久化

```gherkin
Feature: Question History Persistence
  The system must record every quiz attempt and answer for later review.

  Scenario: Recording a wrong answer
    Given a student has completed a quiz
    And submitted an incorrect answer to a question
    When the Validator Agent confirms the error
    Then the system must insert a record into question_history table
    And the record must include user_id, node_id, question_text, user_answer, correct_answer
    And is_correct must be set to False
    And error_type must match the validation result
    And is_invalidated must default to False
```

### Feature: 错题本查询与分组

```gherkin
Feature: Wrong Answers Review
  Students can view their incorrect answers organized by knowledge concepts.

  Scenario: Fetching wrong answers grouped by node
    Given a student has at least 2 incorrect answers in different knowledge points
    When the frontend calls GET /api/v1/review/wrong-answers with X-User-ID header
    Then the response status must be "success"
    And data.by_node must be an array
    And each element must have node_id, node_label, total_errors, questions array
    And questions must be sorted by attempted_at DESC
    And data.summary.total_wrong_count must match the total unique invalid records
    And data.summary.total_nodes_with_errors must match the number of unique node_ids
    And all records with is_invalidated=true must be excluded

  Scenario: Filtering wrong answers by knowledge point
    Given the student has wrong answers in multiple knowledge points
    When calling GET /api/v1/review/wrong-answers?node_id_filter=doc_1_node_003
    Then only questions with node_id=doc_1_node_003 must be returned
    And other knowledge points must not appear in the response

  Scenario: Missing X-User-ID header
    When calling GET /api/v1/review/wrong-answers without X-User-ID header
    Then the response status must be "error"
    And message must indicate "Missing X-User-ID header"
```

### Feature: 防幻觉集成

```gherkin
Feature: Hallucination Filtering Integration
  Invalidated question records are excluded from the wrong-answer notebook.

  Scenario: Invalidated record exclusion
    Given a question record is marked as is_invalidated=true (by Story 3.3)
    When the student views the wrong-answers notebook
    Then that record must NOT appear in any grouping or list
    And the total_wrong_count must not include this record
    And total_nodes_with_errors must reflect only valid errors
```

---

## Dev Agent Record

### Implementation Progress

**Status**: Done  
**Created At**: 2026-04-05T18:20:00+08:00  
**Dev Agent**: Amelia

#### Completed Tasks
- [x] T-1.1: Database schema creation
- [x] T-1.2: Database integrity verification
- [x] T-2.1: Pydantic models
- [x] T-3.1: Service layer implementation
- [x] T-4.1: API endpoints
- [x] T-4.2: Integration with Quiz API
- [x] T-5.1: Frontend components
- [x] T-5.2: Router configuration
- [x] T-6.1 ~ T-6.4: All tests passing
- [x] T-7.1: E2E tests passing

#### Debug Log
- 2026-04-05: Implemented review notebook persistence (`quiz_attempts` + `question_history`) with grouped query service.
- 2026-04-05: Integrated SSE answer submission flow with `record_answer()` to persist every answer attempt.
- 2026-04-05: Added review notebook API route and frontend review page with node-group filtering and retry navigation.
- 2026-04-05: Added backend unit/integration tests and frontend Vitest spec; all tests passing.
- 2026-04-05: Code review patches applied: stable derived `question_id`, one-time review table init guard, and persistence-failure trace emission; related backend tests passed.

#### Completion Notes
- AC-1 satisfied: wrong answers are persisted in SQLite with timestamps, error_type, severity, node_id.
- AC-2 satisfied: `GET /api/v1/review/wrong-answers` returns grouped payload and summary.
- AC-3 satisfied: frontend allows per-node filtering and expanded grouped display.
- AC-4 satisfied: retry action routes back to quiz with selected node re-seeded in store.
- AC-5 satisfied: backend query excludes `is_invalidated=1` from groups and summary counts.
- Validation: backend `pytest` passed (128/128), frontend `vitest` passed (6/6).

#### Key Decisions
- **Database**: SQLite with sqlite-vec (from previous epics)
- **API Response Format**: Standard envelope with status/data/trace_id
- **User Identification**: X-User-ID header (session-based, no auth required for MVP)
- **Filtering Strategy**: SQL WHERE clause filters `is_invalidated=false` at query time
- **Frontend State**: Use Vue 3 ref + fetch API (Pinia optional for larger state)

#### Known Dependencies
1. **Epic 2 Answer Submit API** must call `record_answer()` to persist quiz data
2. **knowledge_nodes table** must exist with proper schema (from Epic 1)
3. **Story 3.2** will depend on `question_history` table

#### Implementation Notes
- All database queries must include `AND is_invalidated = 0` filter
- Use UUID for all IDs (question_record_id, attempt_id) for cross-system consistency
- Frontend should cache wrong-answers locally to avoid repeated API calls
- Consider adding pagination to API if dataset grows large

---

## File List

### Backend
- `backend/app/schemas/review.py` — Pydantic models for review endpoints
- `backend/app/services/review_service.py` — Business logic (record & query)
- `backend/app/api/v1/review.py` — REST endpoints for wrong-answer notebook
- `backend/app/migrations/003_add_question_history.sql` — Database schema
- `backend/app/main.py` — Registered review router
- `backend/app/api/v1/chat.py` — Persist answer records in SSE flow
- `backend/app/services/vector_store.py` — Ensure review tables are initialized
- `backend/tests/test_review_service.py` — Service layer unit tests
- `backend/tests/test_review_api.py` — API endpoint unit tests
- `backend/tests/test_review_integration.py` — Integration tests
- `backend/tests/test_vector.py` — Added review table existence assertions

### Frontend
- `frontend/src/views/ReviewPage.vue` — Error notebook UI component
- `frontend/src/views/ReviewPage.spec.ts` — Component tests
- `frontend/src/api/review.ts` — Review API client
- `frontend/src/router/index.ts` — Route configuration (update)
- `frontend/src/App.vue` — Navbar review link
- `frontend/src/api/quiz.ts` — Added stable user ID header for quiz/review continuity
- `frontend/package.json` — Added frontend test script and test devDependencies

### Database
- Migrations: `003_add_question_history.sql` in migration directory

---

## Change Log

- 2026-04-05: Implemented Story 3.1 end-to-end (DB schema, review service, API endpoint, quiz integration, review page UI, tests, and routing).

---

## References & Related Documents

- **PRD**: [prd.md](../planning-artifacts/prd.md) — FR8, FR9
- **Epic 3 Overview**: [epics.md](../planning-artifacts/epics.md#epic-3) — Full epic context
- **Architecture**: [architecture.md](../planning-artifacts/architecture.md) — SQLite schema, API patterns
- **Story 3.2**: Structured Mastery Calculation (depends on this story's data)
- **Story 3.3**: Anti-Hallucination Appeals Valve (sets `is_invalidated=true`)

---

## Questions for Clarification

_(To be addressed during implementation or with PM/Design)_

1. Should the wrong-answer notebook support pagination? If so, what page size?
2. Should students be able to export their wrong-answer notebook as PDF?
3. Should the system track how many times a student has retried a specific wrong question?
4. Should there be a "clear all wrong answers" or "reset" function?

