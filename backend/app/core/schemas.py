from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class AskRequest(BaseModel):
    question: str

class SourceItem(BaseModel):
    document: str
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    score: Optional[float] = None
    preview: Optional[str] = None

class AskResponse(BaseModel):
    status: str
    question: str
    answer: str
    sources: List[Any] = []

class IngestResponse(BaseModel):
    status: str
    message: str
    documents_scanned: int
    chunks_indexed: int
    details: List[Dict[str, Any]] = []

class ReadinessResponse(BaseModel):
    status: str
    ollama_ready: bool
    ollama_model_available: bool
    chromadb_ready: bool
    embedding_model_cached: bool
    reranker_model_cached: bool
    documents_count: int
    collection_chunks_count: int
    details: Dict[str, Any] = {}

