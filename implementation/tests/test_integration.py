"""Automated tests. Each test is named after a test case (TC-xx) in the RTM.

The tests start the real services (auth, prediction, history, gateway) as separate
processes and use the system only through HTTP, like a browser would.

Run from the implementation folder:   python -m unittest discover -s tests -v
On PostgreSQL:   set TEST_PG_URL=postgresql://user:pass@localhost:5432  (see harness.py)
"""
import os
import re
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harness import KEY, ROOT, Client, System, api  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "prediction-service"))
import model  # noqa: E402
from data import DISEASES, SYMPTOMS  # noqa: E402

DENGUE = ["high_fever", "severe_headache", "eye_pain_behind", "joint_pain", "skin_rash"]
DIABETES = ["frequent_urination", "excessive_thirst", "blurred_vision"]

SYSTEM = None


def setUpModule():
    global SYSTEM
    SYSTEM = System().start()


def tearDownModule():
    SYSTEM.stop()


def client():
    return Client(SYSTEM.url("gateway"))


def register(c, name="Test User", email="user@test.com", pw="secret1"):
    return c.post("/register", data={"name": name, "email": email, "password": pw})


def login(c, email="user@test.com", pw="secret1"):
    return c.post("/login", data={"email": email, "password": pw})


def users_rows(sql, args=()):
    return SYSTEM.db_rows("auth", sql, args)


def pred_rows(sql, args=()):
    return SYSTEM.db_rows("history", sql, args)


class Tests(unittest.TestCase):
    def setUp(self):
        SYSTEM.exec("history", "DELETE FROM predictions")
        SYSTEM.exec("auth", "DELETE FROM users WHERE is_admin=0")

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
        h = users_rows("SELECT password_hash FROM users WHERE email='user@test.com'")[0][0]
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
        self.assertEqual(pred_rows("SELECT COUNT(*) FROM predictions")[0][0], 0)

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
        rows = pred_rows("SELECT user_id, symptoms, results, created_at FROM predictions")
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
        pid = pred_rows("SELECT id FROM predictions ORDER BY id")[0][0]
        c.post(f"/history/{pid}/delete")
        self.assertEqual(pred_rows("SELECT COUNT(*) FROM predictions")[0][0], 1)

    def test_tc12_only_owner_or_admin_can_open_result(self):
        a, b, adm = client(), client(), client()
        register(a, email="a@test.com")
        login(a, email="a@test.com")
        a.post("/predict", data={"symptoms": DENGUE})
        pid = pred_rows("SELECT id FROM predictions")[0][0]
        register(b, email="b@test.com")
        login(b, email="b@test.com")
        self.assertEqual(b.get(f"/result/{pid}").status_code, 404)
        b.post(f"/history/{pid}/delete")  # must not delete someone else's record
        self.assertEqual(pred_rows("SELECT COUNT(*) FROM predictions")[0][0], 1)
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
        html = r.data.decode().replace("&#39;", "'").replace("&amp;", "&")
        for name in DISEASES:
            self.assertIn(name, html)

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
        rows = users_rows("SELECT email FROM users WHERE is_admin=1")
        self.assertEqual([tuple(r) for r in rows], [("admin@example.com",)])

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
        with open(os.path.join(ROOT, "gateway", "static", "style.css"), encoding="utf-8") as f:
            css = f.read()
        with open(os.path.join(ROOT, "gateway", "templates", "base.html"), encoding="utf-8") as f:
            base = f.read()
        self.assertIn("@media", css)
        self.assertIn('name="viewport"', base)

    def test_tc19_nfr_performance(self):
        t = time.time()
        model.train()
        self.assertLess(time.time() - t, 5.0)
        c = client()
        register(c)
        login(c)
        t = time.time()
        c.post("/predict", data={"symptoms": DENGUE})  # whole path: gateway, prediction and history services
        self.assertLess(time.time() - t, 1.0)

    def test_tc20_nfr_security_sql_injection_and_roles(self):
        c = client()
        register(c)
        r = c.post("/login", data={"email": "' OR 1=1 --", "password": "x"})
        self.assertIn(b"Wrong email or password", r.data)
        self.assertEqual(c.get("/admin").status_code, 302)  # visitor, not admin

    def test_tc21_nfr_offline_and_portable(self):
        tdir = os.path.join(ROOT, "gateway", "templates")
        for f in os.listdir(tdir):
            with open(os.path.join(tdir, f), encoding="utf-8") as fh:
                self.assertIsNone(re.search(r'(src|href)="https?://', fh.read()), f)
        with open(os.path.join(ROOT, "requirements.txt")) as fh:
            reqs = fh.read().strip().splitlines()
        self.assertEqual(len(reqs), 1)
        self.assertTrue(reqs[0].lower().startswith("flask"))

    def test_tc22_nfr_maintainability_modules(self):
        for f in ("gateway/app.py", "gateway/clients.py", "auth-service/app.py", "history-service/app.py",
                  "prediction-service/app.py", "prediction-service/model.py", "prediction-service/data.py"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, f)), f)
        self.assertGreaterEqual(len(os.listdir(os.path.join(ROOT, "gateway", "templates"))), 9)

    def test_tc23_nfr_reliability_bad_input(self):
        c = client()
        self.assertEqual(register(c, name="", email="", pw="").status_code, 200)  # message, not a crash
        register(c)
        login(c)
        r = c.post("/predict", data={"symptoms": ["fever", "not_a_symptom"]}, follow_redirects=True)
        self.assertIn(b"at least 2", r.data)  # unknown names are ignored

    # ---- cloud readiness ----
    def test_tc24_nfr_cloud_ready(self):
        for name in ("gateway", "auth", "prediction", "history"):
            r = Client(SYSTEM.url(name)).get("/health")  # probe used by Docker and load balancers
            self.assertEqual(r.status_code, 200, name)
            self.assertEqual(r.get_json()["status"], "ok", name)
        for f in ("docker-compose.yml", ".env.example", "run_local.py"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, f)), f)
        for folder in ("gateway", "auth-service", "prediction-service", "history-service"):
            for f in ("Dockerfile", "gunicorn.conf.py", "requirements-cloud.txt"):
                self.assertTrue(os.path.exists(os.path.join(ROOT, folder, f)), folder + "/" + f)
            with open(os.path.join(ROOT, folder, "Dockerfile"), encoding="utf-8") as fh:
                self.assertIn("gunicorn", fh.read())

    # ---- microservices ----
    def test_tc25_nfr_microservices_independence(self):
        # each service has its own database, with only its own tables
        self.assertEqual(len(users_rows("SELECT 1 FROM users")) >= 1, True)
        with self.assertRaises(Exception):
            users_rows("SELECT 1 FROM predictions")
        with self.assertRaises(Exception):
            pred_rows("SELECT 1 FROM users")
        # services accept calls only from the gateway (they check the shared key)
        for name, path in (("auth", "/users"), ("history", "/stats"), ("prediction", "/symptoms")):
            self.assertEqual(api(SYSTEM.url(name), "GET", path, key=None)[0], 403, name)
            self.assertEqual(api(SYSTEM.url(name), "GET", path, key="wrong")[0], 403, name)
            self.assertEqual(api(SYSTEM.url(name), "GET", path, key=KEY)[0], 200, name)
        # the prediction service is stateless and works on its own
        status, body = api(SYSTEM.url("prediction"), "POST", "/predict", {"symptoms": DENGUE})
        self.assertEqual((status, body["results"][0][0]), (200, "Dengue"))
        self.assertEqual(api(SYSTEM.url("prediction"), "POST", "/predict", {"symptoms": ["fever"]})[0], 400)
        # the history service stores a user id only, with no link to the user table
        status, body = api(SYSTEM.url("history"), "POST", "/predictions",
                           {"user_id": 99, "symptoms": ["fever", "cough"], "results": [["Common Cold", 50.0]]})
        self.assertEqual(status, 201)
        self.assertEqual(api(SYSTEM.url("history"), "DELETE", f"/predictions/{body['id']}?user_id=1")[1]["deleted"], 0)
        self.assertEqual(api(SYSTEM.url("history"), "DELETE", f"/predictions/{body['id']}?user_id=99")[1]["deleted"], 1)
        # the gateway reports the state of every service
        r = client().get("/ready")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["services"], {"auth": "ok", "prediction": "ok", "history": "ok"})


class ResilienceTests(unittest.TestCase):
    """TC-26: when one service stops, the rest of the system keeps working."""

    def test_tc26_nfr_fault_isolation(self):
        own = System().start()
        try:
            c = Client(own.url("gateway"))
            register(c)
            login(c)
            own.stop("history")                                     # history service goes down
            self.assertEqual(c.get("/history").status_code, 503)    # clear message, not a crash
            self.assertIn(b"history service is not available", c.get("/history").data)
            self.assertEqual(c.get("/diseases").status_code, 200)   # pages that do not need it still work
            self.assertEqual(c.get("/predict").status_code, 200)
            self.assertEqual(c.get("/").status_code, 200)
            self.assertEqual(c.get("/ready").status_code, 503)      # readiness shows the failed service
            self.assertEqual(c.get("/ready").get_json()["services"]["history"], "down")
            self.assertEqual(c.get("/health").status_code, 200)     # the gateway itself is alive
            own.stop("prediction")                                  # now prediction is down too
            self.assertEqual(c.get("/about").status_code, 200)
            self.assertEqual(login(Client(own.url("gateway"))).status_code, 302)  # login still works (auth)
        finally:
            own.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
