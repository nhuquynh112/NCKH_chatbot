import json
import logging
import urllib.error
import urllib.request
import socket
import threading
from typing import Any


logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    _chat_slots = threading.BoundedSemaphore(2)
    def __init__(self, base_url: str, chat_model: str, embedding_model: str, request_timeout: float = 20):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.request_timeout = request_timeout

    @property
    def embedding_signature(self) -> str:
        return self.embedding_model + "|nomic-task-prefix-v1"

    def _embedding_text(self, text: str, task: str) -> str:
        if self.embedding_model.split(":")[0] == "nomic-embed-text":
            return f"search_{task}: {text}"
        return text

    def embed_query(self, text: str) -> list[float]:
        return self.embed(self._embedding_text(text, "query"))

    def embed_document(self, text: str) -> list[float]:
        return self.embed(self._embedding_text(text, "document"))

    def _post(self, path: str, payload: dict[str, Any], timeout: int = 120) -> dict:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            raise OllamaError("Cannot connect to Ollama") from exc
        except json.JSONDecodeError as exc:
            logger.error("Ollama returned invalid JSON for %s", path)
            raise OllamaError("Ollama returned invalid JSON") from exc

    def embed(self, text: str) -> list[float]:
        result = self._post(
            "/api/embeddings",
            {"model": self.embedding_model, "prompt": text},
            timeout=min(8, self.request_timeout),
        )
        embedding = result.get("embedding")
        if not isinstance(embedding, list):
            raise OllamaError("Ollama embedding response is missing embedding")
        return embedding

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Use Ollama's batch endpoint to rebuild an index much faster."""
        if not texts:
            return []
        result = self._post(
            "/api/embed",
            {"model": self.embedding_model, "input": [self._embedding_text(text, "document") for text in texts]},
            timeout=300,
        )
        embeddings = result.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise OllamaError("Ollama batch embedding response is invalid")
        return embeddings

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self._chat_slots.acquire(timeout=.1):
            raise OllamaError("Local model busy; please retry or contact support")
        try:
            return self._chat(system_prompt, user_prompt)
        finally:
            self._chat_slots.release()

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        result = self._post(
            "/api/chat",
            {
                "model": self.chat_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # CSKH cần câu trả lời ổn định và bám dữ liệu hơn tính sáng tạo.
                # Repeating prices/specs from the supplied context is desired.
                "options": {"temperature": 0, "num_predict": 384, "num_ctx": 4096, "repeat_penalty": 1.0},
                "keep_alive": "30m",
            },
            timeout=self.request_timeout,
        )
        try:
            return result["message"]["content"]
        except KeyError as exc:
            raise OllamaError("Ollama chat response is missing content") from exc

    def warm_up(self) -> None:
        self._post(
            "/api/generate",
            {
                "model": self.chat_model,
                "prompt": "",
                "stream": False,
                "keep_alive": "30m",
            },
            timeout=300,
        )

    def is_available(self) -> bool:
        try:
            with urllib.request.urlopen(self.base_url + "/api/tags", timeout=3) as response:
                names = {item["name"] for item in json.load(response).get("models", [])}
                expected = {model if ":" in model else model + ":latest" for model in [self.chat_model, self.embedding_model]}
                return expected.issubset(names)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            logger.warning("Ollama health check failed at %s", self.base_url)
            return False
