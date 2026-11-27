"""Gateway: the web site (pages, login session) that talks to the back-end services.

The browser only ever talks to this service. It calls the auth, prediction and history
services over HTTP (see clients.py) and renders the pages.
"""
import logging
import os
import sys
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

import clients

# ---------- course / team info shown in the footer and About page ----------
COURSE = "Software Design, Dongshin University"
PROFESSOR = "Musa Ibrahim"
TEAM = [
    {"name": "Hasan MD Rakibul", "id": "2677526"},
    {"name": "Hosen Aiyub", "id": "2677530"},
    {"name": "Islam MD Din", "id": "2677519"},
]

# ---------- configuration (12-factor: everything comes from environment variables) ----------
APP_ENV = os.environ.get("APP_ENV", "development")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError("SECRET_KEY must be set when APP_ENV=production")
    SECRET_KEY = "dev-secret-change-me"

logging.basicConfig(
    stream=sys.stdout,
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s gateway: %(message)s",
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


def label(symptom: str) -> str:
    """'eye_pain_behind' -> 'Eye Pain Behind'"""
    return symptom.replace("_", " ").title()


app.jinja_env.globals["label"] = label
app.jinja_env.globals.update(COURSE=COURSE, PROFESSOR=PROFESSOR, TEAM=TEAM)


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
    try:
        n_diseases, n_symptoms = len(clients.diseases()), len(clients.symptoms())
    except clients.ServiceUnavailable:   # the home page still opens if prediction is down
        n_diseases = n_symptoms = "-"
    return render_template("index.html", n_diseases=n_diseases, n_symptoms=n_symptoms)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or "@" not in email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "error")
        else:
            status, _ = clients.register(name, email, password)
            if status == 201:
                flash("Account created. Please log in.", "ok")
                return redirect(url_for("login"))
            if status == 409:
                flash("That email is already registered.", "error")
            else:
                flash("Could not create the account. Please check your details.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        status, user = clients.login(email, password)
        if status == 200:
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
    symptoms = clients.symptoms()
    if request.method == "POST":
        chosen = [s for s in request.form.getlist("symptoms") if s in symptoms]
        if len(chosen) < 2:
            flash("Please select at least 2 symptoms.", "error")
        else:
            status, body = clients.predict(chosen)
            if status != 200:
                flash("Prediction failed. Please try again.", "error")
            else:
                pid = clients.save_prediction(session["user_id"], chosen, body["results"])
                return redirect(url_for("result", pid=pid))
    return render_template("predict.html", symptoms=symptoms)


@app.route("/result/<int:pid>")
@login_required
def result(pid):
    row = clients.prediction(pid)
    if not row or (row["user_id"] != session["user_id"] and not session.get("is_admin")):
        abort(404)
    top = row["results"][0][0]
    return render_template(
        "result.html",
        row=row,
        symptoms=row["symptoms"],
        results=row["results"],
        info=clients.disease(top),
        top=top,
        accuracy=clients.model_accuracy(),
    )


@app.route("/history")
@login_required
def history():
    rows = clients.history_of(session["user_id"])
    items = [
        {"id": r["id"], "created_at": r["created_at"], "symptoms": r["symptoms"], "top": r["results"][0]}
        for r in rows
    ]
    return render_template("history.html", items=items)


@app.route("/history/<int:pid>/delete", methods=["POST"])
@login_required
def delete_history(pid):
    clients.delete_prediction(pid, session["user_id"])
    flash("Record deleted.", "ok")
    return redirect(url_for("history"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/diseases")
def diseases():
    return render_template("diseases.html", diseases=clients.diseases())


@app.route("/admin")
@admin_required
def admin():
    users = clients.users()
    stats = clients.stats()
    for u in users:
        u["n"] = stats["per_user"].get(str(u["id"]), 0)
    ranked = stats["ranked"]
    biggest = ranked[0][1] if ranked else 1
    return render_template(
        "admin.html", users=users, total_pred=stats["total"], ranked=ranked, biggest=biggest,
        accuracy=clients.model_accuracy(),
    )


# ---------- health ----------
@app.route("/health")
def health():
    """Liveness: is the gateway itself running? (Docker and load balancers use this.)"""
    return {"status": "ok", "service": "gateway"}


@app.route("/ready")
def ready():
    """Readiness: can the gateway reach all three services?"""
    states = {name: clients.health(name) for name in ("auth", "prediction", "history")}
    ok = all(v == "ok" for v in states.values())
    return {"status": "ok" if ok else "degraded", "services": states}, 200 if ok else 503


# ---------- errors ----------
@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, msg="You do not have access to this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, msg="Page not found."), 404


@app.errorhandler(clients.ServiceUnavailable)
def service_down(e):
    app.logger.error("%s", e)
    return render_template(
        "error.html", code=503,
        msg=f"The {e.service} service is not available right now. Please try again in a moment."), 503


app.logger.info("Gateway started (env=%s)", APP_ENV)

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
