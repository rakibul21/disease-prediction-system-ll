"""Quick end-to-end check of a running system (local, Docker or cloud).

    python scripts/smoke_test.py                       # checks http://localhost:5000
    python scripts/smoke_test.py https://my-site.example

It waits for all services to be ready, then registers a user, logs in, makes a
prediction, reads the history and opens the admin dashboard.
Set ADMIN_EMAIL / ADMIN_PASSWORD if you changed the default admin account.
"""
import os
import sys
import time
import urllib.request
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests"))
from harness import Client  # noqa: E402

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")


def check(ok, what):
    print(("PASS  " if ok else "FAIL  ") + what)
    if not ok:
        sys.exit(1)


def wait_ready(timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(BASE + "/ready", timeout=3) as r:
                if r.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(2)
    return False


check(wait_ready(), "gateway /ready: all services are up")
c = Client(BASE)
email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
check(c.post("/register", data={"name": "Smoke Test", "email": email, "password": "secret1"}).status_code == 302, "register")
check(c.post("/login", data={"email": email, "password": "secret1"}).status_code == 302, "login")
r = c.post("/predict", data={"symptoms": ["high_fever", "severe_headache", "eye_pain_behind", "joint_pain", "skin_rash"]},
           follow_redirects=True)
check(b"Most likely: Dengue" in r.data, "prediction (Dengue)")
check(b"Dengue" in c.get("/history").data, "history shows the prediction")
admin = Client(BASE)
admin.post("/login", data={"email": os.environ.get("ADMIN_EMAIL", "admin@example.com"),
                           "password": os.environ.get("ADMIN_PASSWORD", "admin123")})
check(email.encode() in admin.get("/admin").data, "admin dashboard lists the new user")
print("\nAll checks passed.")
