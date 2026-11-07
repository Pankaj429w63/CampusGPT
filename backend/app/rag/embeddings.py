from typing import List, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

_embedding_model = None

def get_embedding_model():
    """
    Lazy loader for SentenceTransformer embedding model.
    Avoids loading model weights at application startup.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _embedding_model

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()

def generate_query_embedding(query: str) -> List[float]:
    model = get_embedding_model()
    embedding = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    return embedding[0].tolist()

