"""Selection controls for original FP16 7B; algorithms stay in existing methods."""
import json
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.model_client import create_model_client, HfLoraClient
from benchmark.chapter5 import prepare
from benchmark.methods import build_method, method_settings, GENERATION
from benchmark.protocol import MAIN_METHODS, SUPPLEMENTARY_METHODS, method_spec
from benchmark.run import main as benchmark_main
from local_demo import create_demo_app

ROOT = Path(__file__).resolve().parents[1]


class OriginalSevenBTests(unittest.TestCase):
    def test_runner_defaults_to_four_main_methods_and_requires_explicit_ft(self):
        for selection, expected in (([], list(MAIN_METHODS)), (["--methods", "P+FT"], ["P+FT"])):
            with self.subTest(selection=selection):
                output = io.StringIO()
                with patch.object(sys, "argv", ["benchmark.run", "--validate-only", *selection]), redirect_stdout(output):
                    benchmark_main()
                result = json.loads(output.getvalue())
                self.assertEqual(result["status"], "valid")
                self.assertEqual(result["methods"], expected)
        self.assertEqual(MAIN_METHODS, ("B0", "B1", "B2", "P"))
        self.assertEqual(SUPPLEMENTARY_METHODS, ("P+FT",))

    def test_packaged_ft_adapter_matches_pinned_identity_and_metadata(self):
        profile = json.loads((ROOT / "model_serving/profiles/qwen25_7b.json").read_text(encoding="utf-8"))
        adapter = ROOT / profile["adapter_path"]
        self.assertEqual(hashlib.sha256((adapter / "adapter_model.safetensors").read_bytes()).hexdigest(), profile["adapter_sha256"])
        run = json.loads((adapter.parent / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["checkpoint"]["repo"], profile["base_repo"])
        self.assertEqual(run["checkpoint"]["revision"], profile["base_revision"])
        self.assertEqual(run["source"]["train_rows"], 37)
        self.assertEqual(run["source"]["validation_rows"], 9)
        self.assertEqual(run["training_metrics"]["epoch"], 1.0)
        self.assertEqual(run["release_export"]["original_run_sha256"], "07dca6e1a4e4d2bdbdf8c394fc12a38ae6b8c4f4f27098621ca20d8c0448e92a")
        self.assertFalse(run["release_export"]["adapter_weights_changed"])
        self.assertFalse(run["source"]["official_test_used_for_training"])
        self.assertEqual(method_spec("P")["components"], method_spec("P+FT")["components"])
        self.assertEqual(method_settings("P+FT", 60, ROOT / "rag_data", "unused", "unused").chat_model, "qwen2.5-7b-finetuned")

    def test_clean_website_selects_original_7b_without_adapter(self):
        with patch.dict(os.environ, {}, clear=True):
            config = Settings(_env_file=None)
        client = create_model_client(config)
        self.assertEqual(client.chat_model, "qwen2.5:7b-instruct-fp16")
        self.assertNotIsInstance(client, HfLoraClient)
        self.assertEqual(client.embedding_model, "nomic-embed-text")
        profile = json.loads((ROOT / "rag_data/model_profile.json").read_text(encoding="utf-8"))
        self.assertFalse(profile["fine_tuned_by_group"])
        manifest = json.loads((ROOT / "models/qwen2.5-7b/model_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["model"], client.chat_model)
        self.assertEqual(profile["quantization"], "F16")
        self.assertEqual(manifest["model"], client.chat_model)
        self.assertEqual(manifest["details"]["quantization_level"], "F16")
        self.assertFalse(manifest["group_fine_tuned"])

    def test_all_main_llm_methods_share_7b_but_b0_has_no_model(self):
        for method in ("B0", "B1", "B2", "P"):
            with self.subTest(method=method):
                config = method_settings(method, 60, ROOT / "rag_data", "http://127.0.0.1:11434", "unused")
                runner = build_method(method, config, "neutral fixture prompt")
                self.assertFalse(config.USE_PROJECT_CHAT_MODEL)
                if method == "B0":
                    self.assertIsNone(runner.client)
                else:
                    self.assertEqual(runner.client.chat_model, "qwen2.5:7b-instruct-fp16")
        self.assertEqual(GENERATION, {"temperature": 0, "num_predict": 384, "num_ctx": 4096, "repeat_penalty": 1.0})

    def test_new_study_records_7b_and_keeps_original_generation(self):
        package = ROOT / "benchmark/datasets/chapter5_24"
        with tempfile.TemporaryDirectory() as temp_dir:
            study = Path(temp_dir) / "study"
            prepare(package, study, package / "approval_record.json")
            protocol = json.loads((study / "protocol.json").read_text(encoding="utf-8"))
            self.assertEqual(protocol["chat_model"], "qwen2.5:7b-instruct-fp16")
            self.assertEqual(protocol["generation"], GENERATION)
            self.assertEqual(protocol["counts"]["cases"], 24)
            self.assertEqual((study / "package/test_inputs.jsonl").read_bytes(), (package / "test_inputs.jsonl").read_bytes())

    def test_demo_labels_come_from_actual_recorded_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context = {"output": temp_dir, "frontend_port": 5174, "instance_id": "unit",
                       "expected_identity": {"model": "qwen2.5:7b-instruct-fp16"},
                       "cases": {cid: {"input": {"case_id": cid}} for cid in ("TC01", "TC11", "TC18", "TC21")},
                       "timeout": 90, "study": temp_dir, "snapshot_timestamp": "unit"}
            with TestClient(create_demo_app(context), base_url="http://127.0.0.1:8012", client=("127.0.0.1", 49000)) as client:
                response = client.get("/api/demo/config")
            self.assertEqual(response.status_code, 200)
            methods = {item["id"]: item["model"] for item in response.json()["methods"]}
            self.assertEqual(methods, {"B0": None, "B1": "qwen2.5:7b-instruct-fp16", "B2": "qwen2.5:7b-instruct-fp16", "P": "qwen2.5:7b-instruct-fp16"})


if __name__ == "__main__":
    unittest.main()
