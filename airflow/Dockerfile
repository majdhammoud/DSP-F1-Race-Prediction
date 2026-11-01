FROM apache/airflow:3.1.7

USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
USER airflow

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" pandas apache-airflow-providers-standard great_expectations apache-airflow-providers-postgres