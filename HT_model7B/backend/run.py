"""Start the local backend with the same defaults as Uvicorn in backend/."""
import os
from pathlib import Path

import uvicorn


def main():
    # Resolve .env and explicitly relative SQLite URLs from this checkout,
    # including when invoked as `python backend/run.py` from the project root.
    os.chdir(Path(__file__).resolve().parent)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
