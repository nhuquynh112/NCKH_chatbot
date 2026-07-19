from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _resolve_backend_path(path: Path) -> Path:
    return path if path.is_absolute() else BACKEND_ROOT / path


class Settings(BaseSettings):
    DATABASE_URL: str
    AI_SERVICE_URL: Optional[str] = None

    # Local RAG / Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    CHAT_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    CHROMA_COLLECTION: str = "techcare_rag"
    CHROMA_PERSIST_DIR: Path = Path("chroma_db")
    PROMPT_PATH: Path = Path("rag_data/system_prompt.txt")
    KNOWLEDGE_BASE_PATH: Path = Path("rag_data/knowledge_base.md")
    PRODUCT_CATALOG_PATH: Path = Path("rag_data/product_catalog_extended.md")
    LEGACY_VECTOR_INDEX_PATH: Path = Path("rag_data/vector_index.json")
    RAG_DOCUMENTS_PATH: Path = Path("rag_data/techcare_rag_documents.json")
    PRODUCTS_PATH: Path = Path("rag_data/techcare_products.json")
    RAG_TOP_K: int = 4
    MIN_RETRIEVAL_SCORE: float = 0.55
    
    # JWT Settings
    SECRET_KEY: str = "super_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    @property
    def ollama_base_url(self) -> str:
        return self.OLLAMA_BASE_URL

    @property
    def chat_model(self) -> str:
        return self.CHAT_MODEL

    @property
    def embedding_model(self) -> str:
        return self.EMBEDDING_MODEL

    @property
    def collection_name(self) -> str:
        return self.CHROMA_COLLECTION

    @property
    def chroma_persist_dir(self) -> Path:
        return _resolve_backend_path(self.CHROMA_PERSIST_DIR)

    @property
    def prompt_path(self) -> Path:
        return _resolve_backend_path(self.PROMPT_PATH)

    @property
    def knowledge_base_path(self) -> Path:
        return _resolve_backend_path(self.KNOWLEDGE_BASE_PATH)

    @property
    def product_catalog_path(self) -> Path:
        return _resolve_backend_path(self.PRODUCT_CATALOG_PATH)

    @property
    def legacy_vector_index_path(self) -> Path:
        return _resolve_backend_path(self.LEGACY_VECTOR_INDEX_PATH)

    @property
    def rag_documents_path(self) -> Path:
        return _resolve_backend_path(self.RAG_DOCUMENTS_PATH)

    @property
    def products_path(self) -> Path:
        return _resolve_backend_path(self.PRODUCTS_PATH)

    @property
    def default_top_k(self) -> int:
        return self.RAG_TOP_K

    @property
    def min_retrieval_score(self) -> float:
        return self.MIN_RETRIEVAL_SCORE

    @property
    def knowledge_paths(self) -> list[Path]:
        return [self.knowledge_base_path, self.product_catalog_path]

    class Config:
        env_file = ".env"

settings = Settings()
