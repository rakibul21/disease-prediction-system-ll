# Disease Prediction Management System

A web app where a user registers, logs in, selects symptoms, and gets the most likely
diseases (top 3 with a match score), precautions and the specialist to consult.
Built with **Flask + a pure-Python Naive Bayes model** (no scikit-learn needed). Runs locally with SQLite or in the cloud with PostgreSQL and Docker.

> Educational project. The model is trained on a small **synthetic dataset** generated from
> symptom profiles in `data.py`. It is **not** a medical diagnosis tool.

**Course:** Software Design, Dongshin University
**Professor:** Musa Ibrahim

| Team member | Student ID |
| --- | --- |
| Hasan MD Rakibul | 2677526 |
| Hosen Aiyub | 2677530 |
| Islam MD Din | 2677519 |

## Features
- User registration / login / logout (passwords hashed)
- Symptom picker with live search
- ML prediction: top 3 diseases + match score, precautions, doctor type
- Prediction history per user (view / delete), print or save result as PDF
- About page and footer showing course, professor and team
- Disease library page (19 diseases, 38 symptoms)
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

## Cloud-native deployment

The app follows the [twelve-factor](https://12factor.net) approach, so the same code runs on a laptop, in Docker, or on a cloud platform.

| Cloud-native feature | How it is done here |
| --- | --- |
| Containerised | `Dockerfile` (Python 3.12 slim, non-root user, built-in `HEALTHCHECK`) |
| Production web server | `gunicorn` with `gunicorn.conf.py` (workers set by `WEB_CONCURRENCY`) |
| Stateless app, external database | PostgreSQL through `DATABASE_URL` (`db.py`). SQLite is used only if `DATABASE_URL` is empty |
| Config from the environment | `SECRET_KEY`, `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `PORT`, `COOKIE_SECURE`, `LOG_LEVEL` (see `.env.example`). With `APP_ENV=production` the app refuses to start without a `SECRET_KEY` |
| Health check | `GET /health` returns 200 `{"status":"ok"}` or 503 when the database is down |
| Logs to stdout | Collected by Docker or the platform |
| Behind a load balancer | `TRUST_PROXY=1` (set in the image) uses the proxy headers |
| Horizontal scaling | Any number of identical containers can run. The model trains with a fixed seed, so all give the same answers |
| CI/CD | `.github/workflows/ci.yml` runs the tests on SQLite and PostgreSQL, builds the image and smoke-tests it |
| Infrastructure as code | `docker-compose.yml` (app + PostgreSQL) and `render.yaml` (Render.com blueprint) |

### Run with Docker (app + PostgreSQL)

```bash
cd implementation
docker compose up --build
```

Open http://localhost:5000 and check http://localhost:5000/health. Stop with `docker compose down` (add `-v` to delete the database volume).

### Run the tests on PostgreSQL

```bash
pip install -r requirements-cloud.txt
set DATABASE_URL=postgresql://user:pass@localhost:5432/dbname      # Windows
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname   # Mac/Linux
python -m unittest discover -s tests -v
```

### Deploy to the cloud (Render example)

1. Push the repository to GitHub.
2. In Render choose **New + > Blueprint** and select the repository. It reads `render.yaml` and creates the web service and the PostgreSQL database.
3. Render sets `SECRET_KEY`, `ADMIN_PASSWORD` and `DATABASE_URL` automatically. Read the admin password in the service's environment settings.
4. Open the service URL and `/health`.

The same Docker image also works on AWS (ECS/App Runner), Google Cloud Run, Azure Container Apps or Kubernetes. Only the environment variables change.

## Project structure
```
app.py                  Flask routes, login, configuration, /health
db.py                   Database layer (PostgreSQL or SQLite)
model.py                Dataset generation, training, prediction
data.py                 Diseases, symptoms, precautions, specialists, team info
templates/              HTML pages (Jinja2)
static/style.css        Styling
requirements.txt        Packages for a local run (Flask only)
requirements-cloud.txt  Adds gunicorn and PostgreSQL driver
Dockerfile              Container image
docker-compose.yml      App + PostgreSQL
gunicorn.conf.py        Web server settings
.env.example            Example environment variables
```

## How the prediction works
1. `data.py` stores each disease's core and secondary symptoms.
2. `model.py` generates 400 synthetic patient records per disease (with random noise) and trains a Bernoulli Naive Bayes classifier.
3. When the user submits symptoms, they are converted to a 0/1 vector and the model returns class probabilities; the top 3 are shown (capped at 95%).

## Possible future improvements
- Train on a real dataset (e.g. the Kaggle "Disease Symptom Prediction" dataset)
- Severity weights per symptom, age and gender inputs
- Bengali / Korean language support
- Email password reset, CSRF protection
- Kubernetes manifests, database migrations (Alembic), a separate model service
