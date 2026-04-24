# 企业级 Agentic RAG 重构设计规范

**项目名称：** `ai-class`

**文档日期：** `2026-04-24`

**文档目标：** 将当前“PDF 上传后自动切分、向量化、生成知识树并按节点出题”的项目，升级为面向企业生产实践的 `多模态 Agentic RAG 出题与学习系统`。本文档重点强调真实项目可落地性，同时覆盖适合实习生逐步掌握的企业级 AI 应用技术栈。

---

## 1. 背景与重构定位

当前项目已经具备基础闭环：

- 用户上传 PDF
- 后端解析文本并切分
- 生成 embedding 并建立检索数据
- 生成知识层级树
- 用户选择节点后在范围内出题

这套流程证明项目方向是正确的，但从企业级 AI 应用视角看，当前系统仍然存在明显局限：

- 检索层以单一文本向量检索为主，准确性和相关性上限有限
- 知识树依赖固定规则生成，对非结构化文档适配性弱
- 存储层未分离业务数据、向量索引与原始知识资产
- 上传、解析、索引构建、出题缺少标准化工作流边界
- 缺少多模态知识处理能力，图片、表格、Excel 等资产未参与检索与出题
- 缺少可观测性、评测闭环和异步索引构建机制

因此，本项目不应仅被重构为“更复杂的 PDF 出题系统”，而应升级为：

`面向教育/知识训练场景的企业级多模态 Agentic RAG 系统`

---

## 2. 重构目标

### 2.1 总体目标

重构后的系统应支持以下核心能力：

- 支持 `PDF / 图片 / Excel / 表格 / 结构化文本` 的统一知识接入
- 使用 `LangGraph` 构建可恢复、可追踪的工作流
- 使用 `LangChain` 组织 RAG 组件与多模态提示链路
- 使用 `Milvus` 构建高质量混合检索能力
- 使用 `PostgreSQL + OSS + Redis` 完成企业级分层存储
- 将“静态知识树”升级为“动态测验范围视图”
- 支持图片、表格、页区域等知识资产参与检索和出题
- 建立企业级评测、追踪、缓存、异步任务和索引治理能力

### 2.2 非目标

以下内容不作为第一阶段目标：

- 直接构建完整且长期稳定的全局知识图谱
- 一开始就拆成多服务微服务架构
- 一开始就做复杂多 Agent 协同平台

推荐策略是：

`先做模块化单体 + 明确边界 + 预留服务化演进空间`

---

## 3. 重构后的系统定位

### 3.1 核心产品定位

系统的核心不再是“生成一棵知识树”，而是：

`构建多模态知识资产库，并根据用户意图动态组织测验范围，再在该范围内执行高质量检索与出题`

### 3.2 关键设计结论

- “图”不是系统核心真相数据，`知识资产索引` 才是核心
- 用户选择的不是“图本身”，而是 `测验范围`
- 范围视图是检索结果的组织形式，而不是永久静态结构
- 多模态资产必须作为一等公民参与索引、检索和生成

---

## 4. 推荐总体架构

重构后推荐使用如下分层架构：

### 4.1 接入层

技术推荐：

- `FastAPI`
- `Pydantic`
- `SSE / WebSocket`

职责：

- 文件上传
- 文档管理
- 范围视图查询
- 题目生成与流式返回
- 答题与评估
- 任务状态查询

### 4.2 工作流编排层

技术推荐：

- `LangGraph`

职责：

- 文档接入工作流
- 解析与索引构建工作流
- 范围视图构建工作流
- 出题工作流
- 答案评估与学习反馈工作流

设计原则：

- 一个工作流只负责一种主业务结果
- 每个节点具备明确输入输出与失败处理逻辑
- 重要状态持久化，支持恢复与追踪

### 4.3 RAG 组件层

技术推荐：

- `LangChain`

职责：

- 文档加载器
- 文本分块器
- Embedding 调用
- Retriever 封装
- Reranker 封装
- Prompt Template
- Output Parser
- 多模态内容块组装

### 4.4 存储层

技术推荐：

- `Milvus`
- `PostgreSQL`
- `阿里云 OSS`
- `Redis`

职责拆分：

- `Milvus`：向量索引、稀疏向量、多向量索引、混合检索
- `PostgreSQL`：文档、chunk、范围视图、题目、答题、资产关系元数据
- `OSS`：原始 PDF、图片、页截图、表格导出、解析中间产物
- `Redis`：缓存、任务状态、限流、热点视图缓存

### 4.5 异步任务层

技术推荐：

- `Celery + Redis`
或
- `Arq + Redis`

职责：

- 文件解析
- OCR
- 向量化
- Milvus 索引写入
- 视图缓存刷新

### 4.6 可观测与评测层

技术推荐：

- `LangSmith`
- `OpenTelemetry`
- `Prometheus + Grafana`
- `Ragas`

职责：

- 模型调用链路追踪
- 工作流节点耗时与失败率监控
- 检索效果评测
- 题目生成质量评测

---

## 5. 从静态知识树到动态测验范围视图

### 5.1 当前知识树方案的问题

当前系统中的知识树构建更接近“固定规则抽取的文档层级树”，存在以下问题：

- 对没有规范章节结构的文档适配性差
- 无法稳定表示非结构化资料
- 无法自然处理多次增量上传
- 难以维护一张完整、稳定、长期有效的全局图

### 5.2 新的设计目标

重构后不再强制生成固定全局知识树，而是引入：

`动态测验范围视图（Dynamic Scope View）`

其本质是：

`基于当前知识库检索结果，对知识资产进行聚合、分组和局部关系组织，以便用户快速选择测验范围`

### 5.3 允许的展示形式

系统可以根据场景动态选择以下一种或多种形式：

- `主题分组卡片`
- `可展开目录树`
- `标签聚类列表`
- `局部关系图`

默认建议：

`主题分组卡片 + 可展开目录树`

局部关系图只作为高级视图，不作为默认主入口。

### 5.4 Scope View 的生成方式

推荐流程：

1. 用户进入某课程或知识库
2. 系统根据最近上传文档、关键词、主题标签、章节元数据召回候选资产
3. 将候选结果聚合为若干主题簇或目录项
4. 生成可供前端展示的范围视图
5. 用户选择一个或多个范围后，系统仅在该范围内执行检索与出题

### 5.5 模块命名建议

当前“知识树生成”模块建议重命名为：

- `Scope View Builder`
或
- `Knowledge Scope Organizer`

这样更符合企业级职责表达。

---

## 6. 多模态知识资产设计

### 6.1 多模态范围

系统需要原生支持以下资产类型：

- `text`
- `image`
- `table`
- `sheet`
- `formula`
- `page_region`
- `pdf_page_snapshot`

### 6.2 核心设计原则

多模态资产不是附件，而是：

`参与检索、参与推理、参与出题的知识资产`

### 6.3 推荐解析方案

优先推荐：

- `Docling`
- `Unstructured`

用于实现：

- PDF layout 解析
- 文本与标题抽取
- 图片抽取
- 表格抽取
- Excel sheet 结构化处理
- 页码、坐标、阅读顺序、附近文本提取

### 6.4 OSS 存储策略

建议将以下内容存入 `阿里云 OSS`：

- 原始 PDF
- 原始 Excel
- 页面截图
- 裁剪图片
- 表格导出文件
- 多模态解析中间结果
- 解析后的结构化 JSON

数据库中只保存：

- `oss_key`
- `url`
- `signed_url`
- 元数据
- 资产关系

---

## 7. 占位符机制与资产关联规范

### 7.1 设计目标

当文本中存在图片、表格、页区域时，不能因为切块导致这些内容与上下文断裂。

因此推荐采用：

`文本块 + 占位符 + 资产映射`

### 7.2 示例

```text
矩阵乘法要求前一个矩阵的列数等于后一个矩阵的行数。[FIGURE:fig_001]
乘积矩阵的维度由前一个矩阵的行数和后一个矩阵的列数共同决定。[TABLE:tbl_003]
```

### 7.3 规范要求

- 图片、表格、页区域应被视为不可切分原子资产
- 文本块中保留占位符
- 系统维护占位符与资产的映射关系
- 检索返回的不应只是文本，而应是 `Chunk + Linked Assets`

### 7.4 数据模型建议

#### knowledge_assets

- `asset_id`
- `document_id`
- `asset_type`
- `source_type`
- `oss_key`
- `page_no`
- `bbox`
- `caption`
- `ocr_text`
- `nearby_text`
- `mime_type`
- `hash`
- `created_at`

#### chunk_asset_links

- `chunk_id`
- `asset_id`
- `placeholder_token`
- `link_type`
- `order_index`

### 7.5 检索后的组装方式

当检索命中某个 chunk 时，系统需要：

1. 解析 chunk 中的占位符
2. 查询 `chunk_asset_links`
3. 查询 `knowledge_assets`
4. 返回图片、表格或页区域的元数据与 OSS 地址
5. 将文本和资产一并送入生成链路

---

## 8. 企业级检索架构：Milvus + 混合检索 + 重排

### 8.1 检索目标

你的出题场景不是开放域问答，而是：

`在用户选择的范围内，尽可能准确地检索出与当前知识点最相关的上下文`

### 8.2 推荐的三层检索策略

#### 第一层：范围约束

根据用户选择的测验范围，先缩小候选集合：

- 课程
- 文档
- 主题簇
- 章节
- 标签
- 资产集合

#### 第二层：混合召回

在候选范围内做：

- `Dense Retrieval`
- `Sparse Retrieval / BM25`
- `Metadata Filter`

#### 第三层：重排

推荐：

- `RRF / WeightedRanker`
- `Cross-Encoder Reranker`

### 8.3 多模态检索策略

推荐按两阶段演进：

#### 第一阶段：文本主导 + 资产补水

- 以文本 chunk 检索为主
- 命中文本后回查图片、表格等关联资产

#### 第二阶段：真正多模态检索

- 文本向量
- 图片向量
- 表格摘要向量
- Sheet 级别向量
- 多向量融合检索

### 8.4 Milvus 使用建议

Milvus 中至少维护以下索引能力：

- 文本 dense vector
- 文本 sparse vector
- 可选图像向量
- 文档与范围过滤字段

推荐结合：

- `Milvus Hybrid Search`
- `Milvus Multi-Vector Search`
- Rerank 策略

---

## 9. 数据存储分层设计

### 9.1 PostgreSQL 业务表建议

建议维护以下核心表：

- `documents`
- `document_versions`
- `chunks`
- `knowledge_assets`
- `chunk_asset_links`
- `scope_views`
- `scope_view_items`
- `questions`
- `question_generation_logs`
- `quiz_attempts`
- `answer_evaluations`
- `retrieval_logs`

### 9.2 Milvus collection 设计

每个检索单元建议具备以下字段：

- `chunk_id`
- `document_id`
- `scope_id`
- `node_or_topic_id`
- `text`
- `dense_vector`
- `sparse_vector`
- `asset_refs`
- `subject`
- `difficulty`
- `created_at`

### 9.3 OSS 对象路径建议

建议统一对象路径规范，例如：

- `raw/{kb_id}/{document_id}/source.pdf`
- `pages/{kb_id}/{document_id}/page_001.png`
- `assets/{kb_id}/{document_id}/figures/fig_001.png`
- `assets/{kb_id}/{document_id}/tables/tbl_003.html`
- `derived/{kb_id}/{document_id}/parsed/document.json`

---

## 10. LangGraph 工作流拆分建议

### 10.1 文档接入工作流

流程建议：

`upload -> persist_raw_file -> register_document -> enqueue_parse_job`

### 10.2 解析与索引构建工作流

流程建议：

`load_from_oss -> parse_document -> extract_assets -> build_placeholders -> chunking -> embedding -> milvus_upsert -> postgres_upsert -> cache_refresh`

### 10.3 范围视图构建工作流

流程建议：

`collect_candidate_assets -> cluster_topics -> build_scope_view -> cache_scope_view`

### 10.4 出题工作流

流程建议：

`resolve_scope -> retrieve_hybrid -> rerank -> hydrate_assets -> build_prompt -> generate_question -> validate_output`

### 10.5 答题评估工作流

流程建议：

`validate_answer -> retrieve_supporting_context -> evaluate_answer -> generate_feedback -> persist_attempt`

---

## 11. 推荐技术栈清单

### 11.1 基础栈

- `FastAPI`
- `Vue 3`
- `TypeScript`
- `PostgreSQL`
- `Redis`

### 11.2 AI 应用核心栈

- `LangChain`
- `LangGraph`
- `LangSmith`
- `Milvus`
- `Ragas`

### 11.3 多模态解析与知识处理

- `Docling`
或
- `Unstructured`

### 11.4 基础设施建议

- `阿里云 OSS`
- `阿里云 RDS PostgreSQL`
- `Redis`
- `Docker / Docker Compose`
- 后续可演进到 `Kubernetes`

---

## 12. 分阶段学习与重构路线

### Phase 1：标准 RAG 基础设施升级

目标：

- 用 `Milvus` 替换本地向量存储
- 引入 `PostgreSQL`
- 引入 `OSS`
- 完成范围内混合检索

学习重点：

- 向量数据库
- Hybrid Retrieval
- 业务数据与检索数据分层

### Phase 2：从知识树升级到动态范围视图

目标：

- 不再依赖固定知识树
- 构建动态测验范围选择能力

学习重点：

- 检索聚合
- 主题聚类
- 查询结果组织

### Phase 3：多模态知识资产与占位符机制

目标：

- 支持文本、图片、表格、Excel
- 建立资产映射与回查能力

学习重点：

- 多模态解析
- 占位符机制
- 资产元数据设计

### Phase 4：企业级运维与评测

目标：

- 加入追踪、评测、缓存、异步队列

学习重点：

- LangSmith
- OpenTelemetry
- Ragas
- 队列与任务治理

---

## 13. 最适合实习生强化的技术点

如果从“投入产出比”和“简历竞争力”看，最推荐优先掌握：

1. `Milvus + Hybrid Search`
2. `LangGraph 工作流拆分`
3. `OSS + PostgreSQL + Milvus 分层存储`
4. `Docling / Unstructured 多模态解析`
5. `Reranker 与评测`
6. `LangSmith / OpenTelemetry`

---

## 14. 简历与项目表达建议

重构完成后，项目亮点建议这样表达：

- 将 PDF 出题系统重构为 `基于 LangGraph 的企业级 Agentic RAG 学习系统`
- 引入 `Milvus + 混合检索 + Rerank` 提升测验范围内知识召回准确率
- 设计 `动态测验范围视图` 替代固定知识树，适配增量知识库场景
- 构建 `多模态知识资产索引`，支持文本、图片、表格、Excel 的统一检索与关联出题
- 采用 `OSS + PostgreSQL + Milvus` 完成知识资产、元数据和向量索引的企业级分层存储
- 使用 `LangSmith / Ragas` 建立检索与题目生成效果的可观测与评测闭环

---

## 15. 最终结论

本项目最值得学习和重构的方向，不是继续强化“自动生成一棵知识树”，而是完成以下认知升级：

- 从 `静态结构抽取` 升级到 `动态范围组织`
- 从 `文本向量检索` 升级到 `混合检索 + 多模态资产回查`
- 从 `单体功能链路` 升级到 `LangGraph 驱动的企业级工作流`
- 从 `本地轻量存储` 升级到 `OSS + PostgreSQL + Milvus` 分层架构
- 从 `能跑的项目` 升级到 `可观测、可评测、可演进的 AI 应用`

这条路线既符合当前企业级 AI 应用开发实践，也非常适合作为实习阶段的核心项目成长路线。
