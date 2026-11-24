"""Explicit local catalog update; backup SQLite first, never delete history."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.catalog_data import read_catalog, synchronize_catalog
from app.config import settings
from app.database import SessionLocal, engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=settings.products_path)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--replace-active", action="store_true",
                        help="Hide older products missing from this catalog; keep their rows")
    args = parser.parse_args()
    if settings.ENVIRONMENT not in {"development", "test"} or engine.dialect.name != "sqlite":
        raise ValueError("This migration supports local development/test SQLite only")
    rows = read_catalog(args.catalog.resolve())
    database = Path(engine.url.database).resolve()
    if not database.is_file():
        raise ValueError("Run seed.py first to create a new database")
    args.backup_dir.mkdir(parents=True, exist_ok=True)
    backup = args.backup_dir.resolve() / ("before-catalog-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8] + ".db")
    source = sqlite3.connect("file:" + database.as_posix() + "?mode=ro", uri=True)
    destination = sqlite3.connect(backup)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    with SessionLocal() as db:
        result = synchronize_catalog(db, rows, replace_active=args.replace_active)
        db.commit()
    print(json.dumps({**result, "backup": str(backup), "database": str(database)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
