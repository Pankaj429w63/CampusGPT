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
    assert "[Source 1: policy.pdf (Dept: general, Page 3)]" in prompt
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

def test_faculty_reranking_prioritization():
    from app.rag.reranker import rerank_chunks
    chunks = [
        {
            "text": "Director Dr. Ketan Kotecha, Civil Coordinator Mr. Abhijit Hambir, Mech Coordinator Mr. Vishal Sharma",
            "metadata": {"document": "STUDENT-HANDBOOK-2026-27.pdf", "department": "aiml", "page": 47}
        },
        {
            "text": "Dr. Sumit Kumar, Professor and Head AI&ML, Ph.D, M. Tech., B. Tech.",
            "metadata": {"document": "AIML-Faculty-Profile.pdf", "department": "aiml", "page": 3}
        }
    ]
    ranked = rerank_chunks("List AIML department faculty with their designations.", chunks, top_k=2)
    # The dedicated AIML faculty document must be prioritized ahead of the student handbook
    assert ranked[0]["metadata"]["document"] == "AIML-Faculty-Profile.pdf"
    assert "Sumit Kumar" in ranked[0]["text"]

def test_faculty_prompt_guardrail():
    from app.services.llm import SYSTEM_PROMPT
    assert "Faculty Department Attribution" in SYSTEM_PROMPT
    assert "do NOT attribute or list them as faculty members of the requested department" in SYSTEM_PROMPT

def test_aiml_multi_faculty_retrieval_and_completeness():
    from app.rag.pipeline import retrieve_and_rerank
    chunks = retrieve_and_rerank("List AIML department faculty with their designations.")
    # Must retrieve all relevant faculty introduction chunks from AIML-Faculty-Profile.pdf
    assert len(chunks) == 29
    aiml_docs = [c["metadata"]["document"] for c in chunks]
    assert all(d == "AIML-Faculty-Profile.pdf" for d in aiml_docs)

    # Check key professors across leadership, professorship, and associates are present
    combined_text = "\n".join(c["text"] for c in chunks)
    assert "Dr. Ketan Kotecha" in combined_text
    assert "Dr.Tanveer Ahmed" in combined_text or "Dr. Tanveer Ahmed" in combined_text
    assert "Dr. Sumit Kumar" in combined_text
    assert "Dr. Anupkumar M Bongale" in combined_text
    assert "Dr. Anjali More" in combined_text
    assert "Dr. Sangeeta Pant" in combined_text
    assert "Dr. Pooja Vinayak Kamat" in combined_text
    assert "Prof. Amruta S. Kolhar" in combined_text

def test_faculty_cross_department_penalty():
    from app.rag.reranker import rerank_chunks
    chunks = [
        {
            "text": "Dr. Suman Lata Tripathi, Professor, ENTC",
            "metadata": {"document": "Faculty_Profile.pdf", "department": "ENTC", "page": 1}
        },
        {
            "text": "Dr. Ketan Kotecha, Professor & Director SIT Pune",
            "metadata": {"document": "AIML-Faculty-Profile.pdf", "department": "aiml", "page": 1}
        }
    ]
    # In an AIML faculty query, the AIML profile must rank top and the ENTC profile must be penalized
    ranked = rerank_chunks("List AIML department faculty", chunks, top_k=2)
    assert ranked[0]["metadata"]["document"] == "AIML-Faculty-Profile.pdf"
    assert ranked[1]["metadata"]["document"] == "Faculty_Profile.pdf"
    assert ranked[0]["rerank_score"] > ranked[1]["rerank_score"]


def test_academic_calendar_optimization_and_completeness():
    from app.rag.pipeline import retrieve_and_rerank
    chunks = retrieve_and_rerank("Explain the academic calendar for 2026-27.")
    assert len(chunks) == 2
    # Verify documents and pages
    assert all(c["metadata"]["document"] == "Academic_Calendar_2026-27.pdf.pdf" for c in chunks)
    assert chunks[0]["metadata"]["page"] == 1
    assert chunks[1]["metadata"]["page"] == 2

    # Verify both ODD and EVEN semesters are completely represented
    odd_text = chunks[0]["text"]
    even_text = chunks[1]["text"]

    # Check key ODD 2026 dates
    assert "B.Tech - First Year - ODD 2026" in odd_text
    assert "Induction Registration and Session Commencement" in odd_text
    assert "July 20 to July 26, 2026" in odd_text
    assert "Techfest & Cultural Fest" in odd_text
    assert "October 12 to October 17, 2026" in odd_text
    assert "Diwali Vacation" in odd_text
    assert "November 6 to November 11, 2026" in odd_text
    assert "End Semester Examination (ESE ODD 2026)" in odd_text
    assert "December 7 to December 12, 2026" in odd_text
    assert "4th January 2027" in odd_text

    # Check key EVEN 2027 dates
    assert "EVEN 2027" in even_text
    assert "Registration and Session Commencement - B.Tech PROTA" in even_text
    assert "January 4 to January 9, 2027" in even_text
    assert "Industry Conclave" in even_text
    assert "April 12 to April 17, 2027" in even_text
    assert "Backlog Examination (ODD Semester)" in even_text
    assert "May 3 to May 15, 2027" in even_text
    assert "End Semester Examination (EVEN Semester)" in even_text
    assert "May 17 to May 29, 2027" in even_text
    assert "1st July 2027" in even_text

    # Check official authorities are preserved
    assert "Dr. Mangal Singh" in odd_text and "Dr. Mangal Singh" in even_text
    assert "Dr. Deepali Vora" in odd_text and "Dr. Deepali Vora" in even_text
    assert "Dr. Ketan Kotecha" in odd_text and "Dr. Ketan Kotecha" in even_text


def test_ollama_timeout_configuration():
    from app.core.config import settings
    # Verify timeout is configured to at least 120 seconds to prevent read timeouts on CPU
    assert settings.OLLAMA_TIMEOUT >= 120.0




