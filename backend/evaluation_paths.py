"""Keep disposable test output outside the application checkout."""
import os
from pathlib import Path
import tempfile


def work_directory():
    default = Path(tempfile.gettempdir()) / "TechCare"
    path = Path(os.environ.get("CHATBOT_WORK_DIR", str(default))).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_directory():
    path = work_directory() / "evaluation_artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def temporary_directory():
    path = work_directory() / "test_tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path
