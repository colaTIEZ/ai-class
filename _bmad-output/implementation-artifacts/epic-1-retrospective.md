# Epic 1 Retrospective

**Epic:** 课件解析、边界圈选与高可用并发控制 (Course Material, Processing Queue & Scope Selection)

**Date:** 2026-03-31

**Facilitator:** Bob (Scrum Master)

**Participants:** Alice (Product Owner), Charlie (Senior Dev), Amelia (Developer), Jins (Project Lead)

---

## Executive Summary

Epic 1 成功交付了 ai-class 项目的核心基础设施，实现了从 PDF 上传到知识图谱可视化与范围圈选的完整流程。四个 Story 全部完成，累计通过 50+ 测试用例，为后续苏格拉底测验引擎（Epic 2）奠定了坚实基础。

---

## Stories Completed

| Story | Title | Status | Key Deliverables |
|-------|-------|--------|------------------|
| 1.1 | 项目基座与数据契约 | ✅ Done | Vue3+FastAPI+sqlite-vec 全栈搭建，24 个测试通过 |
| 1.2 | 全局单例上传队列 | ✅ Done | 防 OOM 并发控制，28 个测试通过，SQLite 持久化 |
| 1.3 | 内存安全的 RAG 萃取 | ✅ Done | Generator 模式解析、层级抽取、OpenAI 嵌入集成 |
| 1.4 | 知识图谱与范围圈选 | ✅ Done | AntV G6 可视化、Pinia 状态管理、Vue Router |

---

## What Went Well (WWW)

### Architecture & Engineering

1. **内存约束下的创新设计** - 全局单例 asyncio.Queue + Generator 模式解析，完美应对 2C2G 硬限制
2. **sqlite-vec 选型** - 单文件同时承载关系数据和向量检索，在单 VM 部署场景下是降维打击
3. **数据契约先行** - Story 1.1 定义的 `knowledge_tree.py` Schema 被后续 Story 严格遵守，前后端并行开发零冲突

### Process & Quality

4. **Review 流程有效** - Story 1.2/1.4 的 Review Findings 详尽，关键问题（内存增长、UUID 碰撞、G6 事件兼容性）在 Review 阶段被捕获修复
5. **测试覆盖率高** - 每个 Story 都有专门测试套件，累计 50+ 测试用例，支撑重构信心
6. **文档即代码** - Story 文件本身是详尽的技术文档，包含 Tasks、Dev Notes、Completion Notes、File List

### Product & UX

7. **优雅降级** - 服务器繁忙时返回明确队列位置而非报错，体现成熟产品思维
8. **交互直觉** - 知识图谱的级联选择（选父节点自动选子节点）符合用户直觉

---

## What Could be Done Improved (WCDI)

### Critical Issues Identified

1. **🚨 Zombie Tasks 问题** - OOM Killer 杀掉进程后，SQLite 中 status=0 的任务永久残留，用户卡在加载动画，队列可能死锁
   - **严重性：** P0 Critical
   - **决议：** Epic 2 开始前必须修复

2. **Magic Byte 校验缺失** - 目前只检查 MIME type，恶意用户可伪造
   - **严重性：** P1
   - **决议：** 补充 PDF 文件头签名校验 (`%PDF`)

3. **嵌入 API 静默 Fallback** - 无 API Key 时返回 dummy embeddings，生产环境可能静默失败
   - **严重性：** P1
   - **决议：** 启动时 fail-fast 而非静默 fallback

### Deferred Improvements

4. **加载进度反馈** - 用户只知道"排队中"，不知道解析进度
   - **决议：** 延迟到 Epic 2 Story 2.2，复用 SSE 通道推送 `{"type": "progress"}` 消息

5. **错误提示国际化** - 目前硬编码英文
   - **决议：** 低优先级，Epic 3 或后续评估

### Explicitly Rejected Suggestions

6. **前端 Vitest 单元测试** - MVP 阶段 UI 迭代快，单测维护成本 > 收益
   - **决议：** 保持 TypeScript strict mode (`tsc --noEmit`) 作为防线，后端 Pytest 优先

---

## Action Items

| # | Priority | Action Item | Owner | Timeline |
|---|----------|-------------|-------|----------|
| 1 | 🔴 P0 | **修复 Zombie Tasks** - 进程启动时扫描 status=0 任务，根据 updated_at 超时阈值重置为 failed 或 retry | Dev Team | Epic 2 开始前 |
| 2 | 🟡 P1 | **补充 Magic Byte 校验** - 读取文件头 4 字节验证 PDF 签名 `%PDF` | Dev Team | Epic 2 Story 2.1 前 |
| 3 | 🟡 P1 | **嵌入 API 配置显式校验** - 启动时检测 `OPENAI_API_KEY`，缺失时 fail-fast | Dev Team | Epic 2 开始前 |
| 4 | 🟢 P2 | **统一 SSE 进度推送** - 复用 Epic 2 SSE 通道推送 PDF 解析进度 | Dev Team | Epic 2 Story 2.2 |
| 5 | 🟢 P2 | **错误提示国际化** - 评估 i18n 方案 | Product | Epic 3 或后续 |
| 6 | 🔵 Info | **多模型代码风格** - 记录到 project-context.md | Scrum Master | 回顾会后 |

---

## Epic 2 Readiness Assessment

### Technical Readiness

| Dimension | Score | Notes |
|-----------|-------|-------|
| Architecture Docs | ⭐⭐⭐⭐⭐ | LangGraph 目录结构、SSE 协议已完整定义 |
| Infrastructure | ⭐⭐⭐⭐☆ | 向量检索、状态存储就绪；需先修复 P0 问题 |
| Data Contracts | ⭐⭐⭐⭐⭐ | `knowledge_tree` Schema 已验证，前后端一致 |
| Frontend Entry | ⭐⭐⭐⭐☆ | Router/Pinia 就绪，QuizView 为占位符 |
| Team Confidence | ⭐⭐⭐⭐☆ | Epic 1 经验可复用，LangGraph 是新挑战 |

**Overall:** 🟡 Conditionally Ready (需先完成 P0/P1 Action Items)

### Ready Infrastructure from Epic 1

- ✅ `sqlite-vec` 向量检索已验证可用
- ✅ `knowledge_nodes` 表结构已建立，支持层级查询
- ✅ Pinia `useQuizStore` 存储用户圈选的 `node_id` 数组
- ✅ Vue Router 已配置 `/quiz` 路由入口
- ✅ FastAPI SSE 能力已在架构文档中定义

### Placeholder Files Created in Epic 1

- `backend/app/graph/__init__.py`
- `backend/app/graph/nodes/__init__.py`
- `backend/app/api/v1/chat.py`

### New Components Required for Epic 2

```
backend/app/graph/
├── state.py          # SocraticState TypedDict
├── orchestrator.py   # 图编译 & 边定义
└── nodes/
    ├── question_gen.py
    ├── validator.py
    ├── hint.py
    └── pruner.py
```

---

## Key Learnings

1. **数据契约先行** - 在 Story 1.1 定义严格 Schema 后，后续 Stories 的集成几乎零摩擦
2. **Review 流程价值** - 代码 Review 捕获的问题（内存增长、并发安全、兼容性）比测试更早暴露风险
3. **延迟决策的智慧** - 将加载进度反馈延迟到 Epic 2 SSE 通道，实现了架构上的统一
4. **务实的测试策略** - MVP 阶段 TypeScript strict mode 足够，避免过早引入高维护成本的前端单测

---

## Next Steps

1. **立即执行：** 完成 P0/P1 Action Items (Zombie Tasks, Magic Byte, API Key)
2. **然后：** 启动 Epic 2 Sprint Planning
3. **建议：** 在 Epic 2 Story 2.1 之前更新 project-context.md，记录多模型协作经验

---

*Retrospective facilitated by Bob (Scrum Master) using bmad-retrospective workflow*
