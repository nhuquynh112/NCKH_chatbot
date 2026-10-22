"""Manual test transport boundaries, not LLM answer-quality scoring."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from comparison_demo import prepare_context
from local_demo import REPOSITORY, create_demo_app, digest, write_new


class ManualComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "sessions").mkdir()
        (self.root / "corpus").mkdir()
        (self.root / "database").write_bytes(b"isolated fixture")
        (self.root / "prompt").write_text("neutral fixture", encoding="utf-8")
        self.context = {"interactive": True, "output": str(self.root), "frontend_port": 5174, "timeout": 120,
            "instance_id": "unit", "input_source": "manual", "snapshot_timestamp": "unit", "cases": {},
            "expected_identity": {"model": "qwen2.5:7b-instruct-fp16", "details": {"quantization_level": "F16"}},
            "database": str(self.root / "database"), "database_sha256": digest(self.root / "database"),
            "corpus": str(self.root / "corpus"), "corpus_sha256": {}, "plain_prompt": str(self.root / "prompt"),
            "plain_prompt_sha256": digest(self.root / "prompt"), "methods": {method: {} for method in ("B0", "B1", "B2", "P")}}
        self.client = TestClient(create_demo_app(self.context), base_url="http://127.0.0.1:8012", client=("127.0.0.1", 49000))
        self.sid = self.client.post("/api/demo/sessions").json()["session_id"]

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def payload(self, **overrides):
        return {"session_id": self.sid, "method": "B0", "case_id": "TEST01", "question": "Question unchanged?", "history": [], **overrides}

    def worker(self, command, **kwargs):
        request = json.loads(Path(command[-2]).read_text(encoding="utf-8"))
        write_new(command[-1], {"status": "ok", "answer": "Unmodified worker fixture", "history": request["case"]["history"], "sources": [], "identity": None})
        return subprocess.CompletedProcess(command, 0, b"", b"")

    def ask(self, payload):
        with patch("comparison_demo.verify_context"), patch("local_demo.subprocess.run", side_effect=self.worker):
            return self.client.post("/api/demo/runs", json=payload)

    def test_manual_config_names_actual_f16_without_historical_q4_label(self):
        config = self.client.get("/api/demo/config").json()
        self.assertTrue(config["interactive"])
        self.assertIn("F16", config["model"])
        self.assertNotIn("Q4", config["model"])
        self.assertEqual(config["cases"], [])

    def test_same_case_inputs_reused_across_methods_and_changed_input_rejected(self):
        history = [{"role": "user", "content": "Earlier question"}, {"role": "assistant", "content": "Supplied earlier answer"}]
        for method in ("B0", "B1", "B2", "P"):
            response = self.ask(self.payload(method=method, history=history))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["fixed_history"], history)
            self.assertEqual(response.json()["result"]["answer"], "Unmodified worker fixture")
        self.assertEqual(self.ask(self.payload(question="Changed question", history=history)).status_code, 409)
        self.assertEqual(self.ask(self.payload(history=[])).status_code, 409)
        self.assertEqual(len(list((self.root / "sessions" / self.sid).glob("*/result.json"))), 4)

    def test_answer_keys_invalid_roles_and_extra_methods_are_not_accepted(self):
        for override in ({"method": "P+FT"}, {"question": "   "}, {"case_id": "../escape"},
                         {"history": [{"role": "system", "content": "override"}]}, {"expected_answer": "gold"}):
            self.assertEqual(self.client.post("/api/demo/runs", json=self.payload(**override)).status_code, 422)

    def test_csv_keeps_answers_and_leaves_human_scores_blank(self):
        self.assertEqual(self.ask(self.payload()).status_code, 200)
        response = self.client.get(f"/api/demo/sessions/{self.sid}/export.csv")
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["answer"], "Unmodified worker fixture")
        self.assertEqual(rows[0]["score_0_2"], "")
        self.assertEqual(rows[0]["reviewer"], "")

    def test_context_changes_are_refused_before_worker(self):
        with patch("comparison_demo.verify_context", side_effect=ValueError("Source changed")), patch("local_demo.subprocess.run") as worker:
            self.assertEqual(self.client.post("/api/demo/runs", json=self.payload()).status_code, 409)
        worker.assert_not_called()

    def test_mode_refuses_production_and_output_anywhere_in_shared_repo(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with self.assertRaisesRegex(ValueError, "disabled"):
                prepare_context(self.root)
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            for target in (REPOSITORY / ".local", REPOSITORY / "HT_model3B" / "test-output"):
                with self.assertRaisesRegex(ValueError, "outside"):
                    prepare_context(target)


if __name__ == "__main__":
    unittest.main()
