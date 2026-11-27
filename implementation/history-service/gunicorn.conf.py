"""Gunicorn settings. Everything can be overridden with environment variables."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5003')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("WEB_THREADS", "2"))
timeout = 30
accesslog = "-"   # logs to stdout
errorlog = "-"
