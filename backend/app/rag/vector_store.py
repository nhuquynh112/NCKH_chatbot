from dataclasses import dataclass, field
import json
import logging
import re
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    score: float
    document: Document


def split_markdown_sections(text: str):
    sections = []

    current_parent = ""
    current_title = "Tổng quan"
    current_lines = []

    for line in text.splitlines():

        if re.match(r"^#\s", line):
            if current_lines:
                sections.append(
                    (
                        current_parent,
                        current_title,
                        "\n".join(current_lines).strip(),
                    )
                )

            current_parent = line.replace("#", "").strip()
            current_title = current_parent
            current_lines = [line]

        elif re.match(r"^##\s", line):
            if current_lines:
                sections.append(
                    (
                        current_parent,
                        current_title,
                        "\n".join(current_lines).strip(),
                    )
                )

            current_title = line.replace("##", "").strip()
            current_lines = [line]

        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            (
                current_parent,
                current_title,
                "\n".join(current_lines).strip(),
            )
        )

    return sections


def load_markdown_documents(paths: list[Path]) -> list[Document]:
    documents: list[Document] = []
    next_id = 1

    for path in paths:
        if not path.exists():
            logger.warning("Knowledge source does not exist: %s", path)
            continue

        sections = split_markdown_sections(path.read_text(encoding="utf-8"))
        for parent, title, content in sections:
            documents.append(
                Document(
                    id=f"doc_{next_id:03d}",
                    title=title,
                    content=(
                        f"Nguồn: {path.name}\n"
                        f"Chủ đề: {parent}\n"
                        f"Mục: {title}\n\n"
                        f"{content}"
                    ),
                    metadata={"source": path.name, "parent": parent, "title": title},
                )
            )
            next_id += 1

    logger.info("Loaded %s knowledge documents", len(documents))
    return documents


def load_legacy_vector_index(path: Path) -> tuple[list[Document], dict[str, list[float]]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    documents: list[Document] = []
    embeddings_by_id: dict[str, list[float]] = {}

    for record in records:
        doc = Document(
            id=record["id"],
            title=record["title"],
            content=record["content"],
            metadata={"source": path.name, "title": record["title"]},
        )
        documents.append(doc)
        embeddings_by_id[doc.id] = record["embedding"]

    logger.info("Loaded %s documents from legacy vector index", len(documents))
    return documents, embeddings_by_id


def result_to_record(result: SearchResult) -> dict:
    return {
        "id": result.document.id,
        "title": result.document.title,
        "content": result.document.content,
    }


def record_to_document(record: dict) -> Document:
    return Document(
        id=record["id"],
        title=record["title"],
        content=record["content"],
        metadata=record.get("metadata", {}),
    )
