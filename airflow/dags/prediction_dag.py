import json
import logging
import os
from datetime import datetime

import pandas as pd
from airflow.exceptions import AirflowSkipException
from airflow.sdk import dag, task

DATA_DIR = "/opt/airflow/data"
GOOD = os.path.join(DATA_DIR, "good_data")
# remembers the mtime of the newest file already predicted, so files are
# never sent twice and stay in good_data (the D2 training DAG archives them)
STATE_FILE = os.path.join(DATA_DIR, ".prediction_state.json")

API_URL = os.getenv("API_URL", "http://api:8000")

FEATURE_COLUMNS = [
    "Season",
    "Round",
    "CircuitID",
    "DriverID",
    "ConstructorName",
    "Grid",
]


def load_last_run_ts() -> float:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f).get("last_run_ts", 0.0)
    return 0.0


def save_last_run_ts(ts: float) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"last_run_ts": ts}, f)


@dag(
    # schedule="*/2 * * * *",  # <- enable for the demo (every 2 minutes)
    schedule=None,  # manual runs only while developing
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["prediction"],
)
def prediction_dag():

    @task
    def check_for_new_data() -> list[str]:
        """New (not yet predicted) csv files in good_data, else skip the run."""
        if not os.path.isdir(GOOD):
            raise AirflowSkipException("good_data/ does not exist yet")

        last_run_ts = load_last_run_ts()
        new_files = sorted(
            f
            for f in os.listdir(GOOD)
            if f.endswith(".csv")
            and os.path.getmtime(os.path.join(GOOD, f)) > last_run_ts
        )
        if not new_files:
            raise AirflowSkipException("no new files in good_data")
        logging.info("found %d new file(s): %s", len(new_files), new_files)
        return new_files

    @task
    def make_predictions(new_files: list[str]) -> None:
        """Send all new rows to the API in ONE batch call (course requirement)."""
        import requests

        frames = []
        latest_ts = load_last_run_ts()
        for name in new_files:
            path = os.path.join(GOOD, name)
            if not os.path.exists(path):
                logging.warning("file disappeared: %s", name)
                continue
            df = pd.read_csv(path)
            frames.append(df[FEATURE_COLUMNS])
            latest_ts = max(latest_ts, os.path.getmtime(path))

        if not frames:
            logging.info("no rows to predict")
            return

        combined = pd.concat(frames, ignore_index=True)
        resp = requests.post(
            f"{API_URL}/predict",
            json={
                "features": combined.to_dict(orient="records"),
                "source": "scheduled",
            },
            timeout=60,
        )
        resp.raise_for_status()
        logging.info(
            "predicted %d rows from %d file(s)", len(resp.json()), len(new_files)
        )

        # advance the marker only after a successful call -> failed runs retry
        save_last_run_ts(latest_ts)

    make_predictions(check_for_new_data())


prediction_dag()
