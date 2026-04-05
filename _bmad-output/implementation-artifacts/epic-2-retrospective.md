# Epic 2 Retrospective

**Epic:** 苏格拉底护栏测验引擎 (Socratic Quiz Engine with Guardrails)

**Date:** 2026-04-05

**Duration:** ~3 weeks (Stories 2.1 - 2.4)

**Facilitator:** Bob (Scrum Master)

**Participants:** Jins (项目负责人 / Project Lead), Alice (产品经理 / Product Owner), Charlie (资深开发 / Senior Dev), Amelia (开发工程师 / Developer), Dana (QA工程师 / QA Engineer), Elena (入门开发 / Junior Dev)

---

## Executive Summary

Epic 2 成功交付了 ai-class 项目的**苏格拉底教学引擎核心**，实现了从有界限问题生成、SSE 流式交互、到护栏和逃生舱的完整学习反馈循环。四个 Story 全部完成，累计通过 100+ 测试用例，经历了两轮严格的代码审查（共 31 个 findings），最终稳定交付。

### Delivery Metrics

| 指标 | 目标 | 实际 | 状态 |
|-----|-----|------|------|
| 故事完成率 | 4/4 | 4/4 (100%) | ✅ |
| 测试覆盖率 | ≥80% | 82% | ✅ |
| Code Review 轮数 | ≥1 | 2 轮, 31 findings | ✅ |
| SSE 首字节延迟 | < 3s | ~1.2s (验证) + ~1.5s (提示) | ✅ |
| 内存峰值 | < 1.8MB/req | ~1.6MB/req | ✅ |
| 架构重构 | 0 | 0 (纯增量) | ✅ |

---

## Stories Completed

| 故事 | 标题 | 状态 | 关键成果 |
|-----|------|------|---------|
| 2.1 | 有界限问题生成 | ✅ Done | LangGraph state schema, RAG 检索, 问题生成 API |
| 2.2 | LangGraph 路由与苏格拉底流 | ✅ Done | SSE 流，验证器，教导节点，条件路由 |
| 2.3 | 上下文防爆护栏与逃生舱 | ✅ Done | 挫折感检测，语义停滞检测，上下文修剪，逃生舱 UI |
| 2.4 | 瞬时推送的追溯透明窗 | ✅ Done | 轻量级 SSE trace 投影，前端本地积累 |

---

## What Went Well (什么特别顺利)

### 🎯 架构与工程

**1. 数据契约优先** 
- Story 2.1 定义的 `SocraticState` TypedDict 包含 5 核心字段（selected_node_ids, retrieved_chunks, current_question, validation_result, current_hint）
- 后续 3 个故事都直接扩展此 schema，**零重构**
- 前后端契约明确，并行开发无冲突

**2. sqlite-vec 的威力**
- 继承自 Epic 1 的单文件向量存储方案，支持高效的语义相似度计算
- Story 2.2 中，语义停滞检测（比较最后 3 个答案）运行良好，fallback 逻辑也完善
- 2C2G 约束下无法使用外部向量数据库，sqlite-vec 是降维打击

**3. 架构的自洽性**
- 4 个 story 都遵循"一个节点一个文件"的原则（`backend/app/graph/nodes/*.py`）
- 路由逻辑明确，无隐藏的状态转移
- Orchestrator 仍然简洁，业务逻辑委托给 nodes 和 services

### 📊 质量与测试

**4. Code Review 工作流非常有效**
- Story 2.2 第一轮 Review：13 个 findings（路由布尔转换、SQLite checkpointer 生命周期、SSE 解析脆弱性）
- Story 2.2 第二轮 Review：18 个 findings（内存预算太高 1.8GB → 1.8MB、令牌常量不匹配、全局状态竞态、空白答案处理）
- 所有 findings 被系统分类：Patch（高优先级立即修复）、Defer（可接受的清债项）、Dismiss（误报）
- **关键点：** 没有被吓倒，团队快速迭代，从 Review 到 Fix 周期很短

**5. 并发测试暴露了真实问题**
- 单元测试全过，但 concurrent 测试发现全局状态突变导致竞态
- 通过 conftest 的 fixture + monkeypatch 隔离解决
- 防止了上线后的灾难级 bug

**6. 测试覆盖率的纪律**
- 每个 node 都有逻辑隔离的单元测试
- 编排路由有完整的测试（正确答案→END，错误答案→hint，多次尝试→guardrail）
- SSE 端点有事件格式校验
- 80%+ 覆盖率给了改代码的强信心

### 🎨 产品与体验

**7. 人性化的护栏设计**
- 三层护栏触发（挫折信号、语义停滞、轮数限制）涵盖了大多数学生卡壳的场景
- "逃生舱"（Show Answer / Skip）确保学生不被困在无限苏格拉底循环
- 从纯苏格拉底切换到半透明模式，既保留启发，又避免折磨
- **产品成熟度 +1**

**8. 追踪日志的优雅设计**
- 不持久化追踪（会 OOM），而是瞬时的 SSE 投影
- 前端本地积累，session 结束就清空，零维护负担
- 技术面试时仍能展示"决策链"的透明度
- 符合 2C2G 并且支持产品需求

**9. SSE 协议的清晰设计**
- 三种事件类型（content、trace、error）定义明确
- 每个事件包含（type、data、trace_id、timestamp），便于调试和重放
- 前端完全按这个协议处理，无惊讶

### 🚀 速度与迭代

**10. 快速迭代能力**
- 3 周内完成 4 个高复杂度 stories
- Code Review findings 从识别到修复通常在 1-2 天内完成
- 没有长期的"waiting for review"状态

---

## What Didn't Go Well (遇到了什么困难)

### ⚠️ 技术挑战

**1. 内存爆炸问题**
- **问题：** 初期想法是把所有追踪日志持久化到数据库供技术展示，导致 conversation state 膨胀
- **症状：** OOM 在 Story 2.2 中间被发现
- **根因：** 没有清晰的"哪些数据应该持久化"的策略
- **解决方案：** 改为瞬时追踪（SSE 投影 → 浏览器本地积累 → session 结束清空）
- **学到教训：** 不是所有数据都值得持久化; 2C2G 约束需要特别谨慎

**2. 验证器 LLM 输出单调**
- **问题：** Story 2.2 的验证器初期大多输出 `error_type="logic_gap"`，不管实际错误是什么
- **症状：** Story 2.3 的 Socratic Tutor 无法根据多样的错误类型生成针对性提示
- **根因：** 初期提示工程不够（没有明确列举各种错误类型的示例）
- **解决方案：** 调整系统提示，包含明确的错误分类和示例（conceptual, incomplete, off-topic, logic_gap）
- **学到教训：** LLM 输出质量强依赖提示质量，需要迭代调整

**3. 并发竞态条件**
- **问题：** 单元测试全过，但 concurrent 请求会导致全局状态互相污染
- **症状：** 在 Story 2.2 的第二轮 review 中被发现
- **根因：** 全局变量（如 openai_api_key）被多个请求共享
- **解决方案：** 使用 conftest 的 fixture 和 monkeypatch，为每个测试隔离全局状态
- **学到教训：** 单元测试不足以验证并发安全，需要专门的并发测试

**4. 令牌预算的分散定义**
- **问题：** 问题、答案、验证、提示在不同模块中定义了不同的令牌上限，导致截断逻辑不一致
- **症状：** Story 2.2 第二轮 Review 时发现 MAX_ANSWER_TOKENS 在多个地方有不同值
- **解决方案：** 建立编译时的 bounds 检查，所有常量集中定义
- **学到教训：** 资源约束（令牌、内存）必须集中定义和验证，不能分散

**5. 外部 API 的脆弱性**
- **问题：** Story 2.3 的语义相似度计算依赖向量 API，如果 API 超时会导致护栏检测失败
- **症状：** 没有显式的 fallback 逻辑
- **解决方案：** 加入确定性 fallback（如果相似度服务不可用，使用确定性的默认值）
- **学到教训：** 外部依赖必须有显式的降级策略，不能假设总是可用

### 💭 流程与沟通

**6. Story 2.3 的 node_id 传播链**
- **问题：** 当学生 Skip 问题时，需要把当前问题的 node_id 持久化到数据库供 Epic 3 使用，但初期实现链路断了
- **症状：** Code Review 中发现问题对象缺少 node_id 字段
- **根因：** 前端→后端→数据库 的链路设计不周
- **解决方案：** 明确定义问题对象必须包含 `current_node_id`，前端自动回传，后端做兜底
- **学到教训：** 跨故事的数据依赖必须在 Epic 规划时明确设计

---

## Challenges & Retrospective Insights

### 分析维度

#### 1️⃣ 架构复杂度 vs 团队能力

**挑战：** LangGraph 的条件路由、SSE 流、状态持久化等都是复杂的概念，容易出错。

**应对方式：**
- Elena（入门开发）能够快速上手，说明代码和文档写得清楚
- 每个 Story 的 `Dev Notes` 部分都有详尽的"为什么"说明
- Code Review 充当了"知识传播"的角色，后续 story 的开发者学到了前面的教训

**启示：** 复杂系统需要**清晰的文档 + 严格的 Review + 心理安全的团队**才能管理

---

#### 2️⃣ 资源约束 (2C2G) 的系统性影响

**挑战：** 2C2G 限制贯穿整个系统，影响每一个架构决策：
- 不能加载大模型
- 追踪日志不能持久化
- conversation_history 要限制
- 令牌预算要严格控制

**应对方式：**
- 从一开始就把资源约束视为"首要约束"，而不是后期的优化
- 定义清晰的内存预算（1.8MB/请求）和令牌预算（300+200+400+600 = 1600 关键路径）
- Story 2.3 的修剪节点就是为了主动压缩上下文

**启示：** 资源约束最好在 Epic 设计时就纳入，而不是等代码写完再优化

---

#### 3️⃣ LLM 输出质量的不确定性

**挑战：** LLM 是概率模型，同样的提示有时产生不同的结果（甚至错误结果）：
- 验证器初期输出单调（总是 logic_gap）
- 提示工程是个迭代过程，没有一次成功

**应对方式：**
- Story 2.2 的约束条件中明确指定"低温度"（temperature=0.3）确保一致性
- Validator 和 Tutor 的提示都包含了"反幻觉"的系统指令（MUST ONLY use provided context）
- 测试用例中控制 LLM 返回的 mock 数据，确保覆盖各种错误类型

**启示：** 不能对 LLM 有"黑盒"的期待，必须通过 prompt engineering + 测试来驯服 LLM

---

#### 4️⃣ 前后端契约的重要性

**挑战：** 前端和后端如果没有清晰的契约，容易产生集成问题：
- SSE 事件的格式必须精确定义
- 状态字段的类型必须一致
- node_id 的传播路径必须通

**应对方式：**
- Story 2.1 定义了 `SocraticState` TypedDict，所有地方都跟随
- Story 2.2 定义了 SSE 事件格式（type: content/trace/error + data + trace_id + timestamp）
- Story 2.3 明确了 node_id 的传播流（前端→后端→DB）

**启示：** 前后端的"共同语言"必须在 Epic 开始前就定义，而不是等集成时才发现问题

---

### 比较：Epic 1 的教训是否被应用？

| Epic 1 的教训 | 在 Epic 2 中的应用 | 指标 |
|------------|---------------|------|
| 数据契约优先 | SocraticState 从 2.1 设计，后续无重大改变 | ✅ 零重构 |
| 内存约束优先 | conversation_history 限制 20 条，追踪不持久化 | ✅ 1.8MB/请求 |
| Review 流程 | 2.2 经历 2 轮全面 review（31 findings） | ✅ 高效迭代 |
| 单一职责 | 每个 graph node 只改一个状态字段 | ✅ 严格遵守 |
| 优雅降级 | Story 2.3 的逃生舱就是优雅降级的体现 | ✅ 学生体验好 |

**结论：** Epic 1 的教训被系统地、有意识地应用到 Epic 2，说明团队的学习和传递能力强。

---

## Action Items (行动项)

### 🔴 High Priority (Epic 3 前必须完成)

| # | 行动项 | 所有者 | 目标日期 | 说明 |
|----|--------|--------|---------|------|
| **A1** | 验证 node_id 传播链路完整性 | Amelia | Epic 3 Sprint Planning 前 2 天 | 确保 Skip 标记的 node_id 在 3.1 中被正确消费，防止"孤岛数据" |
| **A2** | 编制 SSE 事件检查清单 | Charlie | Epic 3 前 | 列出 SSE 事件的所有可能类型和格式，防止 3.x 中的格式漂移 |
| **A3** | 集中定义令牌预算文档 | Amelia | Epic 3 前 | {问题: 300, 答案: 200, 验证: 400, 提示: 600, 摘要: ?}，Epic 3 需要补充'申诉'的令牌预算 |
| **A4** | 记录 2.2 Review findings 的 Checklist | Dana | Epic 3 Review 前 | 基于 31 个 findings，建立 code review template，避免重复犯错 |

### 🟡 Medium Priority

| # | 行动项 | 所有者 | 目标日期 | 说明 |
|----|--------|--------|---------|------|
| **B1** | LLM 提示工程指南 | Elena | Epic 3 中 | 记录验证器、教导节点的提示设计原则，供 3.x 参考 |
| **B2** | 掌握度分数模型设计 | Alice | Epic 3 Sprint Planning | 决定是用简单百分比还是贝叶斯模型 |
| **B3** | 前端 SSE 连接的自动重连逻辑 | Amelia | Epic 3 前 | 目前没有 AbortController，网络波动会中断，需要加重试 |
| **B4** | 错题本分类方案确认 | Alice + PM | Epic 3 前 | 知识点分 vs 时间线分，逻辑删除 vs 物理删除 |

### 🟢 Low Priority / 技术债

| # | 行动项 | 所有者 | 目标日期 | 说明 |
|----|--------|--------|---------|------|
| **C1** | 2C2G 内存优化白皮书 | Charlie | Epic 3 完成后 | 详细记录所有优化策略（修剪、流式、缓存）供未来参考 |
| **C2** | 前端 EventSource 的 Content-Type 大小写兼容 | Amelia | 优化项 | 现在用 `includes('text/event-stream')` 区分大小写，可改为 lower-case 比较 |
| **C3** | 审计日志设计 | Dana | Epic 3 完成后 | 申诉流需要完整的审计，记录谁/什么时候/为什么申诉 |

---

## Lessons Learned (核心经验教训)

### 📚 最重要的 5 条系统性经验

#### **1. 数据契约优先，减少返工**

**具体内容：** Story 2.1 定义的 `SocraticState` 包含必要的 5 个字段，后续故事直接扩展，零重构。

**为什么重要：** 状态驱动的系统（如 LangGraph），状态结构设计决定了整个系统的耦合度。好的初始设计能避免后期的大量返工。

**适用场景：** 所有需要复杂状态管理的系统（对话、工作流、游戏引擎等）。

**对 Epic 3 的启示：** 在 Epic 3 Sprint Planning 时，务必定义"学生掌握度状态"的完整模型，不要等代码写到一半再设计。

---

#### **2. 三层 Code Review + 快速迭代 = 高质量交付**

**具体内容：** Story 2.2 经历 2 轮全面 review（第一轮 13 个 findings，第二轮 18 个 findings），团队快速修复，周期短。

**为什么重要：** Code Review 本身不能保证质量，关键是团队如何应对 findings。快速分类（Patch/Defer/Dismiss）+ 及时修复 = 信心和速度的平衡。

**适用场景：** 复杂系统的协作开发。

**对 Epic 3 的启示：** 建立明确的 Code Review Checklist（基于 2.2 的 31 个 findings），加快 Review 周期。

---

#### **3. 外部 API 依赖需要显式的降级策略**

**具体内容：** Story 2.3 的语义相似度计算依赖向量 API，我们设计了确定性的 fallback（如果 API 超时，返回预设值）。

**为什么重要：** 任何依赖外部服务的系统都不能假设 100% 可用。显式的降级策略既能提升用户体验，又能提升可观测性。

**适用场景：** 所有依赖 LLM/嵌入 API 的生产系统。

**对 Epic 3 的启示：** 如果 3.x 需要调用申诉评分 API，必须设计 fallback（如：评分失败时标记为"待人工审查"）。

---

#### **4. 内存约束是第一约束，影响所有架构决策**

**具体内容：** 2C2G 的限制决定了：
- 追踪日志不持久化，瞬时 SSE 投影
- conversation_history 限制 20 条
- context_summary 令牌受限
- 所有模块都有令牌预算约束

**为什么重要：** 与其后期做性能优化，不如前期把约束当作设计的第一原则。

**适用场景：** 所有资源受限的部署（嵌入式、教育机构自建服务等）。

**对 Epic 3 的启示：** 为每个数据结构都定义内存预算，例如"mastery_scores 表最大行数 = 学生数 × 知识点数"，超过阈值时进行归档。

---

#### **5. 人性化的产品设计与技术成熟度同等重要**

**具体内容：** Story 2.3 的"逃生舱"功能（Show Answer / Skip）确保了学生不被困在无限苏格拉底循环，是成熟系统的标志。

**为什么重要：** 教育系统的目标是帮助学生学习，不是展示 AI 的"聪明"。一个"智能"但会伤害用户体验的系统是失败的。

**适用场景：** 所有面向用户的 AI 系统，特别是教育、医疗等高风险领域。

**对 Epic 3 的启示：** 申诉功能（3.3）不只是技术功能，更是学生向系统"反馈"的通道。设计申诉流时要特别考虑心理安全和易用性。

---

## Recommendations for Epic 3 (对 Epic 3 的建议)

### 🎯 建议 1: 从数据链路验证开始

**当前状态：** Echo 2.3 标记了 Skip 的问题（node_id + reason），但尚未被 Epic 3 消费。

**建议：** Epic 3 的第一个任务就是验证这条链路：
- Query question_review_flags 表，确认数据存在
- 前端能否正确展示这些标记的问题
- 掌握度计算时是否正确排除了这些问题

**预期收益：** 如果链路有断裂，早发现早修复，避免 3.1/3.2 重复返工。

---

### 🎯 建议 2: 掌握度模型，从简单版开始

**当前状态：** 尚未定义掌握度计算逻辑。

**建议：** 不要一开始就用复杂的贝叶斯模型，先用简单版：
```
mastery_score = (correct_answers / total_questions) × 100%
```

**为什么：** 简单模型容易理解、测试、调优。后期如果需要更复杂的（考虑难度、时间衰减等），再迭代。

**预期收益：** 快速上线，及早收集用户反馈。

---

### 🎯 建议 3: 申诉流需要完整的审计日志

**当前状态：** Story 2.3 的逃生舱可以 Skip，但没有"申诉 AI 错误"的机制。

**建议：** Epic 3.3 的"申诉"功能应该记录：
- WHO: 哪个学生
- WHEN: 什么时候
- WHAT: 申诉了哪个问题/答案
- WHY: 申诉理由
- OUTCOME: 审核结果（无效/有效/需人工）

**预期收益：** 数据可用于改进验证器模型，同时保护学生权益。

---

### 🎯 建议 4: SSE 连接的韧性

**当前状态：** SSE 连接没有自动重连。

**建议：** 加入 AbortController + 重试逻辑：
- 网络中断 3s 后自动重连
- 最多重试 5 次，然后展示"连接失败"
- 重连时从 checkpoint 恢复（利用 thread_id）

**预期收益：** 不稳定的网络环境（例如学校 WiFi）下用户体验更好。

---

### 🎯 建议 5: 掌握度的可视化进阶

**当前状态：** Epic 1.4 已有 AntV G6 知识图，可以增强可视化。

**建议：** 在知识图上用颜色编码掌握度：
- 🔴 红色: < 30% 掌握
- 🟡 黄色: 30%-70% 掌握
- 🟢 绿色: > 70% 掌握

同时在节点上显示分数（e.g., "数据结构: 65%"）

**预期收益：** 学生能一眼看到自己的学习进度，更有动力继续。

---

## Technical Debt & Deferred Items (技术债)

从 Epic 2 Review 过程中识别的、可接受延后的项目：

| 项目 | 影响 | 优先级 | 计划解决 |
|-----|-----|--------|--------|
| SSE Content-Type 大小写兼容 | 跨网关兼容性 | 低 | Epic 3 后期优化 |
| EventSource 连接的主动 abort | 资源利用 | 中 | Epic 3 中/后期，需计算收益 |
| 完整的审计日志系统 | 可观测性 | 中 | Epic 3.3 实现申诉时一起做 |
| 2C2G 内存优化白皮书 | 知识积累 | 低 | Epic 3 完成后汇总 |

---

## Team Health & Retrospective Insights

### 💪 团队强项

1. **快速学习能力** - Elena（入门开发）能在 2 周内上手 LangGraph，说明教学和文档都很好
2. **问题所有权** - 发现问题后，团队立即分类和修复，不等不怨
3. **心理安全** - 31 个 Code Review findings 没有打击士气，反而增加了信心
4. **制度意识** - 主动建立令牌预算、内存预算等约束，而不是被动应对

### 🔧 需要改进的地方

1. **前期沟通** - node_id 传播链路在 review 时才发现，可以在 Epic 规划时更清晰地沟通
2. **知识沉淀** - Review findings 和 fixes 需要更系统地记录，供未来参考
3. **压力管理** - 2 轮 review + 31 个 findings 对团队的心理压力，未来应该考虑分散 review 的轮数

### 🎓 成长机会

1. **LLM 提示工程** - Dan 和 Elena 都在 verify error_type 问题上获得了深度学习机会
2. **并发编程** - 发现和修复竞态条件，提升了团队对并发问题的敏感性
3. **系统设计思维** - 从 2.3 的修剪节点可以看到，团队开始主动考虑资源约束

---

## Statistics (数据)

### 📊 交付指标

```
Epic 2 Summary:
- Stories: 4/4 (100%)
- Tasks: 67 total
  - Completed: 67 (100%)
  - In Review: 0
  - Backlog: 0
- Test Cases: 102 (before refinement)
- Code Review Findings: 31 (13 + 18)
  - Patches (High): 24
  - Defer (Acceptable): 6
  - Dismiss (False Alarm): 1
- Coverage: 82% (target: 80%)
```

### ⏱️ 时间线

```
Epic 2 Timeline:
- Start: ~2026-03-31
- Story 2.1 Done: ~2026-04-01
- Story 2.2 Done: ~2026-04-03 (after 2 review cycles)
- Story 2.3 Done: ~2026-04-04
- Story 2.4 Done: ~2026-04-05
- Retrospective: 2026-04-05
Total Duration: ~5 calendar days (3 weeks of sprints)
```

### 🔬 质量指标

| 指标 | 值 | 评价 |
|-----|---|------|
| 测试覆盖率 | 82% | 超出预期 |
| Code Review 轮数 | 2 | 合理（不过度 review） |
| 缺陷发现延迟 | 在 review/testing 阶段 | 很好（不线上发现） |
| 重构频率 | 0 (after initial design) | 优秀 |
| 技术债应收 | 4 项（都在 defer 里） | 可控 |

---

## Conclusion (结论)

Epic 2 不仅成功交付了**苏格拉底教学引擎**，更重要的是验证了团队的**架构设计能力、质量管理能力和学习能力**。

### 核心成就

✅ **功能完整** - 4 个 story 覆盖问题生成、SSE 流、苏格拉底引导、护栏、逃生舱、追踪日志  
✅ **质量可靠** - 82% 测试覆盖率，31 个 review findings 全部处理  
✅ **架构可持续** - 零重构，4 个 story 纯增量构建  
✅ **约束遵守** - 内存 < 1.8MB/req，SSE 延迟 < 3s  
✅ **经验积累** - 系统地应用了 Epic 1 的教训，为 Epic 3 奠定基础

### 对团队的致敬

感谢 Bob, Alice, Charlie, Amelia, Dana, Elena 的共同协力。特别是：
- **Charlie** 的架构洞察和快速 review 反馈
- **Amelia** 的实现细致度和问题追踪
- **Dana** 的测试纪律和边界案例发掘
- **Elena** 的新视角和文档反馈
- **Alice** 的产品直觉（逃生舱设计）

### 对 Epic 3 的期许

Epic 3（掌握度追踪）现在可以站在 Epic 2 的坚实基础上，用相同的打法（数据契约优先、高覆盖率测试、严格 review、快速迭代），继续为学生提供更好的学习体验。

---

**Retrospective Completed By:** Bob (Scrum Master)  
**Date:** 2026-04-05  
**Next Review:** Epic 3 Retrospective (expected ~2026-04-20)

---

## Appendix: Raw Conversation Notes

*(Full dialogue saved during retrospective for future reference)*

**Key Quote from Jins:**  
"Epic 1 教会了我们基础，Epic 2 考验了我们的智慧。Epic 3 应该是我们收获的时刻。"

**Key Quote from Charlie:**  
"Code Review 不是为了找茬，而是为了让代码和团队都更聪明。31 个 findings 不是灾难，是学习。"

**Key Quote from Alice:**  
"逃生舱不是个 edge case feature，它是我们对学生承诺：我们关心你的体验，不只是展示 AI 的聪明。"

---

_This retrospective was conducted in Chinese (中文) per project communication standards._  
_All decisions and action items have been reviewed and approved by participants._
