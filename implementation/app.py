import json
import logging
import os
import sys
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import db as database
import model
from data import COURSE, DISEASES, PROFESSOR, SYMPTOMS, TEAM, label

DB_PATH = database.SQLITE_PATH  # only used when DATABASE_URL is not set (local SQLite)

# ---------- configuration (12-factor: everything comes from environment variables) ----------
APP_ENV = os.environ.get("APP_ENV", "development")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError("SECRET_KEY must be set when APP_ENV=production")
    SECRET_KEY = "dev-secret-change-me"

# Logs go to stdout so the platform (Docker, Render, Kubernetes) can collect them.
logging.basicConfig(
    stream=sys.stdout,
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)
if os.environ.get("TRUST_PROXY", "0") == "1":  # behind a load balancer / reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.jinja_env.globals["label"] = label
app.jinja_env.globals.update(COURSE=COURSE, PROFESSOR=PROFESSOR, TEAM=TEAM)


# ---------- database ----------
def get_db():
    if "db" not in g:
        g.db = database.connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = database.connect()
    try:
        database.init_schema(conn)
        # Default admin account. Set ADMIN_EMAIL / ADMIN_PASSWORD in the cloud.
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


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------- auth helpers ----------
def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            flash("Please log in first.", "warn")
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if not session.get("is_admin"):
            abort(403)
        return f(*a, **kw)
    return wrapper


# ---------- pages ----------
@app.route("/")
def index():
    return render_template("index.html", n_diseases=len(DISEASES), n_symptoms=len(SYMPTOMS))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or "@" not in email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "error")
        else:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                    (name, email, generate_password_hash(password), now()),
                )
                db.commit()
                flash("Account created. Please log in.", "ok")
                return redirect(url_for("login"))
            except database.IntegrityError:
                db.rollback()
                flash("That email is already registered.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], is_admin=bool(user["is_admin"]))
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") else url_for("predict"))
        flash("Wrong email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "ok")
    return redirect(url_for("index"))


@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if request.method == "POST":
        chosen = [s for s in request.form.getlist("symptoms") if s in SYMPTOMS]
        if len(chosen) < 2:
            flash("Please select at least 2 symptoms.", "error")
        else:
            results = model.predict(chosen, top_n=3)
            db = get_db()
            pid = db.insert(
                "INSERT INTO predictions(user_id,symptoms,results,created_at) VALUES(?,?,?,?)",
                (session["user_id"], json.dumps(chosen), json.dumps(results), now()),
            )
            db.commit()
            return redirect(url_for("result", pid=pid))
    return render_template("predict.html", symptoms=SYMPTOMS)


def _load_prediction(pid):
    row = get_db().execute("SELECT * FROM predictions WHERE id=?", (pid,)).fetchone()
    if not row or (row["user_id"] != session["user_id"] and not session.get("is_admin")):
        abort(404)
    return row


@app.route("/result/<int:pid>")
@login_required
def result(pid):
    row = _load_prediction(pid)
    results = json.loads(row["results"])
    top = results[0][0]
    return render_template(
        "result.html",
        row=row,
        symptoms=json.loads(row["symptoms"]),
        results=results,
        info=DISEASES[top],
        top=top,
        accuracy=model.get_bundle()["accuracy"] * 100,
    )


@app.route("/history")
@login_required
def history():
    rows = get_db().execute(
        "SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    items = [
        {"id": r["id"], "created_at": r["created_at"],
         "symptoms": json.loads(r["symptoms"]), "top": json.loads(r["results"])[0]}
        for r in rows
    ]
    return render_template("history.html", items=items)


@app.route("/history/<int:pid>/delete", methods=["POST"])
@login_required
def delete_history(pid):
    db = get_db()
    db.execute("DELETE FROM predictions WHERE id=? AND user_id=?", (pid, session["user_id"]))
    db.commit()
    flash("Record deleted.", "ok")
    return redirect(url_for("history"))


@app.route("/health")
def health():
    """Liveness/readiness probe for Docker, load balancers and Kubernetes."""
    try:
        database.ping()
    except Exception:  # noqa: BLE001 - any DB failure means "not ready"
        app.logger.exception("health check failed")
        return {"status": "unhealthy"}, 503
    return {"status": "ok", "database": "postgresql" if database.IS_PG else "sqlite"}


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/diseases")
def diseases():
    return render_template("diseases.html", diseases=DISEASES)


@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    users = db.execute(
        """SELECT u.id,u.name,u.email,u.is_admin,u.created_at,
                  (SELECT COUNT(*) FROM predictions p WHERE p.user_id=u.id) AS n
           FROM users u ORDER BY u.id"""
    ).fetchall()
    total_pred = db.execute("SELECT COUNT(*) AS n FROM predictions").fetchone()["n"]
    counts = {}
    for r in db.execute("SELECT results FROM predictions"):
        d = json.loads(r["results"])[0][0]
        counts[d] = counts.get(d, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: -x[1])
    biggest = ranked[0][1] if ranked else 1
    return render_template(
        "admin.html", users=users, total_pred=total_pred, ranked=ranked, biggest=biggest,
        accuracy=model.get_bundle()["accuracy"] * 100,
    )


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, msg="You do not have access to this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, msg="Page not found."), 404


init_db()
model.get_bundle()  # train on first run so the first prediction is instant
app.logger.info("Started (env=%s, database=%s)", APP_ENV, "postgresql" if database.IS_PG else "sqlite")

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
