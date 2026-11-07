from typing import List, Dict, Any, Optional
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CampusGPT, an AI-powered smart university academic assistant.
Your duty is to answer questions for students and faculty accurately based strictly on the provided university context.

CRITICAL INSTRUCTIONS:
1. Base your answer ONLY on the retrieved university context provided below.
2. If the context does not contain sufficient facts to answer the question, or if no context is provided, you MUST explicitly state:
"The available university documents do not contain sufficient information to answer this question."
3. Do NOT extrapolate, speculate, or invent university policies, dates, marks, professor names, or course information.
4. Department Attribution Guardrail: Do NOT attribute facts, programs, or courses to an academic department unless the retrieved section or text explicitly supports that attribution. Do not treat folder-derived department metadata as proof of the actual section's department, especially for institute-wide documents like the student handbook.
5. Keep answers professional, concise, academic, and well-structured.
"""

def build_prompt_with_context(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    if not context_chunks:
        context_str = "No university document context was found for this query."
    else:
        formatted_chunks = []
        for i, chunk in enumerate(context_chunks, 1):
            meta = chunk.get("metadata", {})
            doc_name = meta.get("document", "Unknown Document")
            dept = meta.get("department", "general")
            section = meta.get("section", "").strip()
            page_num = meta.get("page", 1)
            chunk_text = chunk.get("text", "").strip()
            
            section_info = f", Section: {section}" if section else ""
            formatted_chunks.append(
                f"[Source {i}: {doc_name} (Dept: {dept}{section_info}, Page {page_num})]\n{chunk_text}"
            )
        context_str = "\n\n".join(formatted_chunks)

    prompt = f"""Context from University Documents:
{context_str}

User Question: {question}

Answer:"""
    return prompt

async def check_ollama_health() -> Dict[str, Any]:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                has_target = any(settings.OLLAMA_MODEL in m for m in models)
                return {
                    "running": True,
                    "available_models": models,
                    "target_model_available": has_target
                }
            return {
                "running": False,
                "error": f"Ollama HTTP {resp.status_code}",
                "target_model_available": False
            }
    except Exception as e:
        return {
            "running": False,
            "error": str(e),
            "target_model_available": False
        }

async def generate_answer_via_ollama(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    prompt = build_prompt_with_context(question, context_chunks)
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"Ollama returned HTTP {response.status_code}: {response.text}")
            result = response.json()
            answer = result.get("response", "").strip()
            return answer
    except httpx.ConnectError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. "
            "Please ensure Ollama is installed and running (`ollama serve`)."
        )
    except httpx.TimeoutException:
        raise TimeoutError(f"Request to Ollama timed out after {settings.OLLAMA_TIMEOUT}s.")

