# Phase 2: Retrieval Quality Enhancements & Evaluation Plan

**日期：** 2026-05-16

基于总体设计方向，以及已完成的 Phase 1 基础设施（PostgreSQL、Milvus、对象存储、父子块元数据与异步 embedding 管道），本文件定义 Phase 2 的目标、范围、技术方案、实验计划与交付产物。

## 目标（Scope）
- 在 Phase 1 基础上提升检索在“用户选定范围内”的准确性与一致性；
- 引入检索聚合、主题聚类与查询增强（Query Rewriting / HyDE）策略的可复现实验；
- 设计并实现重排（Reranker）评估流程与度量；
- 提供可复现的实验脚本、评估基线与成功判据；
- 为 Phase 3（多模态资产）保留必要的数据模型与接口扩展点。

## 成功标准
- 在两类典型任务（概念解释类，事实检索类）上，相比 Phase 1 基线检索，召回精度（Precision@K）提升至少 10%；
- 提供一套可运行的实验套件（research/phase2/）用于复现实验与回归；
- 明确评估文档（research/phase2/results.md）记录方法、超参与结论；
- 变更后系统保持多租户隔离与 Phase 1 的一致性保证。

## 交付物
- .specify/plans/2026-05-16-phase-2-retrieval-quality-and-experiments.md（本文件）
- research/phase2/research.md：决策记录与替代方案对比
- research/phase2/experiments/：包含实验脚本、数据快照、baseline 与结果表
- specs/data-model-changes.md：需要的 DB / Milvus 字段或索引变更建议
- LangGraph 工作流变更草案：specs/langgraph/phase2-updates.md

## 未覆盖（非目标）
- Phase 3 的完整多模态解析与 cell-level 索引不在本阶段实现范围；
- 不强制线上切换生产 Milvus collection（仅实验与小规模灰度）。

## 主要研究问题（Research Questions）
1. 在用户提出的问题下，如何最佳结合 dense + sparse + metadata 以提升短文本/术语召回？
2. Parent-Child chunking 的合并策略（取最高分子块／平均／N 个子块）对下游生成质量的影响？
3. Query Rewriting vs HyDE 在不同题型（定义/计算/推理）上的收益差异与成本权衡？
4. 是否需要在 Milvus 层维护额外的 reranker-ready 字段以降低在线 rerank 成本？

## 技术方案概览

1) 范围约束与检索聚合
- 保持 Phase 1 的范围过滤（tenant_id + scope_hint）；
- 实验将基于三层组合召回：
  - Dense retrieval（Milvus, 文本向量）
  - Sparse retrieval（BM25）并对 chunk 的 title / body_text 执行精确匹配
  - Metadata filter（难度、文档日期、sheet_id 等）
- 组合策略：并行召回后采用 RRF（Reciprocal Rank Fusion）或加权得分融合。

2) 父子块合并策略实验
- 实验候选合并策略：
  - Highest-child：同父下得分最高的子块代表父块（当前 Phase 1 实现）
  - Top-N concat：取父下前 N 子块串联后送入 reranker/LLM
  - Parent-Context：检索 child 后回查 parent 内容并以 Parent 为最终上下文
- 为每种策略设计 A/B 实验并记录召回、重排前后精度与生成质量评价（人工抽样）

3) 查询增强（Query Rewriting 与 HyDE）
- Query Rewriting：使用轻量 seq2seq 模型或 prompt-based 小模型生成检索扩展词与学科术语；
- HyDE：使用小模型生成“假设命中文档”并对该文本进行 embedding 用于 Milvus 检索；
- 实验设计：对比 Baseline / QueryRewrite / HyDE / 两者结合，记录成本（API 调用次数、tokens）与效果。

4) 重排与 Cross-Encoder 评估
- 离线训练或使用现成 cross-encoder（小型模型）作为 reranker；
- 在线路径：先召回（Milvus + BM25）→ top M（例如 50）→ rerank → top K 送入 LLM；
- 实验指标：NDCG@K、Precision@K、Recall@K、latency 与成本估计。

5) 自动化评估与人工评审
- 构建评价集：抽取若干文档、人工标注若干查询的“理想支持片段”；
- 自动指标以与标注支持片段的重合度计分（Precision/Recall/NDCG）；
- 同时进行小规模人工评审（生成题目质量、上下文相关性、完整性）。

## 实验计划与里程碑
- Milestone A（1 周）：搭建实验管道与 baseline 采样数据集（10-20 文档，100-200 查询）；
- Milestone B（2 周）：实现 Dense + Sparse 并行召回与 RRF 融合；完成父子块 Highest-child vs Top-N 基线测试；
- Milestone C（2 周）：集成 Query Rewriting 与 HyDE 的灰度实验；记录成本与效果；
- Milestone D（1 周）：集成 reranker（Cross-Encoder），完成 NDCG 与人工评审；
- Milestone E（0.5 周）：整理结果、编写 research/phase2/results.md 并提交评审。

总耗时预估：6.5 周（含缓冲） — 可拆分为短迭代，每次交付明确实验结果。

## 数据模型与接口变更建议
- Milvus：保留并确保以下字段的可用性与检索效率：chunk_id, parent_chunk_id, tenant_id, scope_hint, body_text, title, embedding_version, dense_vector；考虑为 reranker 预留 summary_vector 或 sparse_vector 字段；
- PostgreSQL：新增表 retrieval_experiments 用于记录实验配置、候选集与评估结果；
- LangGraph：增加 rewrite_query 与 retrieve_hybrid 两个可配置节点的参数化入口以便灰度切换策略。

## 风险与缓解
- 风险：HyDE 与 Query Rewriting 会增加模型调用成本与延迟。缓解：限制在实验环境或仅对低召回场景开启；记录成本并设置阈值自动关闭；
- 风险：大规模 Top-M rerank 导致延迟上升。缓解：先做离线 rerank/离线评估，线上采取 M=50 的保守策略并监控延迟；
- 风险：多租户过滤不严导致信息泄漏。缓解：保留强制 tenant_id filter 单元测试与集成测试。

## 下一步（短期行动项）
1. 在 research/phase2/ 初始化 baseline 数据集与脚本（负责人：核心开发者）；
2. 在代码库中添加 specs/langgraph/phase2-updates.md 草案并提交以便后续实现；
3. 运行首轮 Milestone A 实验并在 research/phase2/research.md 记录初步结论；
4. 根据实验结果决定 Phase 3 的优先级（多模态 asset 回查 vs sheet-level 搜索）。

---

作者：AI 项目组
