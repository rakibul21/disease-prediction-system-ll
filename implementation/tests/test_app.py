"""Automated tests. Each test is named after a test case (TC-xx) in the RTM.

Run from the project folder:   python -m unittest discover -s tests -v
"""
import os
import re
import sqlite3
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = os.path.join(_tmp, "test.db")

import app as A  # noqa: E402
import model  # noqa: E402
from data import DISEASES, SYMPTOMS  # noqa: E402

DENGUE = ["high_fever", "severe_headache", "eye_pain_behind", "joint_pain", "skin_rash"]
DIABETES = ["frequent_urination", "excessive_thirst", "blurred_vision"]


def client():
    return A.app.test_client()


def register(c, name="Test User", email="user@test.com", pw="secret1"):
    return c.post("/register", data={"name": name, "email": email, "password": pw})


def login(c, email="user@test.com", pw="secret1"):
    return c.post("/login", data={"email": email, "password": pw})


def db_rows(sql, args=()):
    con = sqlite3.connect(A.DB_PATH)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


class Tests(unittest.TestCase):
    def setUp(self):
        con = sqlite3.connect(A.DB_PATH)
        con.execute("DELETE FROM predictions")
        con.execute("DELETE FROM users WHERE is_admin=0")
        con.commit()
        con.close()

    # ---- accounts ----
    def test_tc01_register_and_duplicate_email(self):
        c = client()
        self.assertEqual(register(c).status_code, 302)
        r = register(c)
        self.assertIn(b"already registered", r.data)
        r = register(c, email="bad", pw="x")
        self.assertIn(b"valid email", r.data)

    def test_tc02_password_is_hashed(self):
        register(client())
        h = db_rows("SELECT password_hash FROM users WHERE email='user@test.com'")[0][0]
        self.assertNotIn("secret1", h)
        self.assertGreater(len(h), 30)

    def test_tc03_login_success_and_failure(self):
        c = client()
        register(c)
        self.assertIn(b"Wrong email or password", login(c, pw="nope").data)
        self.assertEqual(login(c).status_code, 302)
        self.assertEqual(c.get("/predict").status_code, 200)

    def test_tc04_logout_clears_session(self):
        c = client()
        register(c)
        login(c)
        c.get("/logout")
        self.assertEqual(c.get("/predict").status_code, 302)

    def test_tc05_protected_pages_need_login(self):
        c = client()
        for url in ("/predict", "/history", "/result/1", "/admin"):
            r = c.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login", r.headers["Location"])

    # ---- prediction ----
    def test_tc06_symptom_list_and_search_box(self):
        c = client()
        register(c)
        login(c)
        html = c.get("/predict").data.decode()
        self.assertEqual(html.count('type="checkbox"'), len(SYMPTOMS))
        self.assertIn('id="q"', html)

    def test_tc07_at_least_two_symptoms(self):
        c = client()
        register(c)
        login(c)
        r = c.post("/predict", data={"symptoms": ["fever"]}, follow_redirects=True)
        self.assertIn(b"at least 2", r.data)
        self.assertEqual(db_rows("SELECT COUNT(*) FROM predictions")[0][0], 0)

    def test_tc08_top3_scores_and_known_cases(self):
        res = model.predict(DENGUE)
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0][0], "Dengue")
        self.assertEqual(model.predict(DIABETES)[0][0], "Type 2 Diabetes")
        self.assertEqual(model.predict(["runny_nose", "sneezing", "sore_throat"])[0][0], "Common Cold")
        for _, pct in res + model.predict(DIABETES):
            self.assertLessEqual(pct, 95.0)
            self.assertGreaterEqual(pct, 0.0)

    def test_tc09_result_page_content(self):
        c = client()
        register(c)
        login(c)
        r = c.post("/predict", data={"symptoms": DENGUE}, follow_redirects=True)
        html = r.data.decode()
        self.assertIn("Most likely: Dengue", html)
        self.assertIn(DISEASES["Dengue"]["description"], html)
        self.assertIn("Precautions", html)
        self.assertIn(DISEASES["Dengue"]["specialist"], html)
        self.assertIn("not a medical diagnosis", html)

    def test_tc10_prediction_saved(self):
        c = client()
        register(c)
        login(c)
        c.post("/predict", data={"symptoms": DIABETES})
        rows = db_rows("SELECT user_id, symptoms, results, created_at FROM predictions")
        self.assertEqual(len(rows), 1)
        self.assertTrue(all(rows[0]))

    # ---- history, privacy ----
    def test_tc11_history_order_and_delete(self):
        c = client()
        register(c)
        login(c)
        c.post("/predict", data={"symptoms": DENGUE})
        c.post("/predict", data={"symptoms": DIABETES})
        html = c.get("/history").data.decode()
        self.assertLess(html.index("Type 2 Diabetes"), html.index("Dengue"))  # newest first
        pid = db_rows("SELECT id FROM predictions ORDER BY id")[0][0]
        c.post(f"/history/{pid}/delete")
        self.assertEqual(db_rows("SELECT COUNT(*) FROM predictions")[0][0], 1)

    def test_tc12_only_owner_or_admin_can_open_result(self):
        a, b, adm = client(), client(), client()
        register(a, email="a@test.com")
        login(a, email="a@test.com")
        a.post("/predict", data={"symptoms": DENGUE})
        pid = db_rows("SELECT id FROM predictions")[0][0]
        register(b, email="b@test.com")
        login(b, email="b@test.com")
        self.assertEqual(b.get(f"/result/{pid}").status_code, 404)
        b.post(f"/history/{pid}/delete")  # must not delete someone else's record
        self.assertEqual(db_rows("SELECT COUNT(*) FROM predictions")[0][0], 1)
        login(adm, email="admin@example.com", pw="admin123")
        self.assertEqual(adm.get(f"/result/{pid}").status_code, 200)

    def test_tc13_print_button(self):
        c = client()
        register(c)
        login(c)
        r = c.post("/predict", data={"symptoms": DENGUE}, follow_redirects=True)
        self.assertIn(b"window.print()", r.data)

    def test_tc14_disease_library_is_public(self):
        r = client().get("/diseases")
        self.assertEqual(r.status_code, 200)
        html = r.data.decode()
        for name in DISEASES:
            self.assertIn(name.replace("&", "&amp;").replace("(", "(") , html.replace("&#39;", "'"))

    # ---- admin ----
    def test_tc15_admin_dashboard_and_access(self):
        u, adm = client(), client()
        register(u)
        login(u)
        u.post("/predict", data={"symptoms": DENGUE})
        self.assertEqual(u.get("/admin").status_code, 403)
        login(adm, email="admin@example.com", pw="admin123")
        r = adm.get("/admin")
        self.assertEqual(r.status_code, 200)
        for text in (b"Admin dashboard", b"Predictions", b"Most predicted diseases", b"Model accuracy", b"user@test.com"):
            self.assertIn(text, r.data)

    def test_tc16_default_admin_exists(self):
        rows = db_rows("SELECT email FROM users WHERE is_admin=1")
        self.assertEqual(rows, [("admin@example.com",)])

    def test_tc17_error_pages(self):
        c = client()
        self.assertEqual(c.get("/no-such-page").status_code, 404)
        self.assertIn(b"Page not found", c.get("/no-such-page").data)
        register(c)
        login(c)
        r = c.get("/admin")
        self.assertEqual(r.status_code, 403)
        self.assertIn(b"do not have access", r.data)

    # ---- non-functional ----
    def test_tc18_nfr_usability_responsive(self):
        css = open(os.path.join(ROOT, "static", "style.css"), encoding="utf-8").read()
        base = open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8").read()
        self.assertIn("@media", css)
        self.assertIn('name="viewport"', base)

    def test_tc19_nfr_performance(self):
        t = time.time()
        model.train()
        self.assertLess(time.time() - t, 5.0)
        t = time.time()
        model.predict(DENGUE)
        self.assertLess(time.time() - t, 1.0)

    def test_tc20_nfr_security_sql_injection_and_roles(self):
        c = client()
        register(c)
        r = c.post("/login", data={"email": "' OR 1=1 --", "password": "x"})
        self.assertIn(b"Wrong email or password", r.data)
        self.assertEqual(c.get("/admin").status_code, 302)  # visitor, not admin

    def test_tc21_nfr_offline_and_portable(self):
        tdir = os.path.join(ROOT, "templates")
        for f in os.listdir(tdir):
            html = open(os.path.join(tdir, f), encoding="utf-8").read()
            self.assertIsNone(re.search(r'(src|href)="https?://', html), f)
        reqs = open(os.path.join(ROOT, "requirements.txt")).read().strip().splitlines()
        self.assertEqual(len(reqs), 1)
        self.assertTrue(reqs[0].lower().startswith("flask"))

    def test_tc22_nfr_maintainability_modules(self):
        for f in ("app.py", "model.py", "data.py"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, f)))
        self.assertGreaterEqual(len(os.listdir(os.path.join(ROOT, "templates"))), 9)

    def test_tc23_nfr_reliability_bad_input(self):
        c = client()
        self.assertEqual(register(c, name="", email="", pw="").status_code, 200)  # message, not a crash
        register(c)
        login(c)
        r = c.post("/predict", data={"symptoms": ["fever", "not_a_symptom"]}, follow_redirects=True)
        self.assertIn(b"at least 2", r.data)  # unknown names are ignored


if __name__ == "__main__":
    unittest.main(verbosity=2)
