#!/usr/bin/env bash
# Download the Kaggle F1 dataset into scripts/kaggle_data/ (no account needed).
set -e
cd "$(dirname "$0")"
python3 download_data.py kaggle_data
