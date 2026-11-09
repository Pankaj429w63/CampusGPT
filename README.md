# CampusGPT

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.4_Turbopack-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.0-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6F00?style=for-the-badge&logo=databricks&logoColor=white)](https://www.trychroma.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Qwen_2.5-white?style=for-the-badge&logo=ollama&logoColor=black)](https://ollama.ai/)
[![HuggingFace](https://img.shields.io/badge/BGE--M3-Embeddings_%26_Reranker-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/BAAI/bge-m3)

<p align="center">
  <b>Enterprise-Grade Local Campus AI Assistant: Hybrid Semantic RAG, Multi-Agent Intent Planner & Deterministic Timetable Engine</b>
</p>

[Local Frontend](http://localhost:3000) • [Local API Docs](http://localhost:8000/docs) • [FastAPI Health](http://localhost:8000/health) • [Prometheus Metrics](http://localhost:8000/metrics) • [GitHub Repository](https://github.com/Pankaj429w63/CampusGPT)

</div>

---

## Overview

**CampusGPT** is an intelligent university campus assistant combining modern generative AI with deterministic domain engines. It serves students, faculty, and administrators with instant, grounded answers across institutional handbooks, course curricula, academic calendars, faculty directories, and live class timetables without hallucination or cross-department confusion.

### Key Capabilities
- **Hybrid Multi-Agent Planner:** Automatically routes user queries between deterministic tools (academic calendar, class timetable, faculty room lookup) and a dense semantic RAG pipeline.
- **Deterministic Structured Timetable Engine:** Direct OpenPyXL parser for complex 13-worksheet master schedules, merged cells, concurrent laboratory batches, and room allocations with sub-10ms latency (zero ChromaDB overhead).
- **Domain-Aware Semantic RAG:** Deep document chunking with hierarchical section preserving, powered by `BAAI/bge-m3` dense embeddings, `BAAI/bge-reranker-v2-m3` cross-encoders, and ChromaDB vector store.
- **Hallucination & Attribution Guardrails:** Department-isolated cross-penalties, prompt injection firewalls, and out-of-domain refusals.
- **Full-Stack Production Ready:** Responsive Next.js 16 (Turbopack) UI with real-time thinking states and markdown formatting paired with an asynchronous FastAPI backend.

---

## System Architecture

```mermaid
flowchart TB
    subgraph ClientLayer ["Client Layer (Next.js 16 / React 19)"]
        UI["Web Browser / Chat Dashboard"]
        APIClient["Frontend API Service (api.ts)"]
        TimetableComponent["Interactive Timetable View"]
        UI --> APIClient
        UI --> TimetableComponent
    end

    subgraph Gateway ["FastAPI Application Gateway (Port 8000)"]
        AskEndpoint["POST /ask"]
        TTEndpoints["GET /timetable/*"]
        HealthMetrics["/health, /readiness, /metrics"]
    end

    APIClient -->|JSON Request| AskEndpoint
    TimetableComponent -->|Class / Day Query| TTEndpoints

    subgraph AgentLayer ["Intent Classifier & Planner Agent"]
        IntentRouter{"classify_query_intent()"}
        Guardrail["Prompt Injection & Length Guardrails"]
    end

    AskEndpoint --> Guardrail
    Guardrail --> IntentRouter

    subgraph DeterministicEngine ["Deterministic Engines (Sub-10ms)"]
        TTEngine["Timetable Query Service\n(Master TT OpenPyXL Engine)"]
        CalEngine["Academic Calendar Extractor\n(2026-27 ODD/EVEN Terms)"]
        FacLookup["Faculty Directory & Room Lookup"]
    end

    subgraph RAGPipeline ["Semantic RAG Pipeline (Document Knowledge)"]
        Embedder["BAAI/bge-m3 Vector Retrieval"]
        VectorDB[("ChromaDB Vector Store\n(campusgpt_knowledge)")]
        Reranker["BAAI/bge-reranker-v2-m3\n(Dept Priority & Penalty Filter)"]
        LLMGen["Local Ollama Generator\n(Qwen 2.5:3b - 120s Timeout)"]
    end

    IntentRouter -->|Class / Batch / Room / Next Class| TTEngine
    IntentRouter -->|Academic Dates / Exams| CalEngine
    IntentRouter -->|Faculty Room Allocation| FacLookup
    IntentRouter -->|Curriculum / Policy / Regulations| Embedder

    TTEndpoints --> TTEngine
    Embedder <--> VectorDB
    Embedder -->|Top-K Chunks| Reranker
    Reranker -->|Grounded Context + Rules| LLMGen

    TTEngine -->|Structured Markdown| AskEndpoint
    CalEngine -->|Verified Schedule| AskEndpoint
    FacLookup -->|Faculty Match| AskEndpoint
    LLMGen -->|Grounded Answer + Citations| AskEndpoint
```

---

## Detailed Data & Routing Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Student / User
    participant FE as Next.js Dashboard
    participant API as FastAPI /ask
    participant Plan as Planner Agent
    participant TT as Timetable Service
    participant RAG as RAG Pipeline (BGE-M3)
    participant LLM as Ollama (Qwen 2.5)

    User->>FE: Ask question (e.g. "Where is the SY-A A1 lab?")
    FE->>API: POST /ask { question }
    API->>Plan: classify_query_intent(question)
    
    alt Timetable or Room Allocation Intent
        Plan->>TT: Resolve sheet ("SY-A"), batch ("A1"), day
        TT-->>Plan: Match: Multimodal Sensor Analytics Lab (Room 514)
        Plan-->>API: Markdown timetable response + Excel source citation
    else Ambiguous Timetable Query (e.g. "Show my timetable")
        Plan-->>API: Clarification prompt (SY-A, TY-B, M.Tech-FY, etc.)
    else Academic Calendar Intent (2026-27)
        Plan-->>API: Fast-path verified ODD 2026 / EVEN 2027 calendar
    else Document Knowledge Query (e.g. "Explain AIML curriculum")
        Plan->>RAG: retrieve_and_rerank(question)
        RAG->>RAG: BGE-M3 Dense Search + BGE Reranker (Dept Prioritization)
        RAG->>LLM: Grounded context + strict attribution prompt
        LLM-->>RAG: Synthesized grounded response
        RAG-->>Plan: Answer + Top-K Sources
        Plan-->>API: Final JSON response { status, answer, sources }
    end

    API-->>FE: HTTP 200 OK
    FE-->>User: Display formatted answer with source badges
```

---

## Models & Technology Stack

| Component | Technology / Model | Identifier / Link | Role |
| :--- | :--- | :--- | :--- |
| **LLM Inference** | Qwen 2.5 (3B Parameters) | [`qwen2.5:3b`](https://ollama.ai/library/qwen2.5) | Local private answer synthesis via Ollama |
| **Dense Embeddings** | BAAI BGE-M3 | [`BAAI/bge-m3`](https://huggingface.co/BAAI/bge-m3) | 1024-dim multilingual semantic embeddings |
| **Neural Reranker** | BAAI BGE Reranker v2 M3 | [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Cross-encoder reranking with department prioritization |
| **Vector Database** | ChromaDB | [`chromadb`](https://www.trychroma.com/) | Persistent local embeddings collection (`campusgpt_knowledge`) |
| **Backend Framework** | FastAPI + Uvicorn | Python 3.12 | Async REST API, Pydantic schemas, Prometheus metrics |
| **Frontend Framework** | Next.js 16 + React 19 | Turbopack | Modern glassmorphism UI, real-time chat, responsive views |
| **Workbook Parser** | OpenPyXL | Python | Deterministic multi-sheet Excel timetable engine |

---

## Live Endpoints & Port Map

| Service / Port | URL | Description |
| :--- | :--- | :--- |
| **Frontend Application** | `http://localhost:3000` | Interactive Chat and Timetable Dashboard |
| **Backend REST API** | `http://localhost:8000` | Application Root |
| **Interactive API Docs** | `http://localhost:8000/docs` | Swagger UI documentation and testing |
| **Backend Health Check** | `http://localhost:8000/health` | Service health status |
| **Backend Readiness** | `http://localhost:8000/readiness` | Deep readiness check (Ollama + Vector Store + Documents) |
| **Prometheus Metrics** | `http://localhost:8000/metrics` | Latency and tool call telemetry |
| **Timetable Sheets API** | `http://localhost:8000/timetable/sheets` | List all available classes |
| **Class Timetable API** | `http://localhost:8000/timetable/class/{sheet}` | Query day/batch schedule for section |
| **Timetable Search API** | `http://localhost:8000/timetable/search` | Search by faculty, subject code, or room |

---

## Quickstart Guide

### 1. Prerequisites
- **Python 3.11+** (Python 3.12 recommended)
- **Node.js 18+** & **pnpm 10+**
- **Ollama** installed with `qwen2.5:3b` pulled:
  ```bash
  ollama pull qwen2.5:3b
  ```

### 2. Backend Setup
```powershell
# Navigate to repository root
cd CampusGPT

# Create and activate virtual environment
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# Start FastAPI Server
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```powershell
# Navigate to frontend
cd frontend

# Install dependencies
pnpm install

# Start Next.js Development Server
pnpm dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## Verification & Testing Suite

CampusGPT includes comprehensive test suites across agents, RAG, and timetable modules:

```powershell
# Run full backend test suite (55 tests)
$env:PYTHONPATH="backend"
pytest backend/tests -v

# Run frontend linting & TypeScript type checks
cd frontend
pnpm lint
pnpm tsc --noEmit

# Test production build
pnpm build
```

---

## Repository Safety & Data Governance

- **Institutional Privacy:** Original PDF handbooks, Master Excel files (`data/`), and local vector stores (`backend/data/`) are strictly excluded via `.gitignore`.
- **Zero Hallucination Attribution:** Strict negative penalties prevent coordinators of other departments from being classified as AIML faculty.
- **Zero Mock Fallback:** All chat endpoints resolve against live backend knowledge or deterministic timetable parsers.

---

<div align="center">
  <b>CampusGPT</b> • Engineered for Accuracy, Reliability & Academic Integrity.
</div>

