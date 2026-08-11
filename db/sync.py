"""Synchronous PostgreSQL access for the crawler/matcher layers.

The crawler/matcher stack is synchronous (curl_cffi HTTP client, blocking
event loop in cli/monitor.py), so it cannot host the async SQLAlchemy engine
from db.base.py. This module provides a thin synchronous psycopg2 layer that
talks to the SAME PostgreSQL tables defined by db.models, so the FastAPI
(which reads Postgres) sees crawler/matcher writes directly — no bridge.

DB credentials are read from the same DB_* env vars / DB_URL as db.base.
"""

import os

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()  # ensure .env is applied regardless of caller


def pg_params() -> dict:
    """Connection parameters from environment (same defaults as db.base)."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "torob_intel"),
        "user": os.getenv("DB_USER", "torob"),
        "password": os.getenv("DB_PASSWORD", "torob"),
        "connect_timeout": 10,
    }


def connect():
    """Open a new psycopg2 connection with dict-row cursor support."""
    conn = psycopg2.connect(**pg_params())
    conn.set_session(autocommit=False)
    return conn


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def ensure_schema():
    """Create/verify all tables from db.models (idempotent)."""
    from sqlalchemy import create_engine
    from db.base import Base
    import db.models  # noqa: F401  (registers all models)

    p = pg_params()
    dsn = (f"postgresql+psycopg2://{p['user']}:{p['password']}"
           f"@{p['host']}:{p['port']}/{p['dbname']}")
    engine = create_engine(dsn)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()