from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
from app.rag.loader import DocumentChunk
from app.rag.embeddings import generate_embeddings, generate_query_embedding

logger = logging.getLogger(__name__)

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_PERSIST_DIR)
        )
    return _chroma_client

def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

def add_chunks_to_vectorstore(chunks: List[DocumentChunk], batch_size: int = 64) -> int:
    if not chunks:
        return 0

    collection = get_collection()
    total_added = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c.text for c in batch]
        embeddings = generate_embeddings(texts)
        ids = [
            f"{c.metadata.get('department', 'general')}_{c.metadata['document']}_p{c.metadata.get('page', 1)}_c{c.metadata.get('chunk_index', idx)}"
            for idx, c in enumerate(batch, start=i)
        ]
        metadatas = [c.metadata for c in batch]

        collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        total_added += len(batch)

    return total_added

def query_vectorstore(query: str, top_k: int = settings.INITIAL_TOP_K) -> List[Dict[str, Any]]:
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    effective_k = min(top_k, count)
    query_vector = generate_query_embedding(query)
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=effective_k,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
        distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            chunks.append({
                "text": doc,
                "metadata": meta,
                "distance": float(dist),
                # Cosine similarity roughly 1 - distance
                "similarity": float(1.0 - dist)
            })

    return chunks

def get_collection_stats() -> Dict[str, Any]:
    try:
        collection = get_collection()
        count = collection.count()
        return {
            "status": "connected",
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "count": count
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "count": 0
        }

