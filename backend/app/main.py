import time
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.schemas import (
    AskRequest,
    AskResponse,
    IngestResponse,
    ReadinessResponse
)
from app.core.guardrails import (
    sanitize_and_validate_input,
    validate_output
)
from app.core.metrics import (
    MetricsMiddleware,
    get_metrics_content,
    STAGE_LATENCY_SECONDS
)
from app.core.evaluation import (
    EVALUATION_DATASET,
    evaluate_abstention_accuracy
)
from app.agents.planner import (
    execute_planned_query,
    planner_metrics,
    classify_query_intent
)
from app.timetable.service import timetable_service
from app.rag.pipeline import scan_and_ingest_documents, discover_document_files
from app.rag.vectorstore import get_collection_stats
from app.services.llm import check_ollama_health

logger = logging.getLogger(__name__)

# Request ID & Audit Logger Middleware
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        duration = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time-Ms"] = f"{duration * 1000:.2f}"
        return response

app = FastAPI(
    title=settings.APP_NAME,
    description="CampusGPT AI-Powered Smart University Platform — RAG, Deterministic Agents & Guardrails",
    version=settings.APP_VERSION,
)

# Apply middlewares
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
)

# In-memory storage for latest evaluation run
_latest_evaluation_report = None


@app.get("/")
def root():
    return {
        "message": "Welcome to CampusGPT API",
        "status": "running",
        "version": settings.APP_VERSION,
        "engine": "RAG + Specialized Deterministic Agents"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "CampusGPT Backend",
    }


@app.get("/ready")
@app.get("/readiness", response_model=ReadinessResponse)
async def readiness():
    """
    Dependency readiness probe for Ollama, ChromaDB, and indexed documents.
    """
    ollama_status = await check_ollama_health()
    chroma_stats = get_collection_stats()
    
    docs_dir = settings.DATA_DOCUMENTS_DIR
    doc_count = len(discover_document_files(docs_dir))

    is_ready = bool(chroma_stats.get("status") == "connected")
    
    return ReadinessResponse(
        status="ready" if is_ready else "degraded",
        ollama_ready=ollama_status.get("running", False),
        ollama_model_available=ollama_status.get("target_model_available", False),
        chromadb_ready=chroma_stats.get("status") == "connected",
        embedding_model_cached=False,
        reranker_model_cached=False,
        documents_count=doc_count,
        collection_chunks_count=chroma_stats.get("count", 0),
        details={
            "ollama": ollama_status,
            "chroma": chroma_stats,
            "data_directory": str(docs_dir),
            "configured_llm": settings.OLLAMA_MODEL,
            "configured_embedding": settings.EMBEDDING_MODEL_NAME,
            "configured_reranker": settings.RERANKER_MODEL_NAME,
        }
    )


@app.get("/metrics")
def metrics():
    """
    Exposes real-time Prometheus metrics for Prometheus scraping / Grafana dashboards.
    """
    content, content_type = get_metrics_content()
    return Response(content=content, media_type=content_type)


@app.get("/agents/status")
def agents_status():
    """
    Returns current status and execution metrics of the query planner and specialized agents.
    """
    total = max(1, planner_metrics.total_plans)
    success_rate = round((planner_metrics.successful_calls / total) * 100, 2)
    
    return {
        "status": "active",
        "total_queries_planned": planner_metrics.total_plans,
        "overall_tool_success_rate_percent": success_rate,
        "tool_selection_distribution": planner_metrics.tool_calls_count,
        "available_tools": [
            {"id": "timetable_lookup", "type": "deterministic", "description": "Structured timetable and room schedule query"},
            {"id": "faculty_lookup", "type": "deterministic", "description": "Verified faculty profiles, courses and office hours"},
            {"id": "academic_calendar_lookup", "type": "deterministic", "description": "Academic dates, CIE/SEE exams and regulations"},
            {"id": "rag_knowledge_retrieval", "type": "rag_semantic", "description": "BGE-M3 + ChromaDB + Reranker + Qwen2.5:3b synthesis"}
        ]
    }


@app.post("/ingest", response_model=IngestResponse)
def ingest_documents():
    """
    Scans `data/documents/` for PDF, DOCX, TXT, and Markdown files,
    chunks them with metadata and indexes them into ChromaDB.
    """
    try:
        results = scan_and_ingest_documents()
        return IngestResponse(
            status="success",
            message=f"Ingestion complete. {results['documents_scanned']} documents processed, {results['chunks_indexed']} chunks indexed.",
            documents_scanned=results["documents_scanned"],
            chunks_indexed=results["chunks_indexed"],
            details=results["details"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Receives user queries with guardrail sanitization, routes via query planner
    to specialized tools or RAG pipeline, and validates output.
    """
    # 1. Guardrail input validation & prompt-injection defense
    is_valid, cleaned_q, err_msg = sanitize_and_validate_input(request.question)
    if not is_valid:
        return AskResponse(
            status="error",
            question=request.question,
            answer=err_msg or "Invalid question format.",
            sources=[],
        )

    # 2. Execute via Agent Planner
    t_start = time.perf_counter()
    answer_raw, sources, meta = await execute_planned_query(cleaned_q)
    STAGE_LATENCY_SECONDS.labels(stage="total_request").observe(time.perf_counter() - t_start)

    # 3. Output guardrail validation
    safe_answer = validate_output(answer_raw)

    return AskResponse(
        status="success",
        question=cleaned_q,
        answer=safe_answer,
        sources=sources,
    )


@app.post("/evaluate")
async def run_evaluation():
    """
    Executes the deterministic and RAG evaluation benchmark dataset,
    measuring tool accuracy, keyword recall, and abstention compliance.
    """
    global _latest_evaluation_report
    results = []
    correct_routing_count = 0
    grounded_keyword_count = 0
    correct_abstention_count = 0

    t_eval_start = time.perf_counter()

    for item in EVALUATION_DATASET:
        q = item["query"]
        expected_tool = item["expected_tool"]
        
        # Test routing
        actual_tool = classify_query_intent(q)
        routing_correct = (actual_tool == expected_tool)
        if routing_correct:
            correct_routing_count += 1
            
        # Execute query
        ans, srcs, meta = await execute_planned_query(q)
        
        # Keyword checks
        keywords_matched = all(k.lower() in ans.lower() for k in item["expected_keywords"])
        if keywords_matched:
            grounded_keyword_count += 1
            
        # Abstention check
        is_abstention_test = (item["category"] == "abstention")
        abstention_ok = evaluate_abstention_accuracy(ans, is_abstention_test)
        if abstention_ok:
            correct_abstention_count += 1

        results.append({
            "id": item["id"],
            "query": q,
            "category": item["category"],
            "expected_tool": expected_tool,
            "routed_tool": actual_tool,
            "routing_correct": routing_correct,
            "keyword_recall_ok": keywords_matched,
            "abstention_ok": abstention_ok,
            "sources_count": len(srcs)
        })

    total_items = len(EVALUATION_DATASET)
    elapsed = time.perf_counter() - t_eval_start

    _latest_evaluation_report = {
        "timestamp": time.time(),
        "total_test_cases": total_items,
        "elapsed_seconds": round(elapsed, 3),
        "tool_routing_accuracy_percent": round((correct_routing_count / total_items) * 100, 2),
        "grounded_keyword_accuracy_percent": round((grounded_keyword_count / total_items) * 100, 2),
        "abstention_accuracy_percent": round((correct_abstention_count / total_items) * 100, 2),
        "individual_results": results
    }

    return _latest_evaluation_report


@app.get("/evaluation/summary")
def get_evaluation_summary():
    """
    Retrieves the most recent evaluation benchmark report.
    """
    if _latest_evaluation_report is None:
        return {
            "status": "no_evaluations_run",
            "message": "No evaluation has been executed yet. Call POST /evaluate to run benchmark."
        }
    return _latest_evaluation_report


# =========================================================================
# Structured Timetable Endpoints
# =========================================================================
@app.get("/timetable/sheets")
def get_timetable_sheets():
    """Returns available timetable sheets/classes."""
    data = timetable_service.get_data()
    return {
        "status": "success",
        "sheets": data.sheets_parsed,
        "total_entries": data.total_entries
    }


@app.get("/timetable/class/{sheet_name}")
def get_class_schedule(sheet_name: str, day: Optional[str] = None, batch: Optional[str] = None):
    """Returns timetable entries for a specific class sheet (e.g. SY-A, TY-B, M.Tech-FY)."""
    canonical_sheet = timetable_service.normalize_sheet_alias(sheet_name) or sheet_name.upper()
    entries = timetable_service.get_class_timetable(canonical_sheet, day=day, batch=batch)
    return {
        "status": "success",
        "sheet_name": canonical_sheet,
        "day": day or "All Days",
        "batch": batch or "All Batches",
        "count": len(entries),
        "entries": [e.model_dump() for e in entries]
    }


@app.get("/timetable/today/{sheet_name}")
def get_today_schedule(sheet_name: str, batch: Optional[str] = None):
    """Returns today's timetable for a specific class section."""
    canonical_sheet = timetable_service.normalize_sheet_alias(sheet_name) or sheet_name.upper()
    return timetable_service.get_today_timetable(canonical_sheet, batch=batch)


@app.get("/timetable/next/{sheet_name}")
def get_next_class_schedule(sheet_name: str, batch: Optional[str] = None):
    """Returns currently ongoing or next upcoming class for a section."""
    canonical_sheet = timetable_service.normalize_sheet_alias(sheet_name) or sheet_name.upper()
    return timetable_service.get_next_class(canonical_sheet, batch=batch)


@app.get("/timetable/free/{sheet_name}")
def get_free_periods_schedule(sheet_name: str, day: Optional[str] = None, batch: Optional[str] = None):
    """Returns free/unallocated periods for a class section."""
    canonical_sheet = timetable_service.normalize_sheet_alias(sheet_name) or sheet_name.upper()
    free_slots = timetable_service.get_free_periods(canonical_sheet, day=day, batch=batch)
    return {
        "status": "success",
        "sheet_name": canonical_sheet,
        "day": day or "Today",
        "free_slots": free_slots
    }


@app.get("/timetable/search")
def search_timetable(faculty: Optional[str] = None, subject: Optional[str] = None, room: Optional[str] = None):
    """Searches timetable entries across all sheets by faculty, subject or room."""
    if faculty:
        results = timetable_service.search_by_faculty(faculty)
    elif subject:
        results = timetable_service.search_by_subject(subject)
    elif room:
        results = timetable_service.search_by_room(room)
    else:
        raise HTTPException(status_code=400, detail="Must provide at least one query parameter: faculty, subject, or room.")
    
    return {
        "status": "success",
        "count": len(results),
        "results": [e.model_dump() for e in results]
    }

