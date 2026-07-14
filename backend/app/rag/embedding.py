import json
import logging
import urllib.error
import urllib.request
from typing import Any


logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, chat_model: str, embedding_model: str):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model

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
        except urllib.error.URLError as exc:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            raise OllamaError("Cannot connect to Ollama") from exc
        except json.JSONDecodeError as exc:
            logger.error("Ollama returned invalid JSON for %s", path)
            raise OllamaError("Ollama returned invalid JSON") from exc

    def embed(self, text: str) -> list[float]:
        result = self._post(
            "/api/embeddings",
            {"model": self.embedding_model, "prompt": text},
        )
        embedding = result.get("embedding")
        if not isinstance(embedding, list):
            raise OllamaError("Ollama embedding response is missing embedding")
        return embedding

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        result = self._post(
            "/api/chat",
            {
                "model": self.chat_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {"temperature": 0.2},
            },
        )
        try:
            return result["message"]["content"]
        except KeyError as exc:
            raise OllamaError("Ollama chat response is missing content") from exc

    def is_available(self) -> bool:
        try:
            with urllib.request.urlopen(self.base_url + "/api/tags", timeout=3):
                return True
        except urllib.error.URLError:
            logger.warning("Ollama health check failed at %s", self.base_url)
            return False
