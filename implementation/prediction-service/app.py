"""Prediction service: the knowledge base and the Naive Bayes model. Stateless, no database.

REST API (JSON). Called only by the gateway, with the X-Internal-Key header.
    GET  /symptoms             -> 200 {symptoms: [...]}
    GET  /diseases             -> 200 {diseases: {name: info}}
    GET  /diseases/<name>      -> 200 {info} | 404
    POST /predict {symptoms}   -> 200 {results: [[disease, percent], ...]} | 400 (fewer than 2 known symptoms)
    GET  /model                -> 200 {accuracy, diseases, symptoms}
    GET  /health
"""
import logging
import os
import sys

from flask import Flask, jsonify, request

import model
from data import DISEASES, SYMPTOMS

SERVICE = "prediction-service"
INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")

logging.basicConfig(
    stream=sys.stdout,
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s " + SERVICE + ": %(message)s",
)

app = Flask(__name__)


@app.before_request
def require_internal_key():
    if request.path == "/health" or not INTERNAL_KEY:
        return None
    if request.headers.get("X-Internal-Key") != INTERNAL_KEY:
        return jsonify(error="forbidden"), 403
    return None


@app.get("/symptoms")
def symptoms():
    return jsonify(symptoms=SYMPTOMS)


@app.get("/diseases")
def diseases():
    return jsonify(diseases=DISEASES)


@app.get("/diseases/<path:name>")
def disease(name):
    if name not in DISEASES:
        return jsonify(error="not found"), 404
    return jsonify(info=DISEASES[name])


@app.post("/predict")
def predict():
    body = request.get_json(silent=True) or {}
    raw = body.get("symptoms")
    if not isinstance(raw, list):
        return jsonify(error="symptoms must be a list"), 400
    chosen = [s for s in raw if isinstance(s, str) and s in SYMPTOMS]
    if len(chosen) < 2:
        return jsonify(error="select at least 2 known symptoms"), 400
    return jsonify(results=model.predict(chosen, top_n=3))


@app.get("/model")
def model_info():
    return jsonify(accuracy=model.get_bundle()["accuracy"], diseases=len(DISEASES), symptoms=len(SYMPTOMS))


@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE, model="trained")


model.get_bundle()  # train at start-up so the first prediction is instant
app.logger.info("Started (%d diseases, %d symptoms)", len(DISEASES), len(SYMPTOMS))

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5002")))
