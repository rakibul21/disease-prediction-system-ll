"""Database layer for one service: PostgreSQL in the cloud, SQLite for a quick local run.

Each service owns its own database. Set DATABASE_URL (for example
postgresql://user:pass@host:5432/dbname) to use PostgreSQL. If it is not set, a local
SQLite file is used (DATABASE_PATH, default history.db next to this file).
"""
import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
SQLITE_PATH = os.environ.get(
    "DATABASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")
)

if IS_PG:
    import psycopg2
    import psycopg2.extras

    IntegrityError = psycopg2.IntegrityError
else:
    IntegrityError = sqlite3.IntegrityError


class Conn:
    """Small wrapper so the same SQL (with ? placeholders) works on both databases."""

    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, args=()):
        if IS_PG:
            cur = self.raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql.replace("?", "%s"), args)
            return cur
        return self.raw.execute(sql, args)

    def insert(self, sql, args=()):
        """Run an INSERT and return the new row id."""
        if IS_PG:
            return self.execute(sql + " RETURNING id", args).fetchone()["id"]
        return self.execute(sql, args).lastrowid

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def connect():
    if IS_PG:
        return Conn(psycopg2.connect(DATABASE_URL))
    raw = sqlite3.connect(SQLITE_PATH)
    raw.row_factory = sqlite3.Row
    return Conn(raw)


def init_schema(conn, schema_sqlite, schema_pg, lock_id):
    """Create tables if missing. Safe to run from several workers at once."""
    if IS_PG:
        cur = conn.raw.cursor()
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (lock_id,))  # one worker creates the tables
        cur.execute(schema_pg)
    else:
        conn.raw.executescript(schema_sqlite)
    conn.commit()


def ping():
    """Used by the /health endpoint."""
    conn = connect()
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()
