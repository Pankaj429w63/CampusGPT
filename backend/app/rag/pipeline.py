from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
from app.core.config import settings
from app.core.schemas import SourceItem
from app.rag.loader import process_file_into_chunks
from app.rag.vectorstore import add_chunks_to_vectorstore, query_vectorstore, get_collection_stats
from app.rag.reranker import rerank_chunks
from app.services.llm import generate_answer_via_ollama

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".markdown"}

def discover_document_files(docs_dir: Path = settings.DATA_DOCUMENTS_DIR) -> List[Path]:
    """
    Recursively scans docs_dir for supported files, ignoring hidden/system files.
    """
    if not docs_dir.exists():
        return []
    
    discovered = []
    for f in docs_dir.rglob("*"):
        if not f.is_file():
            continue
        # Ignore hidden/system files (starting with dot or contained in hidden folders)
        if any(part.startswith(".") for part in f.relative_to(docs_dir).parts):
            continue
        if f.suffix.lower() in SUPPORTED_EXTENSIONS:
            discovered.append(f)
            
    # Sort for deterministic processing order
    discovered.sort(key=lambda p: str(p.relative_to(docs_dir)))
    return discovered

def scan_and_ingest_documents(docs_dir: Path = settings.DATA_DOCUMENTS_DIR) -> Dict[str, Any]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    files = discover_document_files(docs_dir)
    
    total_chunks_added = 0
    details = []

    for file_path in files:
        rel_path = str(file_path.relative_to(docs_dir)).replace("\\", "/")
        try:
            chunks = process_file_into_chunks(file_path, base_dir=docs_dir)
            added = add_chunks_to_vectorstore(chunks)
            total_chunks_added += added
            details.append({
                "file": file_path.name,
                "relative_path": rel_path,
                "status": "success",
                "chunks_count": len(chunks)
            })
        except Exception as e:
            logger.error(f"Error ingesting file {rel_path}: {e}")
            details.append({
                "file": file_path.name,
                "relative_path": rel_path,
                "status": "error",
                "error": str(e),
                "chunks_count": 0
            })

    return {
        "documents_scanned": len(files),
        "chunks_indexed": total_chunks_added,
        "details": details
    }

def retrieve_and_rerank(query: str) -> List[Dict[str, Any]]:
    # Step 1: Initial vector retrieval
    initial_chunks = query_vectorstore(query, top_k=settings.INITIAL_TOP_K)
    if not initial_chunks:
        return []

    # Step 2: Cross-Encoder Reranking
    reranked = rerank_chunks(query, initial_chunks, top_k=settings.RERANK_TOP_K)
    return reranked

def format_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    sources = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        doc = meta.get("document", "Unknown")
        page = meta.get("page")
        key = (doc, page)
        if key not in seen:
            seen.add(key)
            preview_text = chunk.get("text", "")[:150].strip()
            sources.append({
                "document": doc,
                "page": page,
                "score": round(chunk.get("rerank_score", chunk.get("similarity", 0.0)), 4),
                "preview": preview_text + "..." if len(chunk.get("text", "")) > 150 else preview_text
            })
    return sources

async def ask_campusgpt_rag(question: str) -> Tuple[str, List[Dict[str, Any]]]:
    # 1. Retrieve knowledge chunks
    retrieved_chunks = retrieve_and_rerank(question)
    
    # 2. Extract structured sources
    sources = format_sources(retrieved_chunks)

    # 3. If no documents exist in vectorstore or none retrieved
    stats = get_collection_stats()
    if stats.get("count", 0) == 0 or not retrieved_chunks:
        fallback_msg = (
            "The available university documents do not contain information regarding this topic. "
            "Please ensure institutional documents are added to `data/documents/` and ingested."
        )
        return fallback_msg, []

    # 4. Generate grounded answer with Ollama
    try:
        answer = await generate_answer_via_ollama(question, retrieved_chunks)
        return answer, sources
    except ConnectionError as e:
        # Graceful degradation message explaining Ollama status
        error_msg = (
            f"**CampusGPT Knowledge Retrieved Successfully** ({len(sources)} source references found), "
            f"but local LLM generation is currently offline.\n\n"
            f"Reason: {str(e)}\n\n"
            f"**Top Relevant Excerpt:**\n> {retrieved_chunks[0]['text'][:350]}..."
        )
        return error_msg, sources
    except Exception as e:
        error_msg = f"An error occurred while synthesizing the answer: {str(e)}"
        return error_msg, sources

