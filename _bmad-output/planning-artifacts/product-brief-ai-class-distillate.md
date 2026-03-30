---
title: "Product Brief Distillate: AI-Class"
type: llm-distillate
source: "product-brief-ai-class.md"
created: "2026-03-30"
purpose: "Token-efficient context for downstream PRD creation"
---

# Product Brief Distillate: AI-Class

## Requirements Hints

- Web 前端优先，响应式设计（桌面+移动浏览器）
- 支持 PDF/课件上传，RAG 索引后自动出题
- 题型需覆盖：选择题（MCQ）、填空题、简答题
- 知识点层级组织（课程 → 章节 → 知识点）
- 每题需包含结构化解析：正确理由 + 常见误区 + 关联知识点
- 错题自动归集，支持按知识点薄弱度排序的复习模式
- 内置题库（种子数据）+ 用户上传生成 + LLM 实时生成三种来源
- 部署目标：2C2G 阿里云 ECS

## Technical Context

- **LLM 策略**：使用远程 API（硅基流动/DeepSeek/通义等），不在本地跑大模型
- **向量数据库**：ChromaDB 或 FAISS（内存友好，适合 2GB RAM）
- **Embedding**：使用轻量嵌入模型（如 nomic-embed-text 或 text2vec-chinese）
- **文档处理**：必须使用 lazy loading / generator 模式，避免一次性加载大文件导致 OOM
- **编排框架**：LangChain 或 LlamaIndex
- **后端**：Python（FastAPI 推荐）
- **前端**：待定，但用户倾向 Web
- **Swap 空间**：建议配置 2-4GB swap 作为安全网

## Competitive Intelligence

- **作业帮/小猿搜题**：题库资源丰富但偏 K12，高等教育深度不足，重"出答案"轻"教学理解"
- **Quizgecko/QuestionWell**：从 PDF/笔记生成试题，但缺乏大学专业课深层知识库
- **匡优AI**：侧重从文档生成题目，中文支持
- **Yuxi-Know**：开源可定制，整合知识图谱，但需技术背景维护
- **差异化切入点**：面向大学生专业课，提供"课件绑定 + 知识点关联 + 深度解析"

## Scope Signals

### MVP 必须有
- 文档上传 → RAG 索引 → AI 出题
- 知识点浏览和按知识点刷题
- 答案解析（结构化）
- 错题本 + 复习模式
- 基础 Web UI

### MVP 明确不做
- 微信小程序/原生 App
- 社交/协作功能
- 间隔重复算法（SRS）
- 知识图谱可视化
- 付费/商业化
- 多租户/机构管理

### 未来可能做
- GraphRAG（知识图谱 + RAG 混合检索）
- 间隔重复（Spaced Repetition）
- 学生协作共建课程题库
- 知识图谱可视化
- 移动端适配

## User Profile

- **主要用户**：中国大学生（本科为主）
- **使用场景**：期末考试复习、日常课程练习
- **学科范围**：通用多学科（高数、计算机、经济、法律等）
- **用户技术水平**：普通大学生，不需要技术背景即可使用

## Project Context

- 开发者背景：具备 Python、Java、Agent 开发技能
- 项目目的：AI 开发实习作品集项目，展示 RAG 和多 Agent 编排能力
- 成功标准（当前阶段）：能完整跑起来即可
- 可维护性：高优先级，代码需清晰模块化

## Open Questions

- 前端框架选择：Vue/React/纯 HTML？
- 种子题库数据从哪里获取？开源题库？手动录入？爬取？
- LLM API 具体选择哪家？（成本/质量/速度权衡）
- 知识点层级如何定义？用户自定义 vs 系统推荐？
- 是否需要用户登录/注册系统？
- 文件大小限制？支持哪些格式？（PDF only or also DOCX/PPT?）

## Rejected Ideas (with rationale)

- **本地跑大模型**：2C2G 内存不足，且量化后的小模型质量不够稳定，走 API 更可靠
- **先做小程序**：Web 版开发部署更快、门槛更低，适合 MVP 快速验证
- **只做搜题不做出题**：搜题市场竞争激烈（作业帮等），出题+解析+错题分析是差异化方向
