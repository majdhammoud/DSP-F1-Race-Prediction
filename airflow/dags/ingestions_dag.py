import json
import os
import random
import sys
from datetime import datetime

import pandas as pd
from airflow.exceptions import AirflowSkipException
from airflow.sdk import dag, task
from utils.ge_helpers import validate_dataframe

sys.path.insert(0, "/opt/airflow/dags")
RAW = "/opt/airflow/data/raw_data"
GOOD = "/opt/airflow/data/good_data"
BAD = "/opt/airflow/data/bad_data"

TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")
DATA_DOCS_BASE_URL = os.getenv("DATA_DOCS_BASE_URL", "")
APP_DB_CONN_ID = "app_db"  # Airflow Connection to the project database


@dag(
    # schedule="* * * * *",   # <- enable for the demo (every minute)
    schedule=None,  # manual runs only while developing
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ingestion"],
)
def ingestion_dag():

    @task
    def read_data() -> dict:
        files = [f for f in os.listdir(RAW) if f.endswith(".csv")]
        if not files:
            raise AirflowSkipException("no files in raw_data")
        chosen = random.choice(files)
        path = os.path.join(RAW, chosen)
        df = pd.read_csv(path)
        os.remove(path)
        return {"file_name": chosen, "data": df.to_json(orient="records")}

    @task
    def validate_data(payload: dict) -> dict:
        df = pd.read_json(payload["data"], orient="records")
        result = validate_dataframe(df)
        result["file_name"] = payload["file_name"]
        result["data"] = payload["data"]
        return result

    @task
    def save_statistics(v: dict) -> None:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        errors = v["error_counts"]
        hook = PostgresHook(postgres_conn_id=APP_DB_CONN_ID)
        hook.run(
            """
            INSERT INTO ingestion_stats
                (file_name, total_rows, valid_rows, invalid_rows, criticality,
                 null_count, type_error_count, range_count, consistency_count,
                 format_count, duplicate_count, schema_error)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            parameters=(
                v["file_name"],
                v["total_rows"],
                v["total_rows"] - v["invalid_rows"],
                v["invalid_rows"],
                v["criticality"],
                errors["null"],
                errors["type_error"],
                errors["range"],
                errors["consistency"],
                errors["format"],
                errors["duplicate"],
                v["schema_error"],
            ),
        )
        print(
            f"[save_statistics] saved stats for {v['file_name']} "
            f"(criticality={v['criticality']})"
        )

    @task
    def send_alerts(v: dict) -> None:
        import requests

        if v["criticality"] not in ("medium", "high"):
            print(f"[send_alerts] criticality={v['criticality']}, no alert")
            return

        report = v.get("report_filename", "")
        report_link = (
            f"{DATA_DOCS_BASE_URL}/{report}"
            if DATA_DOCS_BASE_URL and report
            else "not available"
        )
        errors = v["error_counts"]

        payload = {
            "@type": "MessageCard",
            "summary": f"Data Quality Alert - {v['criticality'].upper()}",
            "themeColor": "FF0000" if v["criticality"] == "high" else "FFA500",
            "sections": [
                {
                    "activityTitle": f"Data Quality Alert - {v['criticality'].upper()}",
                    "facts": [
                        {"name": "File", "value": v["file_name"]},
                        {
                            "name": "Invalid rows",
                            "value": f"{v['invalid_rows']}/{v['total_rows']} "
                            f"({v['percent_invalid']}%)",
                        },
                        {
                            "name": "Missing columns",
                            "value": ", ".join(v["missing_columns"]) or "none",
                        },
                        {"name": "Error counts", "value": json.dumps(errors)},
                        {"name": "Report", "value": report_link},
                    ],
                }
            ],
        }

        if not TEAMS_WEBHOOK_URL:
            print(
                f"[send_alerts] no TEAMS_WEBHOOK_URL set - would send: "
                f"{payload['summary']}"
            )
            return
        resp = requests.post(TEAMS_WEBHOOK_URL, json=payload, timeout=10)
        print(f"[send_alerts] Teams alert sent (status {resp.status_code})")

    @task
    def split_and_save_data(v: dict) -> None:
        df = pd.read_json(v["data"], orient="records")
        bad_indices = set(v["bad_row_indices"])
        file_name = v["file_name"]

        os.makedirs(GOOD, exist_ok=True)
        os.makedirs(BAD, exist_ok=True)

        if v["invalid_rows"] == 0:
            df.to_csv(os.path.join(GOOD, file_name), index=False)
            print(f"[split_and_save_data] all rows clean -> {GOOD}/{file_name}")

        elif v["invalid_rows"] == v["total_rows"]:
            df.to_csv(os.path.join(BAD, file_name), index=False)
            print(f"[split_and_save_data] all rows bad -> {BAD}/{file_name}")

        else:
            good_df = df[~df.index.isin(bad_indices)]
            bad_df = df[df.index.isin(bad_indices)]
            good_df.to_csv(os.path.join(GOOD, file_name), index=False)
            bad_df.to_csv(os.path.join(BAD, file_name), index=False)
            print(
                f"[split_and_save_data] split: {len(good_df)} good, "
                f"{len(bad_df)} bad rows -> {file_name}"
            )

    v = validate_data(read_data())
    save_statistics(v)
    send_alerts(v)
    split_and_save_data(v)


ingestion_dag()
