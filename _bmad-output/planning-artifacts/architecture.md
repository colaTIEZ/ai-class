---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments: ["_bmad-output/planning-artifacts/prd.md", "_bmad-output/planning-artifacts/product-brief-ai-class.md", "_bmad-output/project-context.md"]
workflowType: 'architecture'
project_name: 'ai-class'
user_name: 'Jins'
date: '2026-03-31T00:11:19+08:00'
lastStep: 8
status: 'complete'
completedAt: '2026-03-31'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
系统核心围绕 PDF 课件的“活化”展开。架构需支持从文件上传、知识点提取 (RAG) 到动态生成测验。最关键的架构挑战在于**苏格拉底式交互逻辑**：系统需要通过状态机精确跟踪并将用户在“错题生成”和“引导式探索”状态之间无缝切换，并实时流式传输引导内容以实现低延迟反馈。展示“追踪日志 (Trace Log)”证明了我们在 Agent 编排上的透明度和技术深度。

**Non-Functional Requirements:**
- **资源效率 (核心驱动力):** 在严格的 2C2G (2GB RAM) 限制下，系统必须采用“纯调度节点 (Pure Orchestrator)”模式，杜绝重型内存进程。
- **响应速度:** 初始提示延迟需 < 3s，依赖外置 API 的极速响应和本地缓存命中。
- **前端架构:** 使用 Vue 3 + Vite CSR (客户端渲染) 架构，尽最大可能将交互、UI生成和状态可视化计算卸载到客户端。
- **合规与隔离:** 会话级别的环境隔离，确保上传文档仅做学习使用。

**Scale & Complexity:**
系统属于低计算、高 I/O 且具有中等状态流转复杂度的应用程序，聚焦于图架构 (Graph-based) 的对话管线流转与三方服务集成。

- Primary domain: AI-Agentic Full-Stack Web Application
- Complexity level: Medium (系统受限资源与图引擎编排共同导致)
- Estimated architectural components: 5 (Vue SPA 客户端, FastAPI 异步后端, SQLite 本地存储/向量库, LangGraph 状态引擎, External APIs)

### Technical Constraints & Dependencies

- **Hardware Constraint:** 2C2G (2GB RAM)。这是最高指挥棒——必须全面外包重度计算（OCR/图片 PDF 解析走第三方大模型文档API、Embedding/LLM 推理全走云端）。
- **State Management Engine:** 确立使用 `LangGraph` (Python) 作为多 Agent 的图状态机，负责错题、提示与苏格拉底循环的状态持久化流转。
- **Data & Vector Storage:** 采用极轻量级的 `SQLite` + `sqlite-vss/sqlite-vec` 扩展方案用于零开销本地向量检索（如果规模超出预期，留有切换无服务器云存储如 Pinecone 的灵活性）。
- **Base Extraction Tool:** 本地仅保留如 `PyMuPDF` 这样的快速轻量级文本提取库。
- **Protocol:** Server-Sent Events (SSE) 用于 AI 流式的响应传输。

### Cross-Cutting Concerns Identified

- **External API Resilience:** 系统极其依赖外部 API (DeepSeek/GLM 等)，因此对网络抖动、超时回退及错误重试等“容错处理”横切关注点要求极高。
- **Memory Guarding:** 防止即使是轻量级库解析大本纯文本 PDF 瞬间导致的内存溢出（OOM），需要采取流式处理或硬性分段控制。
- **System Observability:** 必须能将后端 LangGraph 状态节点跳转的“推理链日志”有效地向前端传递，以支持透明的技术面试演示。


## Starter Template Evaluation

### Primary Technology Domain

Full-stack Web Application (AI-Agentic) 基于项目对资源效率和 Agent 编排透明度的要求。

### Selected Starter: Custom Lean Full-stack (Vue 3 + FastAPI + LangGraph)

**Rationale for Selection:**
针对 2C2G (2GB RAM) 的极端约束，选择手动构建前后端分离的精简架构。前端通过 Vue 3 CSR 卸载计算压力；后端通过 FastAPI 异步处理 I/O，并利用 LangGraph 实现复杂的苏格拉底教学逻辑状态管理。

**Initialization Commands:**

**Frontend:**
```bash
npm create vite@latest frontend -- --template vue-ts
npm install -D tailwindcss @tailwindcss/vite
```

**Backend:**
```bash
pip install fastapi uvicorn langgraph langchain-openai sqlite-vec pydantic-settings python-multipart PyMuPDF
```

**Architectural Decisions Provided by Starter:**

- **Language & Runtime:** TypeScript (Frontend), Python 3.10+ (Backend).
- **Styling Solution:** Tailwind CSS v4 (通过 Vite 插件零配置运行).
- **State Management:** LangGraph (后端 Agent 状态机) + Pinia (前端应用状态，视需要添加).
- **Data & Vector:** SQLite + `sqlite-vec` (本地文件索引，内存占用极低)。
- **Real-time:** FastAPI `StreamingResponse` (用于 SSE 助教思考过程流式输出)。
- **Development Experience:** 采用 HMR 驱动的快速开发流，后端支持 Swagger 自动文档。

**Note:** 分别在 `frontend/` 和 `backend/` 目录下初始化是实现该架构的首要任务。


## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- **存储方案:** 选定 SQLite + `sqlite-vec` (本地向量数据库)。通过单一文件实现业务数据与嵌入向量的统一存储，极大降低 2C2G 环境下的维护成本与内存开机。
- **状态引擎:** 选定 LangGraph (Python) 并使用 SQLite 作为 Checkpointer。确保苏格拉底循环对话的状态在断电/重启后依然可追溯且持久化。

**Important Decisions (Shape Architecture):**
- **API 通信模式:** 采用 SSE (Server-Sent Events) 并支持多类型 JSON 负载设计。允许系统在单一流中同时下发对话内容 (`type: content`) 与 Agent 推理链数据 (`type: trace`)。
- **知识可视化:** 选定 AntV G6 实现交互式知识图谱。其针对层级依赖关系（Hierarchical Layout）的优秀支持能完美呈现 PDF 的知识点脉络。

**Deferred Decisions (Post-MVP):**
- **分布式向量后端:** 预留了向 Pinecone 或阿里云 DashVector 迁移的接口设计，待 MVP 版本数据规模突破 500 万向量时再行评估。
- **WeChat 适配:** 暂缓 Mini-program 原生组件开发，优先保证 Web 端 (Vue 3) 的极致体验。

### Data Architecture

- **Database:** SQLite (Version: 3.45+)
- **Vector Extension:** `sqlite-vec` (Version: 0.1.0+)
- **Rationale:** 2C2G 环境下的最优解：零进程、高性能、无缝备份同步。

### API & Communication Patterns

- **Pattern:** RESTful API (for Upload/Management) + SSE (for AI logic).
- **Format:** Strict JSON streaming.
- **Trace observability:** 后端 LangGraph 节点事件通过 SSE `trace` 事件类型实时同步至前端 Vue 3 渲染。

### Frontend Architecture

- **Visualization:** AntV G6 (Version: 5.0+)
- **State management:** Pinia (用于管理课程元数据与追踪日志缓存)。
- **Mobile optimization:** CSS Container Queries + Element Plus Responsive Designs.

### Infrastructure & Deployment

- **Deployment Model:** Single VM Docker-Compose (Frontend container + Backend container + SQLite Volume).
- **Environment:** Lightweight 2C2G (2 CPU, 2GB RAM)。
- **Scaling strategy:** 通过客户端渲染 (CSR) 尽可能将负载转移给用户的浏览器。


## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
3 个核心可能会引起 AI Agent 之间协作冲突的领域：命名冲突、项目目录组织、以及跨栈（前端-后端）的交互数据模式。

### Naming Patterns

**Database Naming Conventions:**
- 表名使用 `snake_case` 的复数形式（例：`users`, `documents`）。
- 列名也使用 `snake_case`（例：`user_id`, `created_at`）。

**API Naming Conventions:**
- JSON Response 的 Key 全部采用 `snake_case`，以匹配后端 Python 风格。
- 路由使用复数 REST 标准（例：`/api/v1/documents`）。
- URL 参数形式始终采用下划线风格：`?document_id=123` 而不是 `documentId`。

**Code Naming Conventions:**
- 后端 (Python): 严格 PEP8，所有模块、函数和变量均为 `snake_case`。
- 前端 (Vue 3 TS): 
  - 组件名采用 `PascalCase`（例：`KnowledgeGraph.vue`）。
  - 可组合式函数 (Composables) 采用驼峰的 `useAction` 模式（例：`useDocumentUpload`）。

### Structure Patterns

**Project Organization:**
- 采用最极致的前后端分离隔离：
  - `/frontend`: 此级为 Vite 根目录。
  - `/backend/app`: FastAPI 及核心业务代码。
- 严禁任何跨目录级别的环境遍历，保证各自容器内的上下文完全纯净。

**File Structure Patterns:**
- **LangGraph**: 杜绝将所有节点写在单一文件中。强制规则：`/backend/app/graph/nodes/` 目录下按业务单元切分（例如 `question_gen.py`, `hint_generator.py`）。

### Format Patterns

**API Response Formats:**
- 所有的非流式 API 强制包裹标准封套：
```json
{
  "status": "success", // or "error"
  "data": { ... },     // payload
  "message": "",       // Error detail when applicable
  "trace_id": ""       // LangGraph invocation trace
}
```

**Data Exchange Formats:**
- 日期格式全部使用 ISO 8601 UTC 字符串传递 (`2026-03-31T00:00:00Z`)，禁止使用 Unix 时间戳整数交接以免解析混乱。

### Communication Patterns

**Event System Patterns (SSE):**
- SSE 监听对象的事件类型 `type` 必须枚举：
  - `content`: AI 用于显示给学生的聊天文本流。
  - `trace`: 后端代理思考的节点流转日志。
  - `error`: 异常阻拦。

**State Management Patterns:**
- 前端使用 `Pinia` 维护会话层状态；后端 `LangGraph Checkpointer (SQLite)` 为权威全局状态源，客户端禁止本地模拟状态转换。

### Process Patterns

**Error Handling Patterns:**
- External API 失败（LLM 请求失败，速率受限）统一在后端的 Node 逻辑层内部执行 Retry；
- 传达给前端的仅限终态：“无法生成提示，请重试。”

### Enforcement Guidelines

**All AI Agents MUST:**

- 严格遵循 `snake_case` 为基准的后端-数据库打通命名。
- 将复杂图论处理或格式化渲染直接编写为 Vue 组件代码，保持后端的最小职责。
- 在 LangGraph 节点设计上，每次仅变异/产出 `State` 的一个键，禁止跨界修改无关数据。

### Pattern Examples

**Good Examples:**
```python
# Backend Node Example: 单一职责，snake_case
async def generate_hint_node(state: SocraticState):
    return {"current_hint": hint_text} 
```

**Anti-Patterns:**
```javascript
// 前端试图修正大小写而导致映射混乱
const userId = response.data.UserId; // BAD
const user_id = response.data.user_id; // GOOD (接受 snake_case)
```


## Project Structure & Boundaries

### Complete Project Directory Structure

```text
ai-class/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── frontend/                   # Vue 3 CSR SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js      # v4 CSS setup via @tailwindcss/vite
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── style.css           # @import "tailwindcss"
│   │   ├── App.vue
│   │   ├── api/                # Axios/Fetch clients for backend requests
│   │   ├── assets/             # Static files
│   │   ├── components/
│   │   │   ├── chat/           # Socratic chat & trace log UI
│   │   │   ├── graph/          # AntV G6 visualization
│   │   │   └── upload/         # PDF upload UI
│   │   ├── composables/        # useSocraticChat, useDocumentUpload
│   │   ├── stores/             # Pinia state management
│   │   └── types/              # TypeScript interfaces (matching backend models)
│   └── tests/
│
└── backend/                    # FastAPI + LangGraph
    ├── pyproject.toml
    ├── requirements.txt
    ├── app/
    │   ├── __init__.py
    │   ├── main.py             # FastAPI entrypoint & SSE routes
    │   ├── core/
    │   │   ├── config.py       # Pydantic Settings
    │   │   └── exceptions.py   # Global error handling
    │   ├── api/                # REST endpoints
    │   │   ├── v1/
    │   │   │   ├── documents.py
    │   │   │   └── chat.py
    │   ├── graph/              # LangGraph Orchestration
    │   │   ├── __init__.py
    │   │   ├── state.py        # SocraticState definition (TypedDict)
    │   │   ├── tools.py        # LLM tools
    │   │   ├── orchestrator.py # Graph compilation & edges
    │   │   └── nodes/          # Isolated node functions
    │   │       ├── extract.py
    │   │       ├── hint.py
    │   │       └── validate.py
    │   ├── services/
    │   │   ├── pdf_parser.py   # PyMuPDF extraction logic
    │   │   └── vector_store.py # sqlite-vec interaction layer
    │   └── schemas/            # Pydantic data validation models
    ├── data/                   # local sqlite database file mounts here
    └── tests/
```

### Architectural Boundaries

**API Boundaries:**
- 前端与后端的唯一接触点是 `/backend/app/api/v1` 中定义的端点。
- SSE (Server-Sent Events) 通道仅用于下发，不接受前端通过数据流上传状态。前端所有的发话必须通过标准的 `POST /api/v1/chat/message` 请求触发后端的 Agent 图运转。

**Component Boundaries:**
- **[前端] 响应式状态边界:** Pinia (stores) 仅负责管理“UI状态的展示层（如当前选中的课程、错误弹窗的开启）”和缓存。真正的对话历史源（Source of Truth）存在通过后段 Checkpointer 恢复的数据中。
- **[后端] 图网络边界:** FastAPI 路由 (api/) 必须极其轻量。它的唯一职责是将请求转换后调用 `graph.orchestrator.invoke()` 或 `astream()`，严禁在 api 路由中写任何 RAG 或 LLM 业务逻辑。

**Data Boundaries:**
- **Vector VS Relational:** 系统所有的关系数据（Document Meta, User Session）与嵌入向量数据（Text Embeddings）统统受限于同一个 SQLite 数据库中，通过 `sqlite-vec` 提供纯本地检索方案。不允许应用层直接执行复杂的图关系查询，由服务层映射处理。

### Requirements to Structure Mapping

**Feature: Material Management (FR1-FR2)**
- Components: `frontend/src/components/upload/`
- API Routes: `backend/app/api/v1/documents.py`
- Services: `backend/app/services/pdf_parser.py` (包含 2C2G 的内存与文件大小卫兵防御机制)

**Feature: Knowledge Engine & Graph (FR3-FR4, Phase 2)**
- Components: `frontend/src/components/graph/`
- Vector Store Layer: `backend/app/services/vector_store.py`

**Feature: Socratic Interaction & Trace (FR5-FR7, FR10)**
- UI Components: `frontend/src/components/chat/`
- Graph Logic: `backend/app/graph/orchestrator.py` 以及所有的 `backend/app/graph/nodes/`
- State: `backend/app/graph/state.py` (包含 Trace Log 所需记录的所有内部推理过程)


## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
高度兼容。`Vue 3 Vite` 用于纯客户端渲染（CSR）完美契合 `FastAPI` 作为无状态 API 层的设计。`LangGraph` 与 Python 异步生态高度整合，且使用 `SQLite` 作为状态持久化及向量存储（通过 `sqlite-vec`），构建出了一个自洽且无需额外 Redis/PostgreSQL 进程的闭环系统，完全满足 2C2G 的严苛硬件限制。

**Pattern Consistency:**
高度一致。制定了全范围的 `snake_case` 后端命名映射至标准 JSON 的规则。同时通过 SSE 单向流传输复杂模型推理过程（Trace Logging）及前端响应的设计确保了职责分离。前端负责纯“展示及本地用户交互状态层”，后端掌握一切“领域状态层”。

**Structure Alignment:**
目录边界极其清晰，物理隔离了前端工程 (`/frontend`) 和后端工程 (`/backend`)。并且严格规范了 LangGraph 的节点级别文件分割（避免大单体文件），符合扩展性要求。

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**
所有的核心特性均被覆盖：文件上传防卫机制映射到了服务层，知识引擎及向量检索分配给了本地 SQLite 和大模型外包处理，苏格拉底对话通过 LangGraph 状态机获得实现。

**Functional Requirements Coverage:**
- FR1-FR2 (文件管理/大小拦截) → 路由校验及 PyMuPDF 内存流控。
- FR3-FR4 (提取及图谱渲染) → SQLite-vec + AntV G6。
- FR5-FR7, FR10 (多 Agent 引导及透明追踪) → LangGraph 编排结合 SSE 多端（content, trace）分发协议。

**Non-Functional Requirements Coverage:**
- 资源占用：通过放弃重量级 ORM、重量级后端框架、重量级独立向量数据库（改用 SQLite-vec），完全切中 1.5GB 的后端内存红线。
- 可观测性：通过在 SSE 报文中附加 `trace_id` 及原始节点流转日志实现了系统可见性（System Trace Visibility）。

### Implementation Readiness Validation ✅

**Decision Completeness:**
所有可能引起阻塞的前端和后端基座库选择、通信协议选择（SSE）及持久化方式（SQLite）已经全部清晰指出并记录了具体版本控制要求（LangGraph 0.0.60+等）。

**Structure Completeness:**
项目树详细到具体的目录结构（包括如 `app/graph/nodes/` 的子切分）以及职责边界。AI 代码开发 Agent (如 Amelia) 可以无歧义地按照此蓝图落盘代码。

**Pattern Completeness:**
确立了所有 API Payload 的格式模板和前端获取变量的解构准则，预防了绝大部分序列化反序列化导致的“沉默失效”排雷时间。

### Gap Analysis Results

**None Critical:** 目前架构处于闭环且可落地的状态，没有遗漏阻止 MVP 开发的关键组件。
**Minor (Nice-to-Have):** 虽然 SQLite 支持多线程并发（在 `sqlite-vec` 配置妥当的情况下），但是在正式进入高并发线上测试前，可能需要补充对于 SQLite 封锁问题 (Database is locked) 的 WAL (Write-Ahead Logging) 应对小节。不过这可以在实施阶段的具体配置中解决。

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High (高度自信可以稳定运行在 2C2G 规格的设备上)

**Key Strengths:**
- 极具成本效益和部署便携性的存储栈 (`SQLite` 一把梭)。
- 极致的性能压榨模式，一切重度计算和图形绘制都在云端服务商和用户本地浏览器完成，充分布置了防 OOM 的防波堤。

**Areas for Future Enhancement:**
- 向专用云中间件如 Pinecone、Redis，以及针对微信小程序的端终渲染的进一步架构移植改造。

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented.
- Use implementation patterns consistently across all components.
- Respect project structure and boundaries.
- Refer to this document for all architectural questions.

**First Implementation Priority:**
在项目的根目录下分别初始化前端 `frontend` (使用 Vite) 和后端 `backend` 虚拟环境并安装规划的脚手架依赖。
