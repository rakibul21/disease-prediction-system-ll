"""Start all four services on this computer, without Docker.

    python run_local.py

Then open http://127.0.0.1:5000 . Press Ctrl+C to stop everything.
Each service is its own process on its own port, and has its own database file
(auth-service/auth.db and history-service/history.db).
"""
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVICES = [  # (folder, port); the gateway starts last
    ("auth-service", 5001),
    ("prediction-service", 5002),
    ("history-service", 5003),
    ("gateway", 5000),
]


def wait_healthy(port, proc, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    env = os.environ.copy()
    env.setdefault("INTERNAL_API_KEY", "local-dev-key")
    env.update(
        AUTH_URL="http://127.0.0.1:5001",
        PREDICTION_URL="http://127.0.0.1:5002",
        HISTORY_URL="http://127.0.0.1:5003",
    )
    procs = []
    try:
        for folder, port in SERVICES:
            p = subprocess.Popen(
                [sys.executable, "app.py"], cwd=os.path.join(ROOT, folder),
                env={**env, "PORT": str(port)},
            )
            procs.append(p)
            if not wait_healthy(port, p):
                print(f"\n{folder} did not start. Is Flask installed? (pip install -r requirements.txt)")
                return 1
            print(f"{folder:20s} running on port {port}")
        print("\nAll services are running. Open http://127.0.0.1:5000  (Ctrl+C to stop)")
        while all(p.poll() is None for p in procs):
            time.sleep(1)
        print("A service stopped; shutting down.")
        return 1
    except KeyboardInterrupt:
        print("\nStopping...")
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
