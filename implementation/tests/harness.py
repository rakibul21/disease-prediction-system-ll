"""Test helpers: start the real services as separate processes, and talk to them over HTTP.

Standard library only. By default every service uses a temporary SQLite file. To run the
tests on PostgreSQL, set TEST_PG_URL to a server URL such as
postgresql://user:pass@localhost:5432 ; two databases are created for the two services.
"""
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = "test-internal-key"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Response:
    def __init__(self, status, body, headers):
        self.status_code, self.data, self.headers = status, body, headers

    def get_json(self):
        return json.loads(self.data)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


class Client:
    """A browser-like client with its own cookies (so each Client is one logged-in user)."""

    def __init__(self, base):
        self.base = base
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), _NoRedirect)

    def _send(self, method, url, data=None, headers=None, follow_redirects=False):
        full = url if url.startswith("http") else self.base + url
        body = None
        headers = dict(headers or {})
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data, doseq=True).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif isinstance(data, (bytes, str)):
            body = data.encode() if isinstance(data, str) else data
        for _ in range(10):
            req = urllib.request.Request(full, data=body, method=method, headers=headers)
            try:
                r = self.opener.open(req, timeout=30)
                resp = Response(r.status, r.read(), r.headers)
            except urllib.error.HTTPError as e:
                resp = Response(e.code, e.read(), e.headers)
            if follow_redirects and resp.status_code in (301, 302, 303):
                full = urllib.parse.urljoin(full, resp.headers["Location"])
                method, body = "GET", None
                continue
            return resp
        raise RuntimeError("too many redirects")

    def get(self, url, **kw):
        return self._send("GET", url, **kw)

    def post(self, url, data=None, **kw):
        return self._send("POST", url, data=data, **kw)


def api(base, method, path, payload=None, key=KEY):
    """Call a service directly (as the gateway would)."""
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers["X-Internal-Key"] = key
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else None)


class System:
    """The four services running as real processes on free ports."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp()
        self.ports = {n: free_port() for n in ("gateway", "auth", "prediction", "history")}
        self.procs = {}
        self.pg = os.environ.get("TEST_PG_URL", "").rstrip("/")
        self.db_names = {}
        if self.pg:
            import uuid
            tag = uuid.uuid4().hex[:8]
            self.db_names = {"auth": f"auth_{tag}", "history": f"hist_{tag}"}
            self._create_pg_databases()

    # ---- databases ----
    def _create_pg_databases(self):
        import psycopg2
        con = psycopg2.connect(self.pg + "/postgres")
        con.autocommit = True
        for name in self.db_names.values():
            con.cursor().execute(f'CREATE DATABASE "{name}"')
        con.close()

    def db_rows(self, which, sql, args=()):
        """Plain DB-API query on the auth or history database."""
        if self.pg:
            import psycopg2
            con = psycopg2.connect(f"{self.pg}/{self.db_names[which]}")
        else:
            import sqlite3
            con = sqlite3.connect(os.path.join(self.tmp, f"{which}.db"))
        try:
            cur = con.cursor()
            cur.execute(sql, args)
            return cur.fetchall()
        finally:
            con.close()

    def exec(self, which, sql):
        if self.pg:
            import psycopg2
            con = psycopg2.connect(f"{self.pg}/{self.db_names[which]}")
        else:
            import sqlite3
            con = sqlite3.connect(os.path.join(self.tmp, f"{which}.db"))
        try:
            con.cursor().execute(sql)
            con.commit()
        finally:
            con.close()

    # ---- processes ----
    def url(self, name):
        return f"http://127.0.0.1:{self.ports[name]}"

    def _start(self, name, folder):
        env = os.environ.copy()
        env.pop("DATABASE_URL", None)
        env.pop("DATABASE_PATH", None)
        env.update(
            PORT=str(self.ports[name]), INTERNAL_API_KEY=KEY,
            AUTH_URL=self.url("auth"), PREDICTION_URL=self.url("prediction"),
            HISTORY_URL=self.url("history"), LOG_LEVEL="WARNING", SERVICE_TIMEOUT="3",
        )
        if name in ("auth", "history"):
            if self.pg:
                env["DATABASE_URL"] = f"{self.pg}/{self.db_names[name]}"
            else:
                env["DATABASE_PATH"] = os.path.join(self.tmp, f"{name}.db")
        self.procs[name] = subprocess.Popen(
            [sys.executable, "app.py"], cwd=os.path.join(ROOT, folder), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def start(self):
        for name, folder in (("auth", "auth-service"), ("prediction", "prediction-service"),
                             ("history", "history-service"), ("gateway", "gateway")):
            self._start(name, folder)
        for name in self.procs:
            self.wait(name)
        return self

    def wait(self, name, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if self.procs[name].poll() is not None:
                raise RuntimeError(f"{name} exited early")
            try:
                with urllib.request.urlopen(self.url(name) + "/health", timeout=2):
                    return
            except OSError:
                time.sleep(0.3)
        raise RuntimeError(f"{name} did not become healthy")

    def stop(self, name=None):
        for n in ([name] if name else list(self.procs)):
            p = self.procs.get(n)
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
