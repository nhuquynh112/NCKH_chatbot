"""Small accent-insensitive BM25 retriever; no new runtime dependency."""
from collections import Counter
import math
import re

from app.rag.faq_matcher import normalize, STOP
from app.rag.vector_store import Document, SearchResult


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", normalize(text)) if len(t) > 1 and t not in STOP]


def bm25_search(query: str, documents: list[Document], top_k: int) -> list[SearchResult]:
    query_tokens = set(tokenize(query))
    if not query_tokens or not documents:
        return []
    bags = [Counter(tokenize(doc.title + " " + doc.title + " " + doc.content)) for doc in documents]
    lengths = [sum(bag.values()) for bag in bags]
    average = sum(lengths) / max(1, len(lengths)) or 1
    frequencies = {term:sum(term in bag for bag in bags) for term in query_tokens}
    hits = []
    for doc, bag, length in zip(documents, bags, lengths):
        score = 0.0
        for term in query_tokens:
            frequency = bag[term]
            if frequency:
                idf = math.log(1 + (len(bags) - frequencies[term] + .5) / (frequencies[term] + .5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * length / average))
        if score:
            hits.append(SearchResult(score, doc))
    return sorted(hits, key=lambda hit:hit.score, reverse=True)[:top_k]
