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
- 支持多租户隔离与租户级检索过滤
- 支持 LLM Token 追踪、成本统计与模型降级
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

### 4.7 模型网关与 LLM Ops 层

技术推荐：

- `统一模型调用封装`
- 可选 `LiteLLM` 作为模型网关
- `LangChain Runnable with_retry / with_fallbacks`

职责：

- 统一接入多家模型供应商
- 记录输入输出 Token 与调用成本
- 实现主模型失败后的自动降级
- 管理配额、限流、重试和熔断策略
- 为不同工作流选择不同档位模型

设计原则：

- 模型调用入口必须收敛到统一网关或统一适配层
- 工作流不直接耦合具体模型供应商
- 所有模型调用都应带有 trace_id、tenant_id 和 usage metadata
- 主模型、降级模型、兜底模型需要可配置

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
2. 系统先做 `范围意图理解（Scope Intent Understanding）`
3. 根据最近上传文档、关键词、主题标签、章节元数据召回候选资产
4. 将候选结果聚合为若干主题簇或目录项
5. 生成可供前端展示的范围视图
6. 用户选择一个或多个范围后，系统仅在该范围内执行检索与出题

### 5.5 范围意图理解（Scope Intent Understanding）

范围意图理解发生在：

`范围视图生成之前`

它的目标不是直接生成最终检索 query，而是帮助系统判断：

- 用户想练习哪个主题
- 用户更偏向哪类知识资产
- 应优先展示哪些主题簇、目录项、sheet、表格或文档

典型输入：

- “我想练矩阵乘法”
- “只考第二章公式”
- “复习这次上传 Excel 里的利润表分析”

典型输出：

- 推荐主题簇
- 推荐目录节点
- 推荐文档集合
- 推荐 sheet / 表格范围
- 默认勾选的候选测验范围

设计要求：

- 这一阶段服务于 `Scope View Builder`
- 可以使用轻量模型或规则+模型混合方式
- 输出结果应尽量结构化，避免直接把自然语言结果传给前端
- 若用户没有显式输入意图，则退化为基于知识库热点、最近上传和主题聚类生成默认范围视图

### 5.6 模块命名建议

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

### 6.5 表格与 Excel 的多模态检索增强

表格与 Excel 不应只被视为“可导出的附件”，而应被视为可检索知识单元。

推荐补充以下能力：

- 将 `sheet` 作为一类独立知识资产
- 将 `sheet_id` 绑定到 chunk 元数据，支持 chunk 到 sheet 的反向定位
- 对表格生成结构化摘要，保留标题、列名、单位、关键行列关系
- 对公式单元格提取依赖关系，构建 `formula_dependency` 元数据
- 在需要高精度检索时支持 `cell-level retrieval`

推荐的层级设计：

- `workbook`
- `sheet`
- `table_region`
- `row / column summary`
- `cell`

推荐的索引策略：

- `sheet-level vector`：适合主题级召回
- `table summary vector`：适合语义检索
- `cell text / formula sparse index`：适合精确值、列名、公式查找

说明：

- `cell-level vectorization` 会显著增加索引体积和成本，因此建议只对重点 sheet 或重点区域开启
- 公式依赖关系更适合作为结构化元数据或图关系存储，而不是单独依赖 embedding
- 对表格类题目，可在生成前先回查 sheet、表头和公式依赖，再补充给模型

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
- tenant 过滤字段

推荐结合：

- `Milvus Hybrid Search`
- `Milvus Multi-Vector Search`
- Rerank 策略

### 8.5 Advanced RAG 策略补充

除了 Hybrid Search 和 Rerank，推荐补充以下在真实落地中非常有效的策略：

#### Parent-Child Chunking / 父子块检索

设计思路：

- 切分时同时生成 `Parent Chunk` 和 `Child Chunk`
- 向量索引主要建立在 `Child Chunk` 上
- 检索命中后，通过 `parent_id` 回查更大上下文
- 最终送入模型的是 Parent 或 Parent + 邻接块，而不是碎片化 Child

适用价值：

- 提升召回精度
- 减少上下文碎片
- 特别适合教材、讲义、图文混排页面和 Excel sheet 摘要块

推荐实现：

- `ParentDocumentRetriever`
- 自定义 `parent_id` / `child_id` 双层索引

#### Query Rewriting / 查询重写

设计思路：

- 用户选择测验范围后，原始查询往往很短或很模糊
- 在正式检索前，先用一个轻量模型补全查询意图
- 生成更适合 Milvus 检索的查询表达

适用价值：

- 提升召回率
- 提升术语匹配率
- 减少因为用户表达不完整导致的漏召回

推荐改写内容：

- 学科术语补全
- 同义词扩展
- 题型偏好补全
- 范围约束补全

#### HyDE / 假设文档嵌入

设计思路：

- 先让小模型生成一段“理想命中内容”的假设文档
- 再对该假设文档做 embedding 并用于检索

适用价值：

- 适合原始 query 很抽象、很口语化的情况
- 对概念解释类和问答题生成前检索尤其有效

说明：

- Query Rewriting 和 HyDE 不必同时默认开启
- 推荐先上线 Query Rewriting，再在低召回场景中灰度增加 HyDE

边界说明：

- `Scope Intent Understanding` 用于范围视图生成前的候选范围组织
- `Query Rewriting` 用于范围选定后的正式检索
- 两者都属于“意图理解”，但服务的业务阶段不同，不应混用

### 8.6 多租户检索隔离

在引入多用户后，检索层必须保证租户隔离。

推荐原则：

- 每条向量记录必须具备 `tenant_id`
- 检索时必须附带 `tenant_id == current_tenant` 过滤条件
- 私有知识库严禁跨租户混检

Milvus 设计建议：

- 若使用支持 Partition Key 的版本，可优先将 `tenant_id` 设计为 Partition Key
- 在高租户数场景下，可结合 `tenant_id + knowledge_base_id` 做更细粒度过滤
- 对共享公共知识库与私有知识库，建议使用独立 collection 或显式 `visibility_scope`

这部分是根据 Milvus 官方文档中关于 `Partition Key` 和多租户场景的说明做出的设计建议：Milvus 明确支持将特定标量字段设为 Partition Key，并在检索时通过过滤条件缩小搜索范围；其文档也明确提到可以将租户相关字段作为多租户隔离方案的一部分。这一条是基于官方能力做出的架构推断。 

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
- `llm_usage_logs`
- `model_fallback_events`

多租户要求：

- 所有核心业务表必须包含 `tenant_id`
- 用户级私有空间可进一步增加 `user_id`
- 所有查询默认带上 `tenant_id` 过滤条件
- 共享知识库与私有知识库需要通过 `visibility_scope` 或独立表策略显式区分

Token 与成本追踪要求：

- 对每次模型调用记录 `input_tokens`
- 对每次模型调用记录 `output_tokens`
- 记录 `total_tokens`
- 记录 `provider`
- 记录 `model_name`
- 记录 `unit_cost`
- 记录 `estimated_cost`
- 记录所属 `workflow_name`
- 记录 `trace_id`

### 9.2 Milvus collection 设计

每个检索单元建议具备以下字段：

- `tenant_id`
- `user_id`
- `chunk_id`
- `document_id`
- `scope_id`
- `node_or_topic_id`
- `sheet_id`
- `parent_chunk_id`
- `text`
- `dense_vector`
- `sparse_vector`
- `asset_refs`
- `subject`
- `difficulty`
- `created_at`

多租户建议：

- 优先使用 `tenant_id` 作为逻辑隔离主字段
- 若 Milvus 版本与部署方式允许，优先评估将 `tenant_id` 设为 `Partition Key`
- 检索表达式必须显式带上 `tenant_id`

多模态表格建议：

- 对表格摘要块记录 `sheet_id`
- 对单元格级检索记录 `cell_ref`
- 对公式单元格记录 `formula_ref` 与 `dependency_refs`

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

`load_from_oss -> parse_document -> extract_assets -> build_placeholders -> parent_child_chunking -> embedding -> milvus_upsert -> postgres_upsert -> cache_refresh`

### 10.3 范围视图构建工作流

流程建议：

`collect_user_goal -> understand_scope_intent -> collect_candidate_assets -> cluster_topics -> build_scope_view -> cache_scope_view`

说明：

- `understand_scope_intent` 用于在生成范围视图前理解用户目标
- 该节点的输出用于影响候选资产召回、主题聚类和默认展示顺序
- 这一阶段不负责最终检索 query 的重写

### 10.4 出题工作流

流程建议：

`resolve_scope -> rewrite_query -> retrieve_hybrid -> rerank -> hydrate_parent_context -> hydrate_assets -> build_prompt -> generate_question -> validate_output`

说明：

- `resolve_scope` 表示范围已经由用户选定
- `rewrite_query` 发生在范围确定之后、正式检索之前
- 该节点只优化范围内检索效果，不负责生成范围视图

### 10.5 答题评估工作流

流程建议：

`validate_answer -> retrieve_supporting_context -> evaluate_answer -> generate_feedback -> persist_attempt`

### 10.6 LLM 调用治理工作流

流程建议：

`select_model_policy -> invoke_primary_model -> retry_if_transient -> fallback_if_needed -> collect_usage_metadata -> persist_usage_log`

核心要求：

- 主调用失败时允许自动切换到降级模型
- 仅对限流、网络抖动、临时供应商故障启用重试
- 对业务错误和提示词错误不应盲目重试
- 每次调用结束后统一落库 usage metadata

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
- 可选 `LiteLLM`

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

### 11.5 LLM Ops 与模型网关建议

- `统一模型配置中心`
- `LangChain with_retry / with_fallbacks`
- 可选 `LiteLLM Proxy`
- 成本统计与预算告警
- 模型级限流与配额控制

适用场景：

- 同时接入 `DeepSeek / Qwen / OpenAI` 等多供应商
- 需要主模型失败后自动切换
- 需要按租户、项目、用户统计成本

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
- 引入 sheet 级与可选 cell 级检索

学习重点：

- 多模态解析
- 占位符机制
- 资产元数据设计
- 表格与公式依赖建模

### Phase 4：企业级运维、LLM Ops 与评测

目标：

- 加入追踪、评测、缓存、异步队列、模型降级与成本治理

学习重点：

- LangSmith
- OpenTelemetry
- Ragas
- 队列与任务治理
- Token 成本统计
- 模型网关与 fallback 策略

---

## 13. 最适合实习生强化的技术点

如果从“投入产出比”和“简历竞争力”看，最推荐优先掌握：

1. `Milvus + Hybrid Search`
2. `LangGraph 工作流拆分`
3. `OSS + PostgreSQL + Milvus 分层存储`
4. `Docling / Unstructured 多模态解析`
5. `Reranker 与评测`
6. `LangSmith / OpenTelemetry`
7. `LLM Fallback 与成本治理`

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
