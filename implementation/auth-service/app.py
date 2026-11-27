"""Auth service: user accounts and login. Owns the `users` table (its own database).

REST API (JSON). Called only by the gateway, with the X-Internal-Key header.
    POST /register   {name, email, password}  -> 201 {id} | 400 | 409 (email taken)
    POST /login      {email, password}        -> 200 {id, name, is_admin} | 401
    GET  /users                               -> 200 {users: [...]}   (for the admin dashboard)
    GET  /health                              -> 200 {status, service, database}
"""
import logging
import os
import sys
from datetime import datetime

from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

import db as database

SERVICE = "auth-service"
INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")

logging.basicConfig(
    stream=sys.stdout,
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s " + SERVICE + ": %(message)s",
)

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""
SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS users(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

app = Flask(__name__)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_db():
    if "db" not in g:
        g.db = database.connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@app.before_request
def require_internal_key():
    """Only the gateway (which knows the shared key) may call this service."""
    if request.path == "/health" or not INTERNAL_KEY:
        return None
    if request.headers.get("X-Internal-Key") != INTERNAL_KEY:
        return jsonify(error="forbidden"), 403
    return None


def init_db():
    conn = database.connect()
    try:
        database.init_schema(conn, SCHEMA_SQLITE, SCHEMA_PG, lock_id=727201)
        if not conn.execute("SELECT 1 FROM users WHERE is_admin=1").fetchone():
            conn.execute(
                "INSERT INTO users(name,email,password_hash,is_admin,created_at) "
                "VALUES(?,?,?,1,?) ON CONFLICT(email) DO NOTHING",
                (
                    "Admin",
                    os.environ.get("ADMIN_EMAIL", "admin@example.com"),
                    generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123")),
                    now(),
                ),
            )
            conn.commit()
    finally:
        conn.close()


@app.post("/register")
def register():
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    if not name or "@" not in email or len(password) < 6:
        return jsonify(error="invalid input"), 400
    db = get_db()
    try:
        new_id = db.insert(
            "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
            (name, email, generate_password_hash(password), now()),
        )
        db.commit()
    except database.IntegrityError:
        db.rollback()
        return jsonify(error="email already registered"), 409
    return jsonify(id=new_id), 201


@app.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return jsonify(id=user["id"], name=user["name"], is_admin=bool(user["is_admin"]))
    return jsonify(error="wrong email or password"), 401


@app.get("/users")
def users():
    rows = get_db().execute(
        "SELECT id,name,email,is_admin,created_at FROM users ORDER BY id"
    ).fetchall()
    return jsonify(users=[
        {"id": r["id"], "name": r["name"], "email": r["email"],
         "is_admin": bool(r["is_admin"]), "created_at": r["created_at"]}
        for r in rows
    ])


@app.get("/health")
def health():
    try:
        database.ping()
    except Exception:  # noqa: BLE001 - any DB failure means "not ready"
        app.logger.exception("health check failed")
        return jsonify(status="unhealthy", service=SERVICE), 503
    return jsonify(status="ok", service=SERVICE, database="postgresql" if database.IS_PG else "sqlite")


init_db()
app.logger.info("Started (database=%s)", "postgresql" if database.IS_PG else "sqlite")

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5001")))
