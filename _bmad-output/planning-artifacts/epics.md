---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
inputDocuments: ["_bmad-output/planning-artifacts/prd.md", "_bmad-output/planning-artifacts/architecture.md"]
---

# ai-class - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ai-class, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Users can upload PDF materials and see real-time processing status.
FR2: System validates file size/format specifically for 2C2G resource limits.
FR3: System extracts a structured hierarchy of knowledge points and indexes them for RAG.
FR4: Users can preview the extracted concept outline and MUST interactively select specific scope/nodes before starting a quiz to bound constraints.
FR5: System generates Multiple Choice and Short Answer questions grounded in source content.
FR6: System provides step-by-step Socratic hints upon incorrect answers.
FR7: System verifies user reasoning through the guided dialogue.
FR8: System organizes incorrect answers in a "Wrong-Answer Notebook" by knowledge point.
FR9: System tracks user mastery levels per concept based on performance.
FR10: System Trace Visibility: Technical users can access a "Trace Log" showing the reasoning chain and internal hand-offs between orchestrator and agents.
FR11: System utilizes dialogue threshold pruning and an explicit "Escape Hatch" to exit infinite Socratic loops.
FR12: System includes a user "Appeal/Error Flagging" channel to remove hallucinated AI questions from mastery tracking data.

### NonFunctional Requirements

NFR1: Server constraints: 2C2G (2GB RAM) resource limits. Memory cap < 1.5GB for backend processes.
NFR2: Efficiency: Indexing 50p PDF < 30s.
NFR3: Response Latency: < 3s starting latency for initial hint delivery setup via external APIs.
NFR4: Modernity: Exclusive support for Chrome/Edge/Safari latest versions; no legacy polyfills.
NFR5: Architecture: Use Vue 3 + Vite CSR architecture to offload computation to the client.
NFR6: Security: Strict per-user session isolation for uploaded materials and logs.
NFR7: Compliance: Adherence to FERPA/COPPA principles for student data privacy.
NFR8: Accessibility: Target WCAG 2.1 AA compliance for core study interfaces.

### Additional Requirements

- Starter Template Required (Epic 1 Story 1): Custom Lean Full-stack (Vue 3 TS + FastAPI + LangGraph).
- Initialization commands: `npm create vite@latest frontend -- --template vue-ts` and `pip install fastapi uvicorn langgraph langchain-openai sqlite-vec pydantic-settings python-multipart PyMuPDF`.
- Infrastructure setup requirement: Single VM Docker-Compose (Frontend container + Backend container + SQLite Volume) in a 2C2G environment.
- Data Storage requirement: SQLite (Version: 3.45+) with sqlite-vec (Version: 0.1.0+) local database file.
- State Engine requirement: LangGraph with SQLite Checkpointer for conversational state persistence.
- Integration requirement: Server-Sent Events (SSE) for both AI conversational content (`type: content`) and graph trace logs (`type: trace`).
- Knowledge Graph visualization: AntV G6 (Version 5.0+).
- Single-Worker Task Queue: Epic 1 MUST implement a lightweight concurrency controller (max 1 parallel upload processing) to explicitly prevent OOM events on 2C2G architecture, returning queue position to overflow users.

### UX Design Requirements

N/A (No standalone UX Design document found - rely on PRD and general mobile-first TailwindCSS definitions)

### FR Coverage Map

FR1: Epic 1 - Upload PDF and real-time processing status
FR2: Epic 1 - File size/format constraints for 2C2G
FR3: Epic 1 - RAG indexing & structural extraction
FR4: Epic 1 - Extracted outline preview & explicit scope selection mapping
FR5: Epic 2 - Generated contextual questions
FR6: Epic 2 - Step-by-step Socratic hints via SSE
FR7: Epic 2 - User reasoning verification in guided dialogue
FR10: Epic 2 - System trace visibility (Trace Log) for technical observing
FR11: Epic 2 - Memory pruning mechanism & Escape Hatch loop prevention
FR8: Epic 3 - Wrong-Answer Notebook organization
FR9: Epic 3 - Mastery point tracking based on clean data
FR12: Epic 3 - User feedback mechanism protecting mastery state from AI hallucinations

## Epic List

### Epic 1: 课件解析、边界圈选与高可用并发控制 (Course Material, Processing Queue & Scope Selection)
**User Outcome:** 用户不仅能将 PDF 转化为知识图谱结构，而且系统即便在多用户同时上传时也能通过“单排队列控制”稳定返回等待名次；解析完毕后，用户可通过交互界面圈选需要测验的具体章节（解决冷启动并收缩上下文范围）。
**FRs covered:** FR1, FR2, FR3, FR4

### Epic 2: 苏格拉底护栏测验引擎 (Socratic Quiz Engine with Guardrails)
**User Outcome:** 用户基于前置圈选的内容发起深度测验。通过 LangGraph 实现状态跳转与苏格拉底暗示。同时加入隐性“多轮记忆清理”和显性“逃生舱求助”按钮，避免系统被用户的死缠烂打拖入幻觉和 OOM 崩溃。提供“追溯日志”用于面试秀技术。
**FRs covered:** FR5, FR6, FR7, FR10, FR11

### Epic 3: 净水池掌握度追踪 (Clean Mastery Tracking & Wrong-Answer Review)
**User Outcome:** 用户获得可视化的错题本及按知识点的掌握度画像。同时附带了一个“AI 判错上诉”功能，能够将引发幻觉或解析误判的错误剥离出统计模型，确保学习图谱的绝对干净（防毒药数据）。
**FRs covered:** FR8, FR9, FR12

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic 1: 课件解析、边界圈选与高可用并发控制 (Course Material, Processing Queue & Scope Selection)

用户不仅能将 PDF 转化为知识图谱结构，而且系统即便在多用户同时上传时也能通过“单排队列控制”稳定返回等待名次；解析完毕后，用户可通过交互界面圈选需要测验的具体章节（解决冷启动并收缩上下文范围）。

### Story 1.1: 项目基座搭建与环境脱耦协议 (Project Scaffold & Data Contract Schema)

As a Developer,
I want to initialize the frontend and backend with strict predefined data schemas,
So that both sides can work independently without hallucinating formats, and the infrastructure is proven stable on limited hardware.

**Acceptance Criteria:**

**Given** a clean project directory
**When** I run the initialization scripts
**Then** the backend must expose a strict `schemas/knowledge_tree.py` contract enforcing fields: `node_id, label, parent_id, content_summary`
**And** the backend must load a local SQLite database with `sqlite-vec` extension successfully
**And** a dedicated "vector similarity test script" must execute and pass to prove the C-extensions for sqlite-vec are working stably on the host
**And** the frontend can communicate with a basic "Hello World" API endpoint.

### Story 1.2: 带全局并发单例守卫的 PDF 上传 (Upload with Global Singleton Queue)

As a User,
I want to upload my PDF study materials and receive an instant queue position if the server is busy processing someone else's file,
So that my experience is smooth ("graceful degradation") and the 2C2G server never crashes under concurrent load.

**Acceptance Criteria:**

**Given** the backend is running on a 2C2G environment
**When** a user uploads a PDF file
**Then** the system validates the file size and format (PDF)
**And** the backend routes the file to a **Global Singleton asyncio.Queue** (max 1 active worker)
**And** if the worker is occupied, the API immediately returns a 202 Accepted status with payload `{"status": "queued", "position": N}` without blocking the event loop.

### Story 1.3: 内存安全的分层萃取引擎 (Memory-Safe Hierarchical RAG Extraction)

As a System,
I need to parse PDFs using a generator pattern and extract a rigid logical hierarchy,
So that memory stays below 1.5GB and the frontend gets the precise parent-child mapping it needs for tree rendering.

**Acceptance Criteria:**

**Given** an uploaded PDF passed to the processing worker
**When** PyMuPDF reads the file
**Then** the text must be chunked using a Python Generator pattern (Yielding chunks one by one) to strictly prevent loading >10MB of raw strings into memory at once
**And** the extraction logic must generate a hierarchical structure (Chapter -> Section -> Chunk) mapped to the schema defined in Story 1.1 (with `parent_id` relations)
**And** all generated chunks and embeddings are safely committed to SQLite-vec.

### Story 1.4: 基于数据契约的大纲可视化与范围圈选 (Contract-Driven Outline Scope Selection)

As a Student,
I want to see a visual tree of my course material and select specific nodes,
So that I can constrain the RAG context for the Quiz Engine and trigger the actual test phase.

**Acceptance Criteria:**

**Given** the backend has populated the SQLite database according to the `knowledge_tree` schema
**When** the user accesses the document view
**Then** the Vue 3 frontend strictly consumes the `node_id`, `label`, `parent_id` fields to render an interactive AntV G6 hierarchy graph
**And** I can visually select specific leaf nodes or parent branches
**And** clicking "Start Quiz" persists the selected `node_id` array to the active session state and routes the user to the pending Epic 2 Quiz UI.

## Epic 2: 苏格拉底护栏测验引擎 (Socratic Quiz Engine with Guardrails)

用户基于前置圈选的内容发起深度测验。通过 LangGraph 实现状态跳转与苏格拉底暗示。同时加入隐性“多轮记忆清理”和显性“逃生舱求助”按钮，避免系统被用户的死缠烂打拖入幻觉和 OOM 崩溃。提供“追溯日志”用于面试秀技术。

### Story 2.1: 基于圈选边界的题目生成 (Bounded Question Generation)

As a Student,
I want the system to generate a quiz specifically from the topics I selected,
So that I am tested only on the material I am currently trying to master.

**Acceptance Criteria:**

**Given** the user has selected specific `node_id`s in the knowledge graph
**When** the Quiz Engine initializes
**Then** the backend retrieves only the text embeddings corresponding to the child clusters of the selected nodes
**And** the Question Gen Agent generates 1 Multiple Choice or Short Answer question grounded strictly in that retrieved context.

### Story 2.2: 路由分发与苏格拉底流式引导 (LangGraph Routing & Socratic SSE Stream)

As a Student,
I want the AI to guide me when I get an answer wrong rather than just showing me the solution,
So that I naturally reach the "Aha!" moment through active thinking.

**Acceptance Criteria:**

**Given** an active quiz question
**When** the user submits an answer
**Then** the Validator Agent evaluates the answer and MUST return a structured schema (e.g., `{ "error_type": "logic_gap", "severity": 1 }`)
**And** if incorrect, LangGraph routes the structured state to the `Socratic Tutor` Node
**And** the Tutor node generates a targeted hint based on the `error_type`, returning it to the frontend via an SSE stream channel (`type: content`).

### Story 2.3: 上下文防爆护栏：记忆修剪与逃生舱 (Context Guardrails & Escape Hatch)

As a Student facing a difficult question,
I want the system to detect if I'm stuck or frustrated and offer explicit ways out,
So that I don't get trapped in an endless AI loop or waste server tokens.

**Acceptance Criteria:**

**Given** a user is stuck in a Socratic interaction loop
**When** the user expresses negative sentiment ("I don't know", "too hard") OR the semantic similarity of their last 3 answers indicates stagnation, OR the `turn_count` > 5
**Then** the UI explicitly displays an "Escape Hatch" (Show Answer / Skip Question) and the Tutor switches from pure Socratic to "Semi-transparent Mode" (hints become direct)
**And** if the user chooses to Skip, the node is flagged for Epic 3 as "Needs Review"
**And** behind the scenes, a pruning node in LangGraph summarizes the context string, dropping raw historical messages to save tokens.

### Story 2.4: 瞬时推送的追溯透明窗 (Transient Developer Trace Observer)

As a Technical Interviewer,
I want to see the behind-the-scenes decision logic of the agents without burning server memory,
So that I can verify the complexity of the LangGraph state machine without violating 2C2G constraints.

**Acceptance Criteria:**

**Given** the AI is processing an answer
**When** the graph transitions between nodes
**Then** the backend must use a "fire-and-forget" SSE pulse (`type: trace`) sending the current node's name and metadata, DO NOT persist these massive traces in the backend database/memory
**And** the Vue 3 frontend must accumulate these pulses in a local reactive `ref` array to render the trace log.

## Epic 3: 净水池掌握度追踪 (Clean Mastery Tracking & Wrong-Answer Review)

用户获得可视化的错题本及按知识点的掌握度画像。同时附带了一个“AI 判错上诉”功能，能够将引发幻觉或解析误判的错误剥离出统计模型，确保学习图谱的绝对干净（防毒药数据）。

### Story 3.1: 知识点维度的错题本 (Knowledge-Point Wrong-Answer Notebook)

As a Student,
I want to review all my incorrect answers grouped by the specific knowledge concepts,
So that I can see exactly where my systemic weaknesses are before an exam.

**Acceptance Criteria:**

**Given** the user has completed quizzes with errors
**When** they navigate to the Review page
**Then** incorrect questions are displayed, grouped by the `node_id` (Knowledge tree taxonomy)
**And** the user can re-attempt these questions from this view.

### Story 3.2: 结构化掌握度评估 (Structured Mastery Calculation)

As a Student,
I want the system to calculate a mastery score for each course chapter,
So that I have a quantifiable metric of my study progress.

**Acceptance Criteria:**

**Given** the user has answered questions
**When** the system calculates stats
**Then** a mastery score (e.g., percentage) is computed dynamically based on the ratio of successfully answered questions per `parent_id` cluster
**And** the AntV G6 outline graph in Epic 1 is updated with color-coded nodes reflecting this mastery score (e.g., Red for low, Green for high).

### Story 3.3: 防幻觉数据净化阀 (Anti-Hallucination Appeals Valve)

As a Student,
I want to report if the AI made a mistake or hallucinated a question/answer,
So that the system's mistake doesn't ruin my mastery statistics.

**Acceptance Criteria:**

**Given** the user is viewing a guided answer or question review
**When** the user clicks a discrete "Report AI Error/Hallucination" button
**Then** the specific question record is flagged as `invalidated` in the SQLite database
**And** this record is strictly excluded (pruned) from all future Mastery tracking calculations and Error Notebook displays.
