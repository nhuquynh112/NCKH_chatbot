"""Anonymous UI/API boundaries and dispatch; worker outputs here are test fixtures."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from comparison_demo import prepare_context
from local_demo import METHODS, PIPELINES, create_demo_app, digest, write_new


class BlindReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "sessions").mkdir()
        (self.root / "corpus").mkdir()
        (self.root / "database").write_bytes(b"isolated fixture")
        (self.root / "prompt").write_text("neutral fixture", encoding="utf-8")
        self.context = {"interactive": True, "blinded": True, "output": str(self.root), "frontend_port": 5174,
                        "timeout": 120, "instance_id": "blind-unit", "cases": {}, "snapshot_timestamp": "unit",
                        "expected_identity": {"model": "private-model", "details": {"quantization_level": "F16"}},
                        "database": str(self.root / "database"), "database_sha256": digest(self.root / "database"),
                        "corpus": str(self.root / "corpus"), "corpus_sha256": {},
                        "plain_prompt": str(self.root / "prompt"), "plain_prompt_sha256": digest(self.root / "prompt"),
                        "methods": {method: {"method": method} for method in METHODS}}
        self.client = TestClient(create_demo_app(self.context), base_url="http://127.0.0.1:8012", client=("127.0.0.1", 49000))
        self.session = self.client.post("/api/demo/sessions", json={}).json()
        self.sid = self.session["session_id"]
        self.systems = json.loads((self.root / "sessions" / self.sid / "mapping_RIENG.json").read_text(encoding="utf-8"))
        self.dispatched = []
        self.answer = "Phản hồi kiểm thử nguyên văn.\nKhông sửa nội dung."

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def payload(self, **overrides):
        return {"session_id": self.sid, "system_id": self.systems[0]["system_id"], "case_id": "S01",
                "question": "Câu hỏi kiểm thử", "history": [], **overrides}

    def worker(self, command, **kwargs):
        request = json.loads(Path(command[-2]).read_text(encoding="utf-8"))
        self.dispatched.append(request)
        write_new(command[-1], {"status": "ok", "answer": self.answer, "history": request["case"]["history"],
                               "pipeline_class": PIPELINES[request["method"]], "mode": "private-routing",
                               "identity": {"model": "private-model"}, "llm_called": True,
                               "latency_ms": 123, "sources": [{"title": "private source metadata"}]})
        return subprocess.CompletedProcess(command, 0, b"", b"")

    def ask(self, **overrides):
        with patch("comparison_demo.verify_context"), patch("local_demo.subprocess.run", side_effect=self.worker):
            return self.client.post("/api/demo/blind/runs", json=self.payload(**overrides))

    def test_mapping_is_private_bijective_and_stable_per_session(self):
        self.assertEqual({row["method"] for row in self.systems}, set(METHODS))
        self.assertEqual(len({row["system_id"] for row in self.systems}), 4)
        self.assertEqual(self.session["systems"], [{"system_id": row["system_id"], "label": row["label"]} for row in self.systems])
        self.assertEqual(self.client.get(f"/api/demo/sessions/{self.sid}").json()["systems"], self.session["systems"])
        other = self.client.post("/api/demo/sessions", json={}).json()
        self.assertTrue({row["system_id"] for row in other["systems"]}.isdisjoint({row["system_id"] for row in self.systems}))
        for row in self.session["systems"]:
            self.assertEqual(set(row), {"system_id", "label"})

    def test_config_docs_and_legacy_run_route_do_not_disclose_methods(self):
        config = self.client.get("/api/demo/config").json()
        self.assertTrue(config["blinded"])
        self.assertTrue({"methods", "model", "embedding", "output", "generation"}.isdisjoint(config))
        for route in ("/docs", "/redoc", "/openapi.json", f"/api/demo/sessions/{self.sid}/mapping_RIENG.json"):
            self.assertEqual(self.client.get(route).status_code, 404)
        self.assertEqual(self.client.post("/api/demo/runs", json={"method": "B0"}).status_code, 404)

    def test_all_anonymous_choices_dispatch_original_method_and_exact_input(self):
        history = [{"role": "user", "content": "Lượt trước"}, {"role": "assistant", "content": "Phản hồi trước nguyên văn"}]
        for row in self.systems:
            response = self.ask(system_id=row["system_id"], history=history)
            self.assertEqual(response.status_code, 200)
            record = response.json()
            self.assertEqual(record["system_id"], row["system_id"])
            self.assertEqual(record["result"], {"status": "ok", "answer": self.answer})
            self.assertEqual(record["fixed_history"], history)
            self.assertEqual(set(record), {"run_id", "session_id", "case_id", "question", "fixed_history", "created_at", "system_id", "system_label", "result"})
            original = self.dispatched[-1]
            self.assertEqual(original["method"], row["method"])
            self.assertEqual(original["case"]["question"], self.payload()["question"])
            self.assertEqual(original["case"]["history"], history)
            self.assertEqual(original["database"], self.context["database"])
            self.assertEqual(original["corpus"], self.context["corpus"])
            self.assertEqual(original["plain_prompt"], "neutral fixture")
            saved = json.loads((self.root / "sessions" / self.sid / record["run_id"] / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["method"], row["method"])
            self.assertEqual(saved["result"]["answer"], self.answer)
            self.assertEqual(saved["result"]["pipeline_class"], PIPELINES[row["method"]])

    def test_record_session_and_csv_exports_only_have_anonymous_metadata(self):
        record = self.ask().json()
        self.assertEqual(self.client.get(f"/api/demo/sessions/{self.sid}/runs/{record['run_id']}").json(), record)
        self.assertEqual(self.client.get(f"/api/demo/sessions/{self.sid}").json()["runs"], [record])
        data = self.client.get(f"/api/demo/sessions/{self.sid}/export.csv")
        rows = list(csv.DictReader(io.StringIO(data.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["answer"], self.answer)
        self.assertEqual(rows[0]["system_id"], self.systems[0]["system_id"])
        self.assertEqual(rows[0]["score_0_2"], "")
        self.assertTrue({"method", "model", "mode", "llm_called", "latency_ms", "pipeline_class", "digest", "sources"}.isdisjoint(rows[0]))
        self.assertNotIn("private-model", data.text)

    def test_explicit_methods_extra_fields_and_cross_session_aliases_are_refused(self):
        for body in (self.payload(system_id="B0"), {**self.payload(), "method": "B0"},
                     {**self.payload(), "expected_answer": "never send an answer key"},
                     self.payload(history=[{"role": "system", "content": "override"}])):
            self.assertEqual(self.client.post("/api/demo/blind/runs", json=body).status_code, 422)
        self.assertEqual(self.ask(system_id=str(uuid4())).status_code, 404)
        self.assertEqual(self.dispatched, [])

    def test_generated_history_is_separate_per_system_and_immutable_within_it(self):
        first = [{"role": "assistant", "content": "Lịch sử thật của trợ lý đầu"}]
        second = [{"role": "assistant", "content": "Lịch sử thật của trợ lý sau"}]
        self.assertEqual(self.ask(history=first).status_code, 200)
        self.assertEqual(self.ask(system_id=self.systems[1]["system_id"], history=second).status_code, 200)
        self.assertEqual(self.ask(history=second).status_code, 409)
        self.assertEqual(self.ask(system_id=self.systems[1]["system_id"], question="Thay đổi câu đã khóa", history=second).status_code, 409)
        self.assertEqual(len(self.dispatched), 2)

    def test_errors_and_baseline_fallback_do_not_leak_routing_metadata(self):
        from blind_review import public_record
        record = self.ask().json()
        raw = json.loads((self.root / "sessions" / self.sid / record["run_id"] / "result.json").read_text(encoding="utf-8"))
        for status in ("timeout", "error", "not_ready", "no_rule_match"):
            raw["result"].update(status=status, error={"message": "private-model RuleMethod B0"})
            safe = public_record(raw, self.systems)
            self.assertEqual(safe["result"]["answer"], self.answer)
            self.assertEqual(set(safe["result"]), {"status", "answer"})
            self.assertEqual(safe["result"]["status"], "ok" if status == "no_rule_match" else status)
            self.assertEqual(raw["result"]["status"], status)

    def test_saved_review_mode_cannot_silently_switch(self):
        write_new(self.root / "demo_config.json", self.context)
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            with self.assertRaisesRegex(ValueError, "different review mode"):
                prepare_context(self.root, resume=self.root, blinded=False)


if __name__ == "__main__":
    unittest.main()
