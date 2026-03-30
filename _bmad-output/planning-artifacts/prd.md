---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain, step-06-innovation, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish]
author: 'Jins'
inputDocuments:
  - product-brief-ai-class.md
  - product-brief-ai-class-distillate.md
---

# Product Requirements Document - AI-Class

## 🎯 1. Product Vision & Executive Summary

AI-Class is an intelligent, personalized study platform designed for university students to transform passive course materials (PDFs, lecture slides) into active, curriculum-grounded retrieval practice. Existing study tools either provide generic answers or fail to align with specialized university curricula. AI-Class bridges this gap by functioning as a personal Socratic AI Tutor.

**Key Differentiation:** Unlike static "Q&A" tools, AI-Class prioritizes **Guided Mastery**. When a student falters, the AI acts as a senior professor, using pedagogical scaffolding and Socratic questioning to lead the student toward independent discovery.

**The "Aha! Moment":** Upon uploading a dense 50-page lecture, the system instantly processes the content and renders a beautiful, interactive Knowledge Graph. This visual network maps complex dependencies (e.g., limits → derivatives → integrals), building immediate trust through visual impact and serving as the interactive foundation for targeted node-specific practice.

- **Project Type:** Web Application (Vue 3 + Vite SPA)
- **Domain:** EdTech (Medium Complexity)
- **Deployment Target:** Lightweight 2C2G Cloud Infrastructure

## 📈 2. Success Metrics

### User Success
- **Guided Resolution Rate:** > 80% of incorrect answers initiate a successfully guided Socratic interaction rather than a static answer display.
- **Mastery Through Guidance:** Students independently arrive at correct analyses through step-by-step AI guidance.

### Technical & Business Success
- **Portfolio Excellence:** Showcases advanced proficiency in Agentic AI state management and RAG pipeline optimization on limited hardware.
- **Resource Efficiency:** 0% OOM crashes on a 2GB RAM server during peak document processing; < 30s processing time.

## 🗺️ 3. User Experience & Journeys

### Journey 1: The Mastery Cycle (Happy Path)
Li (Sophomore) uploads 40 pages of Calculus slides. System indexes in < 30s. Li hits a "Chain Rule" question, gets it wrong, and the AI Tutor guides him via hints: *"What's the derivative of the inner function u?"*. Li realizes the error, corrects it, and feels the "Aha!" rush.

### Journey 2: Resource Guardrails (Edge Case)
User attempts to upload a 200MB encrypted handbook. The system gracefully intercepts, advising the user to unlock/split files to maintain stability on the 2C2G engine.

### Journey 3: The Architecture Explorer (Demo)
A technical interviewer observes the "Trace Log," seeing the explicit hand-off between the "Question Gen Agent" and the "Socratic Tutor Agent," demonstrating intentional system design.

## 🛣️ 4. Strategic Roadmap & Scoping

### Phase 1: MVP (Core Scaffolding)
- Secure PDF upload & RAG indexing (Vite/Vue 3 + FastAPI).
- **Interactive Socratic Tutor Agent:** Real-time (SSE) guiding questions for incorrect answers.
- Wrong-Answer Notebook with basic "re-explore" retry logic.

### Phase 2: Growth (The "Wow" Factor)
- **Interactive Knowledge Graph:** Visualizing hierarchical concept dependencies.
- **Spaced Repetition (SRS):** Memory-curve based review scheduling.

### Phase 3: Vision (Expansion)
- Collaborative Study Rooms and WeChat Mini-program support.

## 🌍 5. Domain & Innovation Focus

- **Academic Integrity:** AI must flag and prompt verification when using information outside the provided RAG context.
- **Copyright Compliance:** Explicit user agreements stating uploaded materials are for **personal study only**.
- **Agentic Socratic Logic:** Innovation lies in the state-aware agent switching personas based on user performance.

## 🏗️ 6. Technical & Web Architecture

- **SPA Stack:** Vue 3 + Vite (ES2020+) to offload rendering compute to the client browser (CSR).
- **Styling:** TailwindCSS + On-demand Element Plus components for **Mobile-First Responsive Design** and minimal bundle size.
- **Real-time Comms:** Server-Sent Events (SSE) via native `fetch` API for streaming tutor responses.
- **RAG Latency:** < 3s starting latency for initial hint delivery.

## 📝 7. Functional Requirements (The Capability Contract)

### Q1: Material Management
- **FR1:** Users can upload PDF materials and see real-time processing status.
- **FR2:** System validates file size/format specifically for 2C2G resource limits.

### Q2: Knowledge Engine
- **FR3:** System extracts a structured hierarchy of knowledge points and indexes them for RAG.
- **FR4:** Users can preview the extracted concept outline before starting a quiz.

### Q3: Socratic Interaction
- **FR5:** System generates Multiple Choice and Short Answer questions grounded in source content.
- **FR6:** System provides step-by-step Socratic hints upon incorrect answers.
- **FR7:** System verifies user reasoning through the guided dialogue.

### Q4: Progress & Review
- **FR8:** System organizes incorrect answers in a "Wrong-Answer Notebook" by knowledge point.
- **FR9:** System tracks user mastery levels per concept based on performance.
- **FR10:** **System Trace Visibility:** Technical users can access a "Trace Log" showing the reasoning chain and internal hand-offs between orchestrator and agents.

## ⚙️ 8. Non-Functional Requirements

- **Efficiency:** Indexing 50p PDF < 30s; Memory cap < 1.5GB for backend processes.
- **Modernity:** Exclusive support for Chrome/Edge/Safari latest versions; no legacy polyfills.
- **Security:** Strict per-user session isolation for uploaded materials and logs.
- **Compliance:** Adherence to FERPA/COPPA principles for student data privacy.
- **Accessibility:** Target WCAG 2.1 AA compliance for core study interfaces.
