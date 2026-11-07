import pytest
from app.rag.reranker import rerank_chunks
from app.services.llm import build_prompt_with_context

def test_reranker_fallback_or_order(monkeypatch):
    # Mock reranker model loading to prevent remote HuggingFace model download during CI/tests
    from app.rag import reranker
    monkeypatch.setattr(reranker, "get_reranker_model", lambda: (_ for _ in ()).throw(RuntimeError("Mocked offline reranker")))

    chunks = [
        {"text": "Physics lab is held in Block B on Thursday mornings.", "metadata": {"document": "schedule.txt", "page": 1}},
        {"text": "Attendance requirement is 75 percent for all engineering students.", "metadata": {"document": "rules.txt", "page": 1}},
    ]
    query = "What is the attendance requirement?"
    ranked = rerank_chunks(query, chunks, top_k=2)
    assert len(ranked) == 2
    assert all("text" in c for c in ranked)

def test_build_prompt_with_context():
    chunks = [
        {"text": "75 percent attendance is mandatory.", "metadata": {"document": "policy.pdf", "page": 3}}
    ]
    prompt = build_prompt_with_context("What is the attendance rule?", chunks)
    assert "User Question: What is the attendance rule?" in prompt
    assert "[Source 1: policy.pdf (Page 3)]" in prompt
    assert "75 percent attendance is mandatory." in prompt

def test_recursive_discovery_across_departments(tmp_path):
    from app.rag.pipeline import discover_document_files
    
    depts = ["aiml", "CIVIL", "CS", "ENTC", "MECH", "RA"]
    for d in depts:
        dept_dir = tmp_path / d
        dept_dir.mkdir()
        (dept_dir / f"{d}_syllabus.md").write_text(f"Syllabus for {d}", encoding="utf-8")
        (dept_dir / f"{d}_notes.txt").write_text(f"Notes for {d}", encoding="utf-8")
        # Unsupported file
        (dept_dir / f"{d}_archive.zip").write_text("dummy", encoding="utf-8")
        # System/hidden file
        (dept_dir / f".hidden_{d}").write_text("hidden", encoding="utf-8")

    discovered = discover_document_files(tmp_path)
    # Should discover 6 depts * 2 supported files = 12 files
    assert len(discovered) == 12
    discovered_rel = [str(f.relative_to(tmp_path)).replace("\\", "/") for f in discovered]
    for d in depts:
        assert f"{d}/{d}_syllabus.md" in discovered_rel
        assert f"{d}/{d}_notes.txt" in discovered_rel
        assert f"{d}/{d}_archive.zip" not in discovered_rel
        assert f"{d}/.hidden_{d}" not in discovered_rel

def test_collision_safe_deterministic_chunk_ids(monkeypatch):
    from app.rag.loader import DocumentChunk
    from app.rag import vectorstore

    upserted_calls = []

    class MockCollection:
        def upsert(self, ids, documents, embeddings, metadatas):
            upserted_calls.append({
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas
            })

    monkeypatch.setattr(vectorstore, "get_collection", lambda: MockCollection())
    monkeypatch.setattr(vectorstore, "generate_embeddings", lambda texts: [[0.1] * 10 for _ in texts])

    # 1. Ingest document from CS
    chunk_cs = DocumentChunk(
        text="CS lab timetable and curriculum.",
        metadata={
            "department": "CS",
            "document": "curriculum.pdf",
            "page": 1,
            "chunk_index": 0
        }
    )
    vectorstore.add_chunks_to_vectorstore([chunk_cs])

    # 2. Ingest document with same filename from MECH
    chunk_mech = DocumentChunk(
        text="Mechanical engineering curriculum.",
        metadata={
            "department": "MECH",
            "document": "curriculum.pdf",
            "page": 1,
            "chunk_index": 0
        }
    )
    vectorstore.add_chunks_to_vectorstore([chunk_mech])

    # 3. Repeated ingestion of CS document (idempotent / overwrite test)
    vectorstore.add_chunks_to_vectorstore([chunk_cs])

    assert len(upserted_calls) == 3
    # Check IDs are distinct between CS and MECH
    cs_id = upserted_calls[0]["ids"][0]
    mech_id = upserted_calls[1]["ids"][0]
    cs_repeat_id = upserted_calls[2]["ids"][0]

    assert cs_id == "CS_curriculum.pdf_p1_c0"
    assert mech_id == "MECH_curriculum.pdf_p1_c0"
    assert cs_repeat_id == cs_id
    assert cs_id != mech_id

