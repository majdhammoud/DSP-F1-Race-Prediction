#!/usr/bin/env bash
# Prepare demo batches for the ingestion DAG:
#   corrupt the incoming pool, split into N 10-row files, and make the last
#   batch a schema-error file (missing column -> High criticality alert).
# Usage: ./make_demo_data.sh [n_files]   (default 30)
set -e
cd "$(dirname "$0")"
N="${1:-30}"
PY=.venv/bin/python
[ -x "$PY" ] || { echo "run ./train_model.sh first (creates the venv)"; exit 1; }

$PY inject_errors.py ../data/inference.csv ../data/corrupted.csv
$PY split_data.py ../data/corrupted.csv ../data/raw_data "$N"

LAST=$(printf '../data/raw_data/batch_%03d.csv' "$N")
$PY inject_errors.py "$LAST" "$LAST" \
    --p-missing-column 1 --p-missing-value 0 --p-wrong-type 0 \
    --p-out-of-range 0 --p-invalid-category 0 --p-bad-format 0 \
    --p-duplicate-rows 0
echo "done: $N batches in data/raw_data/ (batch_$(printf '%03d' "$N") has a dropped column)"
