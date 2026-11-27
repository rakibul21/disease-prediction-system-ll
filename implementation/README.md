# Disease Prediction Management System

A web app where a user registers, logs in, selects symptoms, and gets the most likely
diseases (top 3 with a match score), precautions and the specialist to consult.
Built as **microservices** with Flask and a pure-Python Naive Bayes model (no scikit-learn needed).

> Educational project. The model is trained on a small **synthetic dataset** generated from
> symptom profiles in `prediction-service/data.py`. It is **not** a medical diagnosis tool.

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

## Architecture: four services

The browser talks only to the **gateway**. The gateway calls the other services over HTTP (REST, JSON).

| Service | Port | Job | Own database |
| --- | --- | --- | --- |
| `gateway` | 5000 | Web pages, login session, calls the other services | none |
| `auth-service` | 5001 | Register, login, user list | `users` table |
| `prediction-service` | 5002 | Knowledge base and Naive Bayes model | none (stateless) |
| `history-service` | 5003 | Saves and reads predictions, statistics | `predictions` table |

```
 Browser --> gateway --+--> auth-service        --> auth database
                       +--> prediction-service      (no database)
                       +--> history-service     --> history database
```

- **Database per service.** No service reads another service's tables. The history service stores only a user id number.
- **Only the gateway is public.** The services accept calls only with the shared `X-Internal-Key` header.
- **Failures stay small.** If the history service is down, the home page, disease library, prediction form and login still work, and the gateway shows a clear 503 message for the pages that need it.
- **Health checks.** Every service has `/health`. The gateway also has `/ready`, which shows whether all services are up.

### REST API of the services (called by the gateway)

| Service | Endpoints |
| --- | --- |
| auth | `POST /register`, `POST /login`, `GET /users`, `GET /health` |
| prediction | `GET /symptoms`, `GET /diseases`, `GET /diseases/<name>`, `POST /predict`, `GET /model`, `GET /health` |
| history | `POST /predictions`, `GET /predictions?user_id=`, `GET /predictions/<id>`, `DELETE /predictions/<id>?user_id=`, `GET /stats`, `GET /health` |

## Run locally (no Docker)

Requires Python 3.9+.

```bash
python -m venv venv
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
python run_local.py
```

`run_local.py` starts the four services (each its own process) and prints their ports. Open http://127.0.0.1:5000 and press `Ctrl+C` to stop. Each service creates its own SQLite file (`auth-service/auth.db`, `history-service/history.db`).

### Demo admin account
- Email: `admin@example.com`
- Password: `admin123`

## Run with Docker (four containers + PostgreSQL)

```bash
docker compose up --build
```

Open http://localhost:5000 and check http://localhost:5000/ready. Only the gateway is published; the services talk to each other on a private network. The auth and history services use separate databases (`auth_db`, `history_db`) on one PostgreSQL server. Stop with `docker compose down` (add `-v` to delete the data).

Check the running system from the command line:

```bash
python scripts/smoke_test.py http://localhost:5000
```

## Cloud-native features

| Feature | How it is done here |
| --- | --- |
| Containerised | One `Dockerfile` per service (Python 3.12 slim, non-root user, `HEALTHCHECK`) |
| Production server | `gunicorn` with `gunicorn.conf.py` in every service |
| External database | PostgreSQL through `DATABASE_URL` (SQLite only if it is not set) |
| Config from the environment | `SECRET_KEY`, `INTERNAL_API_KEY`, `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `*_URL`, `PORT`, `LOG_LEVEL` (see `.env.example`) |
| Stateless services | The gateway keeps the login in a signed cookie; the prediction service has no data |
| Logs to stdout | Collected by Docker or the platform |
| CI/CD | `.github/workflows/ci.yml` runs the tests on SQLite and PostgreSQL, then builds all images and smoke-tests the whole system |
| Blueprint for Render.com | `render.yaml` in the repository root (not tested) |

## Tests

```bash
python -m unittest discover -s tests -v
```

The 26 tests start the four real services as separate processes and use the system through HTTP. Test names match the test cases (TC-01 to TC-26) in the RTM. TC-25 checks that the services are independent (own databases, internal key) and TC-26 checks that the system keeps working when a service is stopped.

Run them on PostgreSQL:

```bash
pip install psycopg2-binary
set TEST_PG_URL=postgresql://user:pass@localhost:5432      # Windows
export TEST_PG_URL=postgresql://user:pass@localhost:5432   # Mac/Linux
python -m unittest discover -s tests -v
```

## Project structure

```
gateway/              Web pages (templates, static), session, clients.py (calls the services)
auth-service/         Users and login (app.py, db.py)
prediction-service/   data.py (knowledge base), model.py (Naive Bayes), app.py (API)
history-service/      Saved predictions and statistics (app.py, db.py)
postgres/             SQL that creates the second database
scripts/smoke_test.py End-to-end check of a running system
tests/                harness.py (starts the services) and test_integration.py
run_local.py          Starts all services without Docker
docker-compose.yml    All services + PostgreSQL
.env.example          Example environment variables
RACI-matrix.md        Team responsibilities
```

Each service folder is self-contained (own `requirements.txt`, `Dockerfile`, `gunicorn.conf.py`).

## Possible future improvements
- Train the model on a real dataset (for example from Kaggle)
- Nearby medical facility map, more diseases (Dengue and Diabetes first)
- Token-based login (JWT) between the services, CSRF protection, e-mail password reset
- Message queue for events, Kubernetes manifests, database migrations (Alembic)
