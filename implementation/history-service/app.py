"""History service: stores each prediction. Owns the `predictions` table (its own database).

It never touches user data. It only stores the user's id as a plain number, so it can
run, scale and fail on its own.

REST API (JSON). Called only by the gateway, with the X-Internal-Key header.
    POST   /predictions                {user_id, symptoms, results}  -> 201 {id}
    GET    /predictions?user_id=N                                     -> 200 {predictions: [...]} newest first
    GET    /predictions/<id>                                          -> 200 {...} | 404
    DELETE /predictions/<id>?user_id=N                                -> 200 {deleted: 0|1} (owner only)
    GET    /stats                                                     -> 200 {total, per_user, ranked}
    GET    /health
"""
import json
import logging
import os
import sys
from datetime import datetime

from flask import Flask, g, jsonify, request

import db as database

SERVICE = "history-service"
INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")

logging.basicConfig(
    stream=sys.stdout,
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s " + SERVICE + ": %(message)s",
)

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS predictions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symptoms TEXT NOT NULL,
    results TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS predictions(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symptoms TEXT NOT NULL,
    results TEXT NOT NULL,
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
    if request.path == "/health" or not INTERNAL_KEY:
        return None
    if request.headers.get("X-Internal-Key") != INTERNAL_KEY:
        return jsonify(error="forbidden"), 403
    return None


def init_db():
    conn = database.connect()
    try:
        database.init_schema(conn, SCHEMA_SQLITE, SCHEMA_PG, lock_id=727202)
    finally:
        conn.close()


def as_dict(r):
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "symptoms": json.loads(r["symptoms"]),
        "results": json.loads(r["results"]),
        "created_at": r["created_at"],
    }


@app.post("/predictions")
def create():
    body = request.get_json(silent=True) or {}
    user_id, symptoms, results = body.get("user_id"), body.get("symptoms"), body.get("results")
    if not isinstance(user_id, int) or not isinstance(symptoms, list) or not isinstance(results, list) or not results:
        return jsonify(error="invalid input"), 400
    db = get_db()
    new_id = db.insert(
        "INSERT INTO predictions(user_id,symptoms,results,created_at) VALUES(?,?,?,?)",
        (user_id, json.dumps(symptoms), json.dumps(results), now()),
    )
    db.commit()
    return jsonify(id=new_id), 201


@app.get("/predictions")
def list_for_user():
    try:
        user_id = int(request.args.get("user_id", ""))
    except ValueError:
        return jsonify(error="user_id is required"), 400
    rows = get_db().execute(
        "SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC", (user_id,)
    ).fetchall()
    return jsonify(predictions=[as_dict(r) for r in rows])


@app.get("/predictions/<int:pid>")
def get_one(pid):
    row = get_db().execute("SELECT * FROM predictions WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify(error="not found"), 404
    return jsonify(as_dict(row))


@app.delete("/predictions/<int:pid>")
def delete_one(pid):
    try:
        user_id = int(request.args.get("user_id", ""))
    except ValueError:
        return jsonify(error="user_id is required"), 400
    db = get_db()
    cur = db.execute("DELETE FROM predictions WHERE id=? AND user_id=?", (pid, user_id))
    deleted = cur.rowcount
    db.commit()
    return jsonify(deleted=deleted)


@app.get("/stats")
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM predictions").fetchone()["n"]
    per_user = {}
    for r in db.execute("SELECT user_id, COUNT(*) AS n FROM predictions GROUP BY user_id"):
        per_user[str(r["user_id"])] = r["n"]
    counts = {}
    for r in db.execute("SELECT results FROM predictions"):
        top = json.loads(r["results"])[0][0]
        counts[top] = counts.get(top, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: -x[1])
    return jsonify(total=total, per_user=per_user, ranked=ranked)


@app.get("/health")
def health():
    try:
        database.ping()
    except Exception:  # noqa: BLE001
        app.logger.exception("health check failed")
        return jsonify(status="unhealthy", service=SERVICE), 503
    return jsonify(status="ok", service=SERVICE, database="postgresql" if database.IS_PG else "sqlite")


init_db()
app.logger.info("Started (database=%s)", "postgresql" if database.IS_PG else "sqlite")

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5003")))
