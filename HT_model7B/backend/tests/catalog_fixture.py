"""The original regression questions refer to the preserved 53-product corpus."""
import json
from app.config import BACKEND_ROOT, Settings


HISTORICAL = BACKEND_ROOT / "rag_data"


def historical_settings():
    return Settings(_env_file=None, PRODUCTS_PATH=HISTORICAL / "techcare_products.json",
                    RAG_DOCUMENTS_PATH=HISTORICAL / "techcare_rag_documents.json",
                    PRODUCT_CATALOG_PATH=HISTORICAL / "product_catalog_extended.md",
                    KNOWLEDGE_BASE_PATH=HISTORICAL / "knowledge_base.md",
                    CURATED_FAQ_PATH=HISTORICAL / "faq_curated.json",
                    LEGACY_VECTOR_INDEX_PATH=HISTORICAL / "vector_index.json")


def pin_historical_catalog(catalog):
    # These tests exercise fixed historical questions, never the developer DB.
    catalog.products_path = HISTORICAL / "techcare_products.json"
    catalog.rag_documents_path = HISTORICAL / "techcare_rag_documents.json"
    rows = json.loads((HISTORICAL / "techcare_products.json").read_text(encoding="utf-8"))
    catalog._load_database_products = lambda: [catalog._normalize_product(row) for row in rows]
    return catalog
