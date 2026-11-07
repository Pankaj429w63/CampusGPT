from typing import List, Dict, Any, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

_reranker_model = None

def get_reranker_model():
    """
    Lazy loader for CrossEncoder reranker model.
    Avoids loading model weights at application startup.
    """
    global _reranker_model
    if _reranker_model is None:
        logger.info(f"Loading reranker model: {settings.RERANKER_MODEL_NAME}")
        from sentence_transformers import CrossEncoder
        _reranker_model = CrossEncoder(settings.RERANKER_MODEL_NAME)
    return _reranker_model

def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = settings.RERANK_TOP_K) -> List[Dict[str, Any]]:
    if not chunks:
        return []
        
    if len(chunks) <= top_k:
        # If chunks count is already within top_k, attempt score enrichment if model loads
        pass

    try:
        model = get_reranker_model()
        pairs = [[query, chunk["text"]] for chunk in chunks]
        scores = model.predict(pairs)
        
        # Attach rerank score
        for i, score in enumerate(scores):
            chunks[i]["rerank_score"] = float(score)
            
        # Sort descending by rerank score
        ranked = sorted(chunks, key=lambda x: x.get("rerank_score", float("-inf")), reverse=True)
        return ranked[:top_k]
    except Exception as e:
        logger.warning(f"Reranker failed or unavailable ({e}); falling back to vector similarity order.")
        return chunks[:top_k]

