#!/usr/bin/env bash
# Remove everything the scripts generate (all reproducible).
# Usage: ./clean.sh          keeps the venv
#        ./clean.sh --all    also removes the venv
set -e
cd "$(dirname "$0")"
rm -rf kaggle_data
rm -f ../data/corrupted.csv ../data/corrupted_hot.csv
rm -f ../data/raw_data/*.csv ../data/good_data/*.csv ../data/bad_data/*.csv
rm -f ../data/.prediction_state.json
rm -f ../artifacts/model_new.pkl
[ "$1" = "--all" ] && rm -rf .venv
echo "cleaned"
