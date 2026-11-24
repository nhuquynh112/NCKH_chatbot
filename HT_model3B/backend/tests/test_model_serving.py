import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from app.config import Settings
from app.model_client import HfLoraClient, ModelNotReady, create_model_client
from app.rag.embedding import OllamaClient
from model_serving.server import verify_artifacts, sha256, AdapterRuntime


class ModelSelectionTests(unittest.TestCase):
    def test_base_can_bypass_project_profile(self):
        config = Settings(_env_file=None, CHAT_PROVIDER="ollama", USE_PROJECT_CHAT_MODEL=False)
        self.assertEqual(create_model_client(config).chat_model, "qwen2.5:3b")

    def test_7b_does_not_use_3b_profile(self):
        config = Settings(_env_file=None, CHAT_PROVIDER="hf_lora")
        client = create_model_client(config)
        self.assertIsInstance(client, HfLoraClient)
        self.assertEqual(client.chat_model, "qwen2.5-7b-finetuned")
        self.assertEqual(client.embedding_model, "nomic-embed-text")

    def test_missing_server_never_calls_ollama_chat(self):
        client = create_model_client(Settings(_env_file=None, CHAT_PROVIDER="hf_lora", HF_LORA_BASE_URL="http://127.0.0.1:1"))
        with patch.object(OllamaClient, "_chat", side_effect=AssertionError("wrong model")):
            with self.assertRaises(ModelNotReady):
                client.chat("system", "question")

    def test_model_identity_is_checked_on_generation(self):
        client = create_model_client(Settings(_env_file=None, CHAT_PROVIDER="hf_lora"))
        state = {"status": "ready", "adapter_loaded": True, "model": "qwen2.5:3b",
                 "answer": "incorrect provider", **{k:client.profile[k] for k in ("checkpoint_sha256", "adapter_sha256")}}
        with patch.object(client, "_server_request", return_value=state):
            with self.assertRaisesRegex(ModelNotReady, "identity"):
                client.chat("system", "question")
        state["model"] = client.chat_model
        with patch.object(client, "_server_request", return_value=state):
            self.assertEqual(client.chat("system", "question"), "incorrect provider")

    def test_http_unready_error_is_diagnosable(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                # Consume the request before closing the HTTP/1.0 connection;
                # unread body bytes can reset it on Windows before 503 is read.
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                data = json.dumps({"error":"adapter failed to load"}).encode()
                self.send_response(503)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = create_model_client(Settings(_env_file=None, CHAT_PROVIDER="hf_lora",
                         HF_LORA_BASE_URL=f"http://127.0.0.1:{server.server_port}"))
            with self.assertRaisesRegex(ModelNotReady, "adapter failed to load"):
                client.chat("system", "question")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_unloaded_runtime_cannot_return_a_generation(self):
        with self.assertRaisesRegex(RuntimeError, "loading"):
            AdapterRuntime({"model":"qwen2.5-7b-finetuned"}).generate({})

    def test_request_timeout_is_diagnosable_without_model_fallback(self):
        client = create_model_client(Settings(_env_file=None, CHAT_PROVIDER="hf_lora"))
        with patch("urllib.request.urlopen",side_effect=TimeoutError("unit test timeout")), \
             patch.object(OllamaClient,"_chat",side_effect=AssertionError("fallback")):
            with self.assertRaisesRegex(ModelNotReady,"timed out"):
                client.chat("system","question")


class ArtifactIntegrityTests(unittest.TestCase):
    def test_tampered_adapter_is_rejected(self):
        # Synthetic files test integrity handling only; never used as model evidence.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, adapter = root / "base", root / "run/adapter"
            base.mkdir(); adapter.mkdir(parents=True)
            (base / "model.safetensors").write_bytes(b"unit-test-base")
            (adapter / "adapter_model.safetensors").write_bytes(b"unit-test-adapter")
            (adapter / "adapter_config.json").write_text(json.dumps({"r":8,"target_modules":["q_proj","v_proj"]}))
            (adapter.parent / "run.json").write_text(json.dumps({"status":"completed","checkpoint":{"repo":"test","revision":"revision"}}))
            base_hash = sha256(base / "model.safetensors")
            (base / "checkpoint_manifest.json").write_text(json.dumps({"repo":"test","revision":"revision", "files":[
                {"name":"model.safetensors","bytes":14,"local_sha256":base_hash}]}))
            profile = {"model":"test", "base_repo":"test","base_revision":"revision",
                       "checkpoint_path":str(base),"adapter_path":str(adapter),
                       "checkpoint_sha256":base_hash,"adapter_sha256":sha256(adapter / "adapter_model.safetensors")}
            self.assertEqual(verify_artifacts(profile)["model"], "test")
            (adapter / "adapter_model.safetensors").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Adapter weights"):
                verify_artifacts(profile)


if __name__ == "__main__":
    unittest.main()
