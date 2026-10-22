"""Portable local startup without developer environment overrides."""
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.config import BACKEND_ROOT, Settings
from app.database import _configure_sqlite_engine
import run


class DemoStartupTests(unittest.TestCase):
    def test_frozen_snapshot_stays_read_only_and_byte_identical(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "frozen.db"
            with sqlite3.connect(database) as writer:
                writer.execute("CREATE TABLE probe (value INTEGER)")
                writer.execute("INSERT INTO probe VALUES (1)")
            writer.close()
            original = database.read_bytes()
            engine = create_engine(f"sqlite:///file:{database.as_posix()}?mode=ro&uri=true")
            _configure_sqlite_engine(engine)
            try:
                with engine.connect() as reader:
                    self.assertEqual(reader.exec_driver_sql("SELECT value FROM probe").scalar(), 1)
                    with self.assertRaises(OperationalError):
                        reader.exec_driver_sql("UPDATE probe SET value=2")
            finally:
                engine.dispose()
            self.assertEqual(database.read_bytes(), original)
            self.assertEqual(list(Path(temp_dir).iterdir()), [database])

    def test_sqlite_reader_does_not_block_another_request_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = create_engine(f"sqlite:///{Path(temp_dir).as_posix()}/demo.db")
            _configure_sqlite_engine(engine)
            try:
                with engine.begin() as writer:
                    writer.exec_driver_sql("CREATE TABLE probe (value INTEGER)")
                    writer.exec_driver_sql("INSERT INTO probe VALUES (1)")
                with engine.connect() as reader:
                    reader.exec_driver_sql("BEGIN")
                    self.assertEqual(reader.exec_driver_sql("SELECT value FROM probe").scalar(), 1)
                    with engine.begin() as writer:
                        writer.exec_driver_sql("UPDATE probe SET value=2")
                    # The old reader keeps its snapshot; new requests see the write.
                    self.assertEqual(reader.exec_driver_sql("SELECT value FROM probe").scalar(), 1)
                with engine.connect() as reader:
                    self.assertEqual(reader.exec_driver_sql("SELECT value FROM probe").scalar(), 2)
            finally:
                engine.dispose()

    def test_clean_environment_uses_checkout_database_and_model(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
        self.assertEqual(
            settings.DATABASE_URL,
            f"sqlite:///{(BACKEND_ROOT / 'techcare.db').as_posix()}",
        )
        self.assertEqual(settings.chat_model, "qwen2.5:7b-instruct-fp16")
        self.assertTrue(settings.AUTO_SEED)
        self.assertEqual(settings.ENVIRONMENT, "development")

    def test_launcher_uses_backend_directory_and_preserves_explicit_config(self):
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            explicit_url = f"sqlite:///{Path(temp_dir).as_posix()}/chosen.db"
            try:
                os.chdir(temp_dir)
                with patch.dict(os.environ, {"DATABASE_URL": explicit_url}):
                    with patch.object(run.uvicorn, "run") as serve:
                        run.main()
                    self.assertEqual(Path.cwd(), BACKEND_ROOT)
                    self.assertEqual(os.environ["DATABASE_URL"], explicit_url)
                    serve.assert_called_once_with(
                        "app.main:app", host="127.0.0.1", port=8000,
                    )
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
