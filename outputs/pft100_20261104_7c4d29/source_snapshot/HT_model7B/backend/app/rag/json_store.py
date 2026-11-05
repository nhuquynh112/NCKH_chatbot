"""Small persistent vector store used by the portable demo.

It intentionally has no database dependency: document embeddings are stored in a
JSON file and only the query is embedded at request time.  This makes the project
work on a clean Windows machine while keeping the same Retriever interface as
ChromaDB.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from pathlib import Path

from app.rag.embedding import OllamaClient
from app.rag.vector_store import Document, SearchResult


logger = logging.getLogger(__name__)


class JsonVectorStore:
    def __init__(self, path: Path, embedding_client: OllamaClient):
        self.path = path
        self.embedding_client = embedding_client
        self._records: list[tuple[Document, list[float]]] | None = None
        self._lock = threading.RLock()
        self._signature: str | None = None
        self._loaded_stat: tuple[int, int] | None = None

    def _load(self) -> list[tuple[Document, list[float]]]:
        with self._lock:
            file_stat = self.path.stat() if self.path.exists() else None
            stamp = (file_stat.st_mtime_ns, file_stat.st_size) if file_stat else None
            if self._records is not None and self._loaded_stat == stamp:
                return self._records
            if not self.path.exists():
                self._records = []
                return self._records

            raw_records = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw_records, dict):
                self._signature = raw_records.get("embedding_signature")
                raw_records = raw_records.get("records", [])
            records: list[tuple[Document, list[float]]] = []
            for record in raw_records:
                embedding = record.get("embedding")
                if not isinstance(embedding, list) or not embedding:
                    continue
                records.append(
                    (
                        Document(
                            id=str(record["id"]),
                            title=str(record.get("title") or record["id"]),
                            content=str(record.get("content", "")),
                            metadata={
                                str(key): str(value)
                                for key, value in (record.get("metadata") or {}).items()
                            },
                        ),
                        [float(value) for value in embedding],
                    )
                )
            self._records = records
            self._loaded_stat = stamp
            return records

    def count(self) -> int:
        return len(self._load())

    def get_all_documents(self) -> list[Document]:
        return [document for document, _ in self._load()]

    def is_current(self, documents: list[Document]) -> bool:
        existing = self.get_all_documents()
        if self._signature != getattr(self.embedding_client, "embedding_signature", None):
            return False
        if len(existing) != len(documents):
            return False
        return all(
            old.id == new.id
            and old.title == new.title
            and old.content == new.content
            and old.metadata == new.metadata
            for old, new in zip(existing, documents)
        )

    def build_index(
        self,
        documents: list[Document],
        embeddings_by_id: dict[str, list[float]] | None = None,
    ) -> None:
        records: list[tuple[Document, list[float]]] = []
        if embeddings_by_id:
            records = [
                (document, embeddings_by_id[document.id]) for document in documents
            ]
        elif hasattr(self.embedding_client, "embed_many"):
            batch_size = 32
            for start in range(0, len(documents), batch_size):
                batch = documents[start:start + batch_size]
                logger.info(
                    "Embedding documents %s-%s/%s",
                    start + 1,
                    start + len(batch),
                    len(documents),
                )
                embeddings = self.embedding_client.embed_many(
                    [document.content for document in batch]
                )
                records.extend(zip(batch, embeddings))
        else:
            for index, document in enumerate(documents, start=1):
                logger.info("Embedding document %s/%s: %s", index, len(documents), document.title)
                embed_document = getattr(self.embedding_client, "embed_document", self.embedding_client.embed)
                records.append((document, embed_document(document.content)))

        dimensions = {len(embedding) for _, embedding in records}
        if len(dimensions) > 1 or 0 in dimensions or any(not math.isfinite(v) for _, vector in records for v in vector):
            raise ValueError("Embedding vectors must be finite and have one consistent dimension")

        payload = [
            {
                "id": document.id,
                "title": document.title,
                "content": document.content,
                "metadata": document.metadata,
                "embedding": embedding,
            }
            for document, embedding in records
        ]
        signature = getattr(self.embedding_client, "embedding_signature", None)
        payload = {"schema_version":2, "embedding_signature":signature, "records":payload}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(self.path)
        with self._lock:
            self._records = records
            self._signature = signature
            file_stat = self.path.stat()
            self._loaded_stat = (file_stat.st_mtime_ns, file_stat.st_size)
        logger.info("JSON vector index rebuilt with %s documents", len(records))

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        records = self._load()
        if not records:
            return []
        if self._signature != getattr(self.embedding_client, "embedding_signature", None):
            raise ValueError("Embedding model/prefix changed; run rebuild_rag.py before semantic search")
        embed_query = getattr(self.embedding_client, "embed_query", self.embedding_client.embed)
        query_embedding = embed_query(query)
        if any(len(query_embedding) != len(embedding) for _, embedding in records):
            raise ValueError("Embedding dimensions differ; rebuild index with the configured model")
        hits = [
            SearchResult(
                score=self._cosine_similarity(query_embedding, embedding),
                document=document,
            )
            for document, embedding in records
        ]
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        # Clamp because floating-point noise can otherwise produce 1.0000001.
        return max(-1.0, min(1.0, dot / (left_norm * right_norm)))
