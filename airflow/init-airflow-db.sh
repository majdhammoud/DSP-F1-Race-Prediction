#!/bin/bash
# Runs once when the postgres volume is first created (docker-entrypoint-initdb.d).
# Creates the SECOND database in the single PostgreSQL instance: Airflow's
# metadata DB, separate from the application data - per the course brief.
# Baked into the image via postgres.Dockerfile (not bind-mounted) so host
# filesystem permissions can never break it.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    CREATE USER airflow WITH PASSWORD '${AIRFLOW_DB_PASSWORD}';
    CREATE DATABASE airflow OWNER airflow;
EOSQL
