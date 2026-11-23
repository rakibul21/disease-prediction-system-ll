# Disease Prediction Management System

A web app where a user registers, logs in, selects symptoms, and gets the most likely
diseases (top 3 with a match score), precautions and the specialist to consult.
Built with **Flask + SQLite + a pure-Python Naive Bayes model** (no scikit-learn needed).

> Educational project. The model is trained on a small **synthetic dataset** generated from
> symptom profiles in `data.py`. It is **not** a medical diagnosis tool.

## Features
- User registration / login / logout (passwords hashed)
- Symptom picker with live search
- ML prediction: top 3 diseases + match score, precautions, doctor type
- Prediction history per user (view / delete), print or save result as PDF
- Disease library page (18 diseases, 40+ symptoms)
- Admin dashboard: user list, total predictions, most predicted diseases, model accuracy

## Run locally

Requires Python 3.9+.

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd disease-prediction-system

python -m venv venv
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

The database (`database.db`) is created automatically on first run; the model trains in memory in about a second.

### Demo admin account
- Email: `admin@example.com`
- Password: `admin123`

(Normal users can register from the Register page.)

## Project structure
```
app.py            Flask routes, login, database
model.py          Dataset generation, training, prediction
data.py           Diseases, symptoms, precautions, specialists
templates/        HTML pages (Jinja2)
static/style.css  Styling
requirements.txt  Python packages
```

## How the prediction works
1. `data.py` stores each disease's core and secondary symptoms.
2. `model.py` generates 400 synthetic patient records per disease (with random noise) and trains a Bernoulli Naive Bayes classifier.
3. When the user submits symptoms, they are converted to a 0/1 vector and the model returns class probabilities; the top 3 are shown (capped at 95%).

## Possible future improvements
- Train on a real dataset (e.g. the Kaggle "Disease Symptom Prediction" dataset)
- Severity weights per symptom, age and gender inputs
- Bengali / Korean language support
- Email password reset, CSRF protection, deployment (Render / PythonAnywhere)
