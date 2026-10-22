"""Boundary tests; actual method calls are verified separately over local HTTP."""
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from local_demo import REPOSITORY, create_demo_app, prepare_context, readonly_url


class LocalDemoBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="techcare-local-demo-")
        self.root = Path(self.temp.name)
        (self.root / "sessions").mkdir()
        self.context = {"output": str(self.root), "frontend_port": 5174}
        self.app = create_demo_app(self.context)
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8012", client=("127.0.0.1", 49000))

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_production_refused_before_reading_study(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with self.assertRaisesRegex(ValueError, "disabled"):
                prepare_context(self.root, self.root / "output", 8012, 5174)

    def test_output_in_repository_refused(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with self.assertRaisesRegex(ValueError, "outside"):
                prepare_context(self.root, REPOSITORY / ".local", 8012, 5174)

    def test_remote_client_cannot_create_demo_session(self):
        with TestClient(self.app, base_url="http://127.0.0.1:8012", client=("192.0.2.8", 49000)) as remote:
            self.assertEqual(remote.post("/api/demo/sessions").status_code, 403)
        self.assertEqual(list((self.root / "sessions").iterdir()), [])

    def test_foreign_host_and_origin_refused(self):
        self.assertEqual(self.client.post("/api/demo/sessions", headers={"Host": "example.com"}).status_code, 403)
        self.assertEqual(self.client.post("/api/demo/sessions", headers={"Origin": "https://example.com"}).status_code, 403)

    def test_customer_routes_are_absent(self):
        self.assertEqual(self.client.get("/api/chat/sessions").status_code, 404)
        self.assertEqual(self.client.post("/api/chat/messages", json={}).status_code, 404)

    def test_method_case_and_history_cannot_be_overridden(self):
        valid = {"session_id": str(uuid4()), "method": "P", "case_id": "TC21"}
        for invalid in ({**valid, "method": "P+FT"}, {**valid, "case_id": "TC02"},
                        {**valid, "history": [{"role": "user", "content": "override"}]},
                        {**valid, "question": "override"}):
            self.assertEqual(self.client.post("/api/demo/runs", json=invalid).status_code, 422)

    def test_new_sessions_are_separate_and_reopenable(self):
        one = self.client.post("/api/demo/sessions").json()
        two = self.client.post("/api/demo/sessions").json()
        self.assertNotEqual(one["session_id"], two["session_id"])
        self.assertEqual(self.client.get("/api/demo/sessions/" + one["session_id"]).json(), one)
        self.assertEqual(len(list((self.root / "sessions").iterdir())), 2)

    def test_database_url_enforces_read_only(self):
        database = self.root / "readonly-test.db"
        with sqlite3.connect(database) as db:
            db.execute("CREATE TABLE example (value INTEGER)")
            db.execute("INSERT INTO example VALUES (1)")
        db.close()
        engine = create_engine(readonly_url(database))
        try:
            with engine.connect() as conn:
                self.assertEqual(conn.execute(text("SELECT value FROM example")).scalar_one(), 1)
                with self.assertRaises(OperationalError):
                    conn.execute(text("UPDATE example SET value=2"))
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
