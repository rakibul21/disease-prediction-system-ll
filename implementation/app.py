import json
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import model
from data import DISEASES, SYMPTOMS, label

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.jinja_env.globals["label"] = label


# ---------- database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS predictions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symptoms TEXT NOT NULL,
            results TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    # Default admin account (change the password after first login!)
    if not db.execute("SELECT 1 FROM users WHERE is_admin=1").fetchone():
        db.execute(
            "INSERT INTO users(name,email,password_hash,is_admin,created_at) VALUES(?,?,?,1,?)",
            ("Admin", "admin@example.com", generate_password_hash("admin123"), now()),
        )
    db.commit()
    db.close()


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
            except sqlite3.IntegrityError:
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
            cur = db.execute(
                "INSERT INTO predictions(user_id,symptoms,results,created_at) VALUES(?,?,?,?)",
                (session["user_id"], json.dumps(chosen), json.dumps(results), now()),
            )
            db.commit()
            return redirect(url_for("result", pid=cur.lastrowid))
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
    total_pred = db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
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

if __name__ == "__main__":
    app.run(debug=True)
