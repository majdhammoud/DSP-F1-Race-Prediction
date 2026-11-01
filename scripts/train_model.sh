#!/usr/bin/env bash
# Build the dataset pools and train the initial model.
# Creates the venv on first run. Requires get_data.sh to have run.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
    echo "creating venv..."
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/python prepare_data_and_model.py kaggle_data
