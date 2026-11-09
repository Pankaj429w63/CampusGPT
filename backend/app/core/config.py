from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "CampusGPT API"
    APP_VERSION: str = "1.0.0"
    
    # Base paths
    BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_ROOT: Path = BACKEND_DIR.parent
    DATA_DOCUMENTS_DIR: Path = PROJECT_ROOT / "data" / "documents"
    CHROMA_PERSIST_DIR: Path = BACKEND_DIR / "data" / "chroma_db"
    
    # Vector DB Collection
    CHROMA_COLLECTION_NAME: str = "campusgpt_knowledge"
    
    # Models
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    
    # Ollama LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT: float = 120.0
    
    # Retrieval parameters
    INITIAL_TOP_K: int = 8
    RERANK_TOP_K: int = 4
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
