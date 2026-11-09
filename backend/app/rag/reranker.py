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

    try:
        model = get_reranker_model()
        pairs = [[query, chunk["text"]] for chunk in chunks]
        scores = model.predict(pairs)
        
        q_lower = query.lower()
        is_faculty_query = any(k in q_lower for k in ["faculty", "professor", "hod", "head of department", "teacher", "instructors"])

        # Attach rerank score and apply domain-aware priority adjustments
        for i, score in enumerate(scores):
            raw_score = float(score)
            doc_name = chunks[i].get("metadata", {}).get("document", "").lower()
            dept_name = chunks[i].get("metadata", {}).get("department", "").lower()

            # For faculty queries, strongly prioritize dedicated department faculty profile documents
            # (e.g. AIML-Faculty-Profile.pdf, Faculty_Profile.pdf) over institute-wide student handbooks
            if is_faculty_query:
                is_dedicated_faculty_doc = "faculty" in doc_name and not ("handbook" in doc_name or "student" in doc_name)
                is_handbook = "handbook" in doc_name or "student" in doc_name
                
                # Check department alignment if mentioned in query
                aiml_match = "aiml" in q_lower and "aiml" in doc_name
                civil_match = "civil" in q_lower and "civil" in doc_name
                mech_match = "mech" in q_lower and "mech" in doc_name
                cse_match = "cse" in q_lower and ("cs" in doc_name or "cse" in doc_name)
                entc_match = "entc" in q_lower and "faculty_profile.pdf" in doc_name
                ra_match = any(k in q_lower for k in ["ra", "robotics"]) and "ra-faculty" in doc_name

                has_dept_query = any(k in q_lower for k in ["aiml", "civil", "mech", "cse", "entc", "ra", "robotics"])
                dept_match = aiml_match or civil_match or mech_match or cse_match or entc_match or ra_match

                if is_dedicated_faculty_doc and dept_match:
                    raw_score += 1.00
                elif is_dedicated_faculty_doc and has_dept_query:
                    # Penalty if this faculty profile belongs to another department than the one requested
                    raw_score -= 1.00
                elif is_dedicated_faculty_doc:
                    raw_score += 0.50
                elif is_handbook:
                    raw_score -= 1.00

            chunks[i]["rerank_score"] = raw_score
            
        # Sort descending by rerank score
        ranked = sorted(chunks, key=lambda x: x.get("rerank_score", float("-inf")), reverse=True)
        return ranked[:top_k]
    except Exception as e:
        logger.warning(f"Reranker failed or unavailable ({e}); falling back to vector similarity order.")
        return chunks[:top_k]

