"""Machine-learning part (pure Python, no scikit-learn / numpy needed).

Builds a training set from the symptom profiles in data.py, trains a Bernoulli
Naive Bayes classifier, and predicts the top matching diseases.
Pure Python means it also runs on locked-down Windows PCs (Smart App Control)
that block unsigned compiled libraries.
"""
import math
import random

from data import DISEASES, SYMPTOMS

_INDEX = {s: i for i, s in enumerate(SYMPTOMS)}
_bundle = None


def build_dataset(n_per_class=400, seed=42):
    """Create synthetic patient records from each disease's symptom profile."""
    rng = random.Random(seed)
    rows = []
    for name, d in DISEASES.items():
        for _ in range(n_per_class):
            row = [0] * len(SYMPTOMS)
            for s in d["core"]:
                if rng.random() < 0.85:
                    row[_INDEX[s]] = 1
            for s in d["secondary"]:
                if rng.random() < 0.40:
                    row[_INDEX[s]] = 1
            for i in range(len(SYMPTOMS)):      # random noise symptoms
                if rng.random() < 0.02:
                    row[i] = 1
            if sum(row) == 0:
                row[_INDEX[rng.choice(d["core"])]] = 1
            rows.append((row, name))
    return rows


def _fit(rows, classes):
    """Bernoulli Naive Bayes with Laplace smoothing."""
    n_feat = len(SYMPTOMS)
    counts = {c: [0] * n_feat for c in classes}
    totals = {c: 0 for c in classes}
    for row, c in rows:
        totals[c] += 1
        for i, v in enumerate(row):
            if v:
                counts[c][i] += 1
    theta = {c: [(counts[c][i] + 1) / (totals[c] + 2) for i in range(n_feat)] for c in classes}
    prior = {c: math.log(totals[c] / len(rows)) for c in classes}
    return theta, prior


def _scores(theta, prior, row):
    """Normalised class probabilities (softmax of log-likelihoods)."""
    logs = {}
    for c in theta:
        lp = prior[c]
        for i, v in enumerate(row):
            t = theta[c][i]
            lp += math.log(t) if v else math.log(1 - t)
        logs[c] = lp
    m = max(logs.values())
    exp = {c: math.exp(v - m) for c, v in logs.items()}
    z = sum(exp.values())
    return {c: v / z for c, v in exp.items()}


def train():
    classes = list(DISEASES)
    rows = build_dataset()
    random.Random(1).shuffle(rows)
    cut = int(len(rows) * 0.8)
    train_rows, test_rows = rows[:cut], rows[cut:]
    theta, prior = _fit(train_rows, classes)
    correct = 0
    for row, c in test_rows:
        p = _scores(theta, prior, row)
        correct += max(p, key=p.get) == c
    accuracy = correct / len(test_rows)
    # Final model uses all data
    theta, prior = _fit(rows, classes)
    return {"theta": theta, "prior": prior, "accuracy": accuracy}


def get_bundle():
    """Train once (takes about a second) and keep the model in memory."""
    global _bundle
    if _bundle is None:
        _bundle = train()
    return _bundle


def predict(selected, top_n=3):
    """Return the top_n [(disease, match %), ...] for the chosen symptoms."""
    b = get_bundle()
    row = [0] * len(SYMPTOMS)
    for s in selected:
        if s in _INDEX:
            row[_INDEX[s]] = 1
    probs = _scores(b["theta"], b["prior"], row)
    ranked = sorted(probs.items(), key=lambda x: -x[1])[:top_n]
    # Cap at 95%: a symptom checker should never claim certainty.
    return [(name, round(min(p * 100, 95.0), 1)) for name, p in ranked]


if __name__ == "__main__":
    print(f"Model trained. Hold-out accuracy on the sample dataset: {get_bundle()['accuracy']:.1%}")
