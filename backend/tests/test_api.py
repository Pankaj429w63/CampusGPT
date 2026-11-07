import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "message" in data

def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_get_readiness():
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert "ollama_ready" in data
    assert "chromadb_ready" in data
    assert "collection_chunks_count" in data
    assert "documents_count" in data

def test_readiness_counts_documents_recursively(monkeypatch, tmp_path):
    from app.core import config
    # Setup dummy department folders with supported and unsupported files
    mock_docs = tmp_path / "documents"
    mock_docs.mkdir()
    dept1 = mock_docs / "aiml"
    dept1.mkdir()
    (dept1 / "doc1.pdf").write_text("dummy", encoding="utf-8")
    (dept1 / "doc2.docx").write_text("dummy", encoding="utf-8")

    dept2 = mock_docs / "CS"
    dept2.mkdir()
    (dept2 / "doc3.md").write_text("dummy", encoding="utf-8")
    (dept2 / "ignore.zip").write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(config.settings, "DATA_DOCUMENTS_DIR", mock_docs)

    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    # Should count 3 supported files across department folders, ignoring the zip and directories
    assert data["documents_count"] == 3


def test_post_ask_empty_question():
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "too short" in data["answer"] or "cannot be empty" in data["answer"]

def test_post_ask_no_docs_fallback():
    # When no documents are stored in Chroma, it gracefully returns contract with fallback message
    response = client.post("/ask", json={"question": "What is the fee structure?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "question" in data
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)

