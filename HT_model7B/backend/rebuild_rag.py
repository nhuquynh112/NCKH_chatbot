import sys

from app.config import settings
from app.rag.chat_service import rebuild_index
from app.rag.document_builder import write_product_rag_documents

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    count, issues = write_product_rag_documents(
        settings.products_path,
        settings.rag_documents_path,
    )
    for issue in issues:
        print(issue.format())
    print(f"Generated {count} product RAG documents -> {settings.rag_documents_path}")

    rebuild_index()
