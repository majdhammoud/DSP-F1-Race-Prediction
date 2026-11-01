# DSP F1 Race Prediction

An end-to-end MLOps pipeline that predicts whether a Formula 1 driver
finishes in the top 10, built for the EPITA Data Science in Production
course. A trained model is served through an API and a web app, while an
Airflow-orchestrated pipeline continuously ingests new race data,
validates it with Great Expectations, alerts on data quality problems,
and makes scheduled predictions on the clean rows.

## Architecture

Everything runs from one Docker Compose file:

| Service | Container | Purpose |
|---|---|---|
| PostgreSQL | f1_postgres | One instance, two databases: app data (predictions, ingestion statistics) and Airflow metadata |
| FastAPI | f1_api | Model service: /predict, /past-predictions, /options, /health |
| Streamlit | f1_webapp | Web UI: single and batch predictions, past-prediction browsing |
| Airflow (x4) | airflow-init, airflow-api-server, airflow-dag-processor, airflow-scheduler | Orchestrates the ingestion and prediction DAGs |

The webapp only talks to the API; the API and the DAGs use the shared
SQLAlchemy models in `database/`; all connection settings come from
environment variables.

## Prerequisites

- Git
- Docker with Compose v2 (Docker Desktop on macOS/Windows, Docker Engine
  on Linux), running
- Python 3.10+ (only for the data/model scripts, not for the stack)

Windows only, once, BEFORE cloning:

```
git config --global core.autocrlf false
```

## 1. Get the code

```
git clone https://github.com/Drsquihi/DSP-F1-Race-Prediction.git
cd DSP-F1-Race-Prediction
```

## 2. Configure the environment

```
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

Open `.env` and fill in every value:

| Variable | What to put |
|---|---|
| POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD | App database name and credentials — any values, created on first boot |
| POSTGRES_PORT | Host port for postgres (default 5435, avoids clashing with a local postgres) |
| AIRFLOW_DB_PASSWORD | Password for Airflow's database user. Letters and digits ONLY |
| AIRFLOW_JWT_SECRET / AIRFLOW_SECRET_KEY | Generate with the python one-liners in the comments of `.env.example` |
| AIRFLOW_UID | Linux: output of `id -u`. macOS/Windows: leave empty |
| TEAMS_WEBHOOK_URL | Teams incoming-webhook URL for data quality alerts; may stay empty (alerts are then written to the task log) |

`.env` is gitignored — real values never go into the repository.

## 3. Start the stack

```
docker compose up -d --build
```

The first run builds all images (several minutes). On a fresh volume,
postgres automatically creates both databases.

If this machine ran an older version of the project before, reset the
database volume once so it is recreated with your current `.env`:

```
docker compose down -v
docker compose up -d --build
```

## 4. Verify

`docker compose ps` should show:

| Container | State |
|---|---|
| f1_postgres | healthy |
| f1_api | healthy |
| f1_webapp | running |
| airflow-init | Exited (0) — one-shot migration job, exiting is success |
| airflow-api-server | healthy |
| airflow-scheduler, airflow-dag-processor | running |

| Service | URL |
|---|---|
| Web app | http://localhost:8501 |
| API (Swagger docs) | http://localhost:8000/docs |
| Airflow UI | http://localhost:8021 |

Airflow login: user `admin`, generated password printed in the log:

```
docker compose logs airflow-api-server | grep -i password
```

(Windows PowerShell: `docker compose logs airflow-api-server | Select-String password`)

## 5. Prepare data for the pipeline

The trained model (`artifacts/model.pkl`) and the data pools
(`data/training_data.csv`, `data/inference.csv`) are committed, so the
API and webapp work immediately. What a fresh clone lacks is ingestion
input: batch files in `data/raw_data/`.

From `scripts/` (macOS/Linux, or Git Bash on Windows):

```
cd scripts
./get_data.sh            # download the Kaggle dataset
./train_model.sh         # create the venv (writes model_new.pkl, never overwrites the live model)
./make_demo_data.sh 30   # 30 x 10-row batches into data/raw_data/, with injected errors
cd ..
```

Details on every script, error types and native Windows equivalents:
`scripts/README.md`.

## 6. Run the pipeline

In the Airflow UI (http://localhost:8021):

1. Unpause and trigger `ingestion_dag`. Each run picks one random file
   from `data/raw_data/`, validates it with Great Expectations, saves
   statistics to the database, sends a Teams alert on medium/high
   criticality, and splits the rows into `data/good_data/` and/or
   `data/bad_data/`. Trigger several times to process several files.
2. Unpause and trigger `prediction_dag`. It collects new files from
   `data/good_data/`, calls `POST /predict` with `source="scheduled"`,
   and the API stores the predictions. No new files = the run skips
   (expected, not an error).

Both DAGs are on-demand during development (`schedule=None`); each DAG
file contains a commented `schedule=` cron line to enable scheduled
execution.

The Great Expectations Data Docs report for each validation run is
generated under
`airflow/great_expectations/gx/uncommitted/data_docs/local_site/` — open
the newest HTML file under `validations/` in a browser.

## 7. See the results

- Web app, Prediction page: single prediction via the form (dropdowns
  offer the values known to the model, new values are accepted), or
  batch prediction via CSV upload with columns
  `Season, Round, Grid, CircuitID, DriverID, ConstructorName`.
- Web app, Past Predictions page: filter by date range and source
  (`webapp` / `scheduled`).
- API: interactive Swagger at http://localhost:8000/docs.

Or straight from the database:

```
docker compose exec postgres psql -U <POSTGRES_USER> -d <POSTGRES_DB> \
  -c "SELECT file_name, total_rows, valid_rows, invalid_rows, criticality FROM ingestion_stats ORDER BY ingested_at DESC LIMIT 10;"
```

## Tests and linting

CI (GitHub Actions) runs black, isort, flake8 and pytest on every push
and pull request. Locally:

```
python3 -m venv .venv-dev
.venv-dev/bin/pip install -r requirements-dev.txt
.venv-dev/bin/black . && .venv-dev/bin/isort . && .venv-dev/bin/flake8
DATABASE_URL=sqlite:///./test.db .venv-dev/bin/pytest -q
```

## Stop / reset

```
docker compose down        # stop, keep all data
docker compose down -v     # stop and wipe both databases
```

`scripts/clean.sh` removes everything the scripts generate
(`--all` also removes the venv).

## Project structure

```
airflow/            Airflow image, DAGs (ingestion, prediction), Great Expectations project
artifacts/          trained model (model.pkl)
data/               data pools + raw_data / good_data / bad_data folders
database/           shared SQLAlchemy models and connection handling
model_service/      FastAPI model service
scripts/            data download, model training, error injection, demo data
tests/              pytest suite (runs against SQLite in CI)
webapp/             Streamlit application
docker-compose.yml  the whole stack
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| "password authentication failed for user airflow" | `AIRFLOW_DB_PASSWORD` has special characters, or the volume predates your `.env`: fix the password, then `docker compose down -v && docker compose up -d --build` |
| ingestion_dag PermissionError on data files (Linux) | set `AIRFLOW_UID=$(id -u)` in `.env`, then `docker compose up -d --build` |
| Every file shows as modified after cloning (Windows) | clone happened before `git config --global core.autocrlf false`: set it, delete the clone, re-clone |
| Port already in use | change `POSTGRES_PORT` in `.env`, or free ports 8000 / 8501 / 8021 |
| Webapp cannot reach the API | `docker compose ps` must show f1_api healthy; inside the network the webapp uses `http://api:8000` |
