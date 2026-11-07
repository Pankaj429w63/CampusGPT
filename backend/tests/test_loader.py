import pytest
from pathlib import Path
from app.rag.loader import split_text_into_chunks, process_file_into_chunks

def test_split_text_into_chunks():
    sample_text = (
        "CampusGPT is an AI-powered smart university platform. "
        "It assists students with timetables and examinations. "
        "All academic policies must be strictly followed according to institute bylaws."
    )
    chunks = split_text_into_chunks(sample_text, chunk_size=80, chunk_overlap=20)
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)
    assert "CampusGPT" in chunks[0]

def test_process_markdown_file(tmp_path: Path):
    doc_path = tmp_path / "test_regulations.md"
    doc_path.write_text(
        "# Attendance Policy\n\nA minimum of 75 percent attendance is mandatory for semester exams.",
        encoding="utf-8"
    )
    chunks = process_file_into_chunks(doc_path)
    assert len(chunks) == 1
    assert chunks[0].metadata["document"] == "test_regulations.md"
    assert chunks[0].metadata["department"] == "general"
    assert chunks[0].metadata["page"] == 1
    assert "75 percent attendance" in chunks[0].text

def test_department_metadata_and_relative_path(tmp_path: Path):
    aiml_dir = tmp_path / "aiml"
    aiml_dir.mkdir()
    doc_path = aiml_dir / "curriculum.md"
    doc_path.write_text("Artificial Intelligence and Machine Learning curriculum 2026.", encoding="utf-8")

    chunks = process_file_into_chunks(doc_path, base_dir=tmp_path)
    assert len(chunks) == 1
    assert chunks[0].metadata["department"] == "aiml"
    assert chunks[0].metadata["document"] == "curriculum.md"
    assert chunks[0].metadata["relative_path"] == "aiml/curriculum.md"
    assert chunks[0].metadata["chunk_index"] == 0
    assert "section" in chunks[0].metadata

def test_heading_preserved_across_chunk_boundary(tmp_path: Path):
    doc_path = tmp_path / "handbook.md"
    # Long text under a heading that will split into multiple chunks
    heading = "# Department of Civil Engineering\n\n"
    para = (
        "Building Information Modeling (BIM) is integrated into our advanced curriculum. "
        "Students learn sustainable design principles, reinforced concrete analysis, "
        "and computational structural mechanics across semester projects and capstones.\n\n"
    ) * 8
    doc_path.write_text(heading + para, encoding="utf-8")

    chunks = process_file_into_chunks(doc_path)
    assert len(chunks) > 1
    # Verify that even chunks past the first one retain the active section heading in metadata
    for i, c in enumerate(chunks):
        assert c.metadata["section"] == "Department of Civil Engineering", f"Chunk {i} lost section heading"

def test_llm_prompt_source_formatting():
    from app.services.llm import build_prompt_with_context, SYSTEM_PROMPT

    chunks = [
        {
            "text": "Civil engineering curriculum integrates BIM and sustainable design.",
            "metadata": {
                "document": "STUDENT-HANDBOOK-2026-27.pdf",
                "department": "aiml",
                "section": "Department of Civil Engineering",
                "page": 15
            }
        }
    ]
    prompt = build_prompt_with_context("What is the AIML curriculum?", chunks)
    assert "Dept: aiml" in prompt
    assert "Section: Department of Civil Engineering" in prompt
    assert "STUDENT-HANDBOOK-2026-27.pdf" in prompt
    assert "Page 15" in prompt
    assert "Department Attribution Guardrail" in SYSTEM_PROMPT

def test_multiple_headings_on_same_page(tmp_path: Path):
    doc_path = tmp_path / "multi_dept.md"
    content = (
        "# Department of Civil Engineering\n\n"
        "Civil engineering studies civil infrastructure and structures.\n\n"
        "# Department of Mechanical Engineering\n\n"
        "Mechanical engineering studies thermodynamics and mechanics.\n\n"
    )
    doc_path.write_text(content, encoding="utf-8")
    chunks = process_file_into_chunks(doc_path)
    assert len(chunks) >= 2
    assert chunks[0].metadata["section"] == "Department of Civil Engineering"
    assert chunks[-1].metadata["section"] == "Department of Mechanical Engineering"

def test_page1_heading_a_then_page2_continuation_then_heading_b(monkeypatch, tmp_path: Path):
    from app.rag import loader
    doc_path = tmp_path / "cross_page.pdf"
    doc_path.write_bytes(b"%PDF-mock")

    # Page 1: Heading A followed by text A
    # Page 2: Continuation text of A, then Heading B followed by text B
    monkeypatch.setattr(loader, "load_pdf", lambda path: [
        {
            "page": 1,
            "text": "# Department of Civil Engineering\nCivil engineering focuses on structural analysis."
        },
        {
            "page": 2,
            "text": (
                "Students also design water resources and concrete structures in civil projects.\n\n"
                "# Department of Mechanical Engineering\n"
                "Mechanical engineering covers thermodynamics, fluid mechanics, and manufacturing."
            )
        }
    ])

    chunks = loader.process_file_into_chunks(doc_path)
    # Page 1 Chunk: Heading A
    assert chunks[0].metadata["page"] == 1
    assert chunks[0].metadata["section"] == "Department of Civil Engineering"

    # Page 2 Chunk 1: Continuation of A before Heading B must retain Heading A
    assert chunks[1].metadata["page"] == 2
    assert "Students also design water resources" in chunks[1].text
    assert chunks[1].metadata["section"] == "Department of Civil Engineering"

    # Page 2 Chunk 2: Heading B and subsequent text must have Heading B
    assert chunks[2].metadata["page"] == 2
    assert "Department of Mechanical Engineering" in chunks[2].text
    assert chunks[2].metadata["section"] == "Department of Mechanical Engineering"

def test_new_document_starts_with_empty_section(tmp_path: Path):
    # Doc 1: Has a section heading
    doc1 = tmp_path / "doc1.md"
    doc1.write_text("# Department of Civil Engineering\nCivil engineering content.", encoding="utf-8")
    chunks1 = process_file_into_chunks(doc1)
    assert chunks1[0].metadata["section"] == "Department of Civil Engineering"

    # Doc 2: Has no headings anywhere
    doc2 = tmp_path / "doc2.md"
    doc2.write_text("General institutional statement with no section headings at all.", encoding="utf-8")
    chunks2 = process_file_into_chunks(doc2)
    assert chunks2[0].metadata["section"] == "", "New document incorrectly inherited previous section heading"





