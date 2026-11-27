"""HTTP clients for the three back-end services (standard library only).

Every call has a timeout. If a service cannot be reached, ServiceUnavailable is raised
and the gateway shows a friendly 503 page instead of crashing.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

URLS = {
    "auth": os.environ.get("AUTH_URL", "http://127.0.0.1:5001"),
    "prediction": os.environ.get("PREDICTION_URL", "http://127.0.0.1:5002"),
    "history": os.environ.get("HISTORY_URL", "http://127.0.0.1:5003"),
}
INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")
TIMEOUT = float(os.environ.get("SERVICE_TIMEOUT", "5"))


class ServiceUnavailable(Exception):
    def __init__(self, service):
        super().__init__(f"{service} service is not available")
        self.service = service


def call(service, method, path, payload=None, params=None, timeout=None):
    """Return (status_code, json_body). Raises ServiceUnavailable on network errors."""
    url = URLS[service].rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", "X-Internal-Key": INTERNAL_KEY}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout or TIMEOUT) as resp:
            return resp.status, _json(resp.read())
    except urllib.error.HTTPError as e:   # the service answered with 4xx/5xx
        return e.code, _json(e.read())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ServiceUnavailable(service) from e


def _json(raw):
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


# ---- auth ----
def register(name, email, password):
    return call("auth", "POST", "/register", {"name": name, "email": email, "password": password})


def login(email, password):
    return call("auth", "POST", "/login", {"email": email, "password": password})


def users():
    return call("auth", "GET", "/users")[1]["users"]


# ---- prediction ----
_cache = {}


def symptoms():
    """The symptom list never changes while the service runs, so keep it in memory."""
    if "symptoms" not in _cache:
        _cache["symptoms"] = call("prediction", "GET", "/symptoms")[1]["symptoms"]
    return _cache["symptoms"]


def diseases():
    if "diseases" not in _cache:
        _cache["diseases"] = call("prediction", "GET", "/diseases")[1]["diseases"]
    return _cache["diseases"]


def disease(name):
    return diseases().get(name) or call("prediction", "GET", "/diseases/" + urllib.parse.quote(name))[1]["info"]


def predict(chosen):
    return call("prediction", "POST", "/predict", {"symptoms": chosen})


def model_accuracy():
    return call("prediction", "GET", "/model")[1]["accuracy"] * 100


# ---- history ----
def save_prediction(user_id, symptoms_, results):
    return call("history", "POST", "/predictions",
                {"user_id": user_id, "symptoms": symptoms_, "results": results})[1]["id"]


def history_of(user_id):
    return call("history", "GET", "/predictions", params={"user_id": user_id})[1]["predictions"]


def prediction(pid):
    status, body = call("history", "GET", f"/predictions/{pid}")
    return body if status == 200 else None


def delete_prediction(pid, user_id):
    return call("history", "DELETE", f"/predictions/{pid}", params={"user_id": user_id})


def stats():
    return call("history", "GET", "/stats")[1]


# ---- health ----
def health(service):
    """'ok' or 'down' for one service."""
    try:
        status, _ = call(service, "GET", "/health", timeout=2)
        return "ok" if status == 200 else "down"
    except ServiceUnavailable:
        return "down"
