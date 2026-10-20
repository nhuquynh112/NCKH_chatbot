from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)


def _enable_sqlite_wal(connection, _record):
    # Chat requests read products/history while other requests create sessions.
    # WAL lets those readers coexist with a committed write in the local demo.
    # No schema/data migration; PostgreSQL does not use this hook.
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


def _configure_sqlite_engine(database_engine):
    query = database_engine.url.query
    # The research UI opens frozen snapshots with mode=ro. Never change their
    # journal or create sidecars; those connections must remain read-only.
    if (database_engine.dialect.name == "sqlite"
            and query.get("mode") != "ro"
            and str(query.get("immutable", "0")).lower() not in {"1", "true"}):
        event.listen(database_engine, "connect", _enable_sqlite_wal)


_configure_sqlite_engine(engine)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
