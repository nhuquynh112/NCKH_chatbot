import logging
from pathlib import Path
from typing import Any

from app.rag.embedding import OllamaClient
from app.rag.vector_store import Document, SearchResult


logger = logging.getLogger(__name__)


class ChromaUnavailableError(RuntimeError):
    pass


class ChromaVectorStore:
    def __init__(
        self,
        persist_dir: Path,
        collection_name: str,
        embedding_client: OllamaClient,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_client = embedding_client
        self._client: Any | None = None
        self._collection: Any | None = None

    def _import_chromadb(self):
        try:
            import chromadb
        except ImportError as exc:
            raise ChromaUnavailableError(
                "chromadb is not installed. Install dependencies from requirements.txt."
            ) from exc
        return chromadb

    def client(self):
        if self._client is None:
            chromadb = self._import_chromadb()
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        return self._client

    def collection(self):
        if self._collection is None:
            self._collection = self.client().get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def is_available(self) -> bool:
        try:
            self.collection()
            return True
        except ChromaUnavailableError:
            logger.warning("ChromaDB is not available")
            return False

    def count(self) -> int:
        return int(self.collection().count())

    def build_index(
        self,
        documents: list[Document],
        embeddings_by_id: dict[str, list[float]] | None = None,
    ) -> None:
        client = self.client()
        try:
            client.delete_collection(self.collection_name)
        except ValueError:
            pass

        self._collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        if not documents:
            logger.warning("No documents were provided for ChromaDB indexing")
            return

        logger.info("Building ChromaDB index with %s documents", len(documents))
        if embeddings_by_id is not None:
            embeddings = [embeddings_by_id[doc.id] for doc in documents]
            logger.info("Using precomputed embeddings for ChromaDB import")
        else:
            embeddings = []
            for index, doc in enumerate(documents, start=1):
                logger.info("Embedding document %s/%s: %s", index, len(documents), doc.title)
                embeddings.append(self.embedding_client.embed(doc.content))
        self._collection.add(
            ids=[doc.id for doc in documents],
            documents=[doc.content for doc in documents],
            metadatas=[
                {"title": doc.title, **{k: str(v) for k, v in doc.metadata.items()}}
                for doc in documents
            ],
            embeddings=embeddings,
        )
        logger.info("ChromaDB index was rebuilt: %s", self.collection_name)

    def get_all_documents(self) -> list[Document]:
        data = self.collection().get(include=["documents", "metadatas"])
        ids = data.get("ids", [])
        contents = data.get("documents", [])
        metadatas = data.get("metadatas", [])

        documents: list[Document] = []
        for doc_id, content, metadata in zip(ids, contents, metadatas):
            metadata = metadata or {}
            documents.append(
                Document(
                    id=doc_id,
                    title=metadata.get("title", doc_id),
                    content=content,
                    metadata={str(k): str(v) for k, v in metadata.items()},
                )
            )
        return documents

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        if self.count() == 0:
            logger.warning("ChromaDB collection is empty: %s", self.collection_name)
            return []

        query_embedding = self.embedding_client.embed(query)
        result = self.collection().query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[SearchResult] = []
        ids = result.get("ids", [[]])[0]
        contents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for doc_id, content, metadata, distance in zip(
            ids, contents, metadatas, distances
        ):
            metadata = metadata or {}
            score = max(0.0, 1.0 - float(distance))
            hits.append(
                SearchResult(
                    score=score,
                    document=Document(
                        id=doc_id,
                        title=metadata.get("title", doc_id),
                        content=content,
                        metadata={str(k): str(v) for k, v in metadata.items()},
                    ),
                )
            )
        return hits
