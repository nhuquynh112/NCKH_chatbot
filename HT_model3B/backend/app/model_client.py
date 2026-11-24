"""Chat provider selection; retrieval embeddings always keep their original model."""
import json
from contextvars import ContextVar
import logging
from pathlib import Path
import socket
import urllib.error
import urllib.request

from app.rag.embedding import OllamaClient, OllamaError

logger = logging.getLogger(__name__)
PROFILE_PATH = Path(__file__).resolve().parents[1] / "model_serving/profiles/qwen25_7b.json"


class ModelNotReady(OllamaError):
    """An explicitly selected adapter must never be replaced with another model."""


class HfLoraClient(OllamaClient):
    def __init__(self, config):
        super().__init__(config.ollama_base_url, config.chat_model, config.embedding_model,
                         max(1, config.ai_response_timeout_seconds - 9))
        self.server_url = config.HF_LORA_BASE_URL.rstrip("/")
        self.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        self._generation_metadata = ContextVar(f"generation_metadata_{id(self)}", default=None)

    @property
    def last_generation_metadata(self):
        return self._generation_metadata.get()

    def _server_request(self, path, payload=None, timeout=3):
        request = urllib.request.Request(
            self.server_url + path,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read()).get("error", str(exc.code))
            except (ValueError, OSError):
                detail = str(exc.code)
            finally:
                exc.close()
            raise ModelNotReady(f"7B server HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, ValueError) as exc:
            if isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError):
                raise ModelNotReady("7B server request timed out") from exc
            raise ModelNotReady(f"7B server unavailable at {self.server_url}: {type(exc).__name__}") from exc
        if not isinstance(result, dict):
            raise ModelNotReady("7B server returned an invalid response")
        return result

    def identity(self):
        state = self._server_request("/health")
        self._verify_identity(state)
        return state

    def _verify_identity(self, state):
        expected = {"model": self.chat_model,
                    "adapter_sha256": self.profile["adapter_sha256"],
                    "checkpoint_sha256": self.profile["checkpoint_sha256"]}
        if state.get("status") != "ready" or not state.get("adapter_loaded"):
            raise ModelNotReady(f"7B not_ready: {state.get('error') or state.get('status')}")
        if any(state.get(k) != v for k, v in expected.items()):
            raise ModelNotReady("7B server identity does not match the verified checkpoint and adapter")

    def chat(self, system_prompt, user_prompt):
        self._generation_metadata.set(None)
        result = self._server_request("/generate", {
            "model": self.chat_model, "system_prompt": system_prompt,
            "user_prompt": user_prompt, "max_new_tokens": 384,
            "num_ctx": 4096, "temperature": 0, "repeat_penalty": 1.0,
            "timeout_seconds": self.request_timeout,
        }, timeout=self.request_timeout + 1)
        self._verify_identity(result)
        if not isinstance(result.get("answer"), str) or not result["answer"].strip():
            raise ModelNotReady("7B server returned an empty answer")
        self._generation_metadata.set({k:result.get(k) for k in
            ("model","adapter_sha256","checkpoint_sha256","generation_ms","input_tokens",
             "output_tokens","peak_allocated_bytes","gpu","quantization")})
        return result["answer"]

    def warm_up(self):
        self.identity()  # Loading belongs to the GPU service, never to the web worker.

    def is_available(self):
        try:
            self.identity()
            embeddings = OllamaClient(self.base_url, self.embedding_model, self.embedding_model)
            return embeddings.is_available()
        except ModelNotReady as exc:
            logger.warning("%s", exc)
            return False


def create_model_client(config):
    if config.CHAT_PROVIDER == "hf_lora":
        return HfLoraClient(config)
    return OllamaClient(config.ollama_base_url, config.chat_model, config.embedding_model,
                        max(1, config.ai_response_timeout_seconds - 9))
