---
title: "Product Brief: AI-Class"
status: "complete"
created: "2026-03-30"
updated: "2026-03-30"
inputs: [user-interview, web-research-competitive, web-research-technical]
---

# Product Brief: AI-Class — Intelligent Study & Quiz Platform

## Executive Summary

College students across every discipline face the same study problem: disconnected learning resources, no clear way to identify weak spots, and exam prep that amounts to blindly re-reading notes. Existing tools (Zuoyebang, Xiaoyuan Souti) are K-12-focused search engines — they serve answers, not understanding. AI-native quiz generators (Quizgecko, QuestionWell) produce generic questions divorced from any specific curriculum.

**AI-Class** is an LLM Agent + RAG-powered study platform that lets students upload their own course materials, drill knowledge-point-targeted questions from built-in or AI-generated banks, and receive deep answer analysis with structured wrong-answer review. It transforms studying from passive re-reading into active, measurable retrieval practice — the single most evidence-backed learning technique.

Built as a lightweight web application, AI-Class runs on a minimal 2C2G cloud server using API-based LLM inference and embedded vector search, making it cost-effective to operate and easy to maintain. As a portfolio project, it demonstrates practical mastery of RAG pipelines, multi-agent orchestration, and production-grade system design.

## The Problem

University students struggle with three core issues:

1. **No targeted practice** — Existing platforms don't map questions to specific knowledge points within a course syllabus. Students can't focus practice on what they actually don't know.
2. **Shallow answer explanations** — Typical platforms show one correct answer. Students need to understand *why* every option is right or wrong, and how the question connects to broader concepts.
3. **No learning feedback loop** — When students get questions wrong, there's no systematic mechanism to surface those topics again at the right time.

Current workarounds (group chats sharing past exams, manually flipping through slides) are tedious, unstructured, and don't scale across multiple courses.

## The Solution

AI-Class provides a three-layer study system:

- **Knowledge-Point Quiz Engine** — Built-in question banks organized by knowledge point, plus AI-generated questions from uploaded course materials (PDFs, slides, notes). RAG ensures all generated content stays grounded in actual course material.
- **Deep Answer Analysis** — Every question includes a structured explanation: correct reasoning, common misconceptions, and links to the underlying knowledge points.
- **Wrong-Answer Intelligence** — Automatically tracks incorrect answers, identifies weak knowledge areas, and generates targeted review sets.

## What Makes This Different

| Dimension | Traditional Quiz Apps | AI-Class |
|---|---|---|
| Content source | Fixed question banks | User materials + built-in + AI-generated |
| Knowledge mapping | None or flat tags | Structured knowledge-point hierarchy |
| Answer analysis | Single correct answer | Multi-dimensional explanation with concept links |
| Wrong-answer handling | Simple list | Intelligent re-surfacing with targeted practice |
| Target audience | K-12 / certification | University multi-discipline |

The core advantage: **curriculum-grounded intelligence**. By using RAG over actual course materials, AI-Class generates questions and explanations that are specific to what a student's professor actually teaches — not generic textbook content.

## Who This Serves

**Primary user:** Chinese university students preparing for exams across any discipline — from Computer Science and Higher Mathematics to Economics and Law.

Typical scenario: A student uploads their Advanced Mathematics lecture slides two weeks before finals. AI-Class indexes the content, generates targeted practice questions organized by knowledge point (limits, derivatives, integrals), and tracks which topics need more work based on quiz performance.

## Technical Approach

- **LLM inference**: Remote API (DeepSeek / SiliconFlow / Tongyi) — no local model, preserving server resources for the application layer
- **RAG pipeline**: LangChain or LlamaIndex with lazy-loading document processing to stay within 2GB RAM
- **Vector store**: ChromaDB or FAISS (embedded, memory-efficient)
- **Backend**: Python + FastAPI
- **Frontend**: Lightweight web framework (responsive)

## Success Criteria

For this initial version, success is defined as:

- The system runs end-to-end on a 2C2G Alibaba Cloud server without OOM crashes
- A user can upload a PDF and receive AI-generated questions within 30 seconds
- Knowledge-point browsing and quiz functionality works for at least 2 distinct subjects
- Wrong-answer tracking produces a meaningful, re-quizzable review set
- Codebase is clean, modular, and demonstrable in a technical interview setting

## Scope

**In scope (MVP):**
- Web-based UI (responsive)
- PDF/document upload and RAG indexing
- Knowledge-point-organized question bank (seed data + AI-generated)
- Quiz mode with multiple question types (MCQ, fill-in-blank, short answer)
- Answer analysis display
- Wrong-answer notebook with review mode

**Out of scope (future):**
- Mobile app / WeChat mini-program
- Real-time collaboration or social features
- Spaced repetition algorithm (SRS)
- Knowledge graph visualization
- Payment / monetization system
- Multi-tenant / institution management

## Vision

If AI-Class proves the concept, it evolves into a **personal AI tutor** — one that knows your curriculum, understands your weak spots, and adapts to your learning pace. Future directions include knowledge graph visualization showing concept dependencies, spaced repetition for long-term retention, and collaborative features where students contribute to shared course-specific question banks. The ultimate goal: every university student has an AI study partner that makes active learning effortless.
