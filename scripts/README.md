# Scripts

All project scripts live here. Quickest way to use them: the shell runners
(macOS/Linux; on Windows run them in Git Bash, or use the python commands
further down).

| Runner | Does |
|---|---|
| `./get_data.sh` | Downloads the Kaggle F1 dataset into `scripts/kaggle_data/` (no account needed) |
| `./train_model.sh` | Creates the venv on first run, builds the dataset pools, trains the initial model |
| `./make_demo_data.sh [N]` | Makes N demo batches (default 30) for the ingestion DAG: corrupts the incoming pool, splits into 10-row files, and turns the last batch into a schema-error file (missing column → High alert) |
| `./clean.sh [--all]` | Removes everything the scripts generate (`--all` also removes the venv) |

Typical full run, from `scripts/`:

```bash
./get_data.sh
./train_model.sh
./make_demo_data.sh 30
```

---

## What the python scripts do

Two groups behind the runners:

**1. Data setup (run once)** — turns the public Kaggle dataset into the
pipeline's committed inputs. Not part of the running stack.

| Script | Needs | Does |
|---|---|---|
| `download_data.py` | Python only (stdlib) | Downloads + extracts the Kaggle "Formula One Data 2000-2024" CSVs |
| `prepare_data_and_model.py` | venv | Builds the top-10 dataset, trains the model, writes the pools |

Outputs (these ARE committed — they are the pipeline's inputs):

| File | Contents |
|---|---|
| `data/training_data.csv` | 8,720 labeled rows, seasons 2000–2021, **with** the `top10` target |
| `data/inference.csv` | 1,179 unlabeled rows, seasons 2022–2024, **no** target — the "incoming" pool |
| `artifacts/model_new.pkl` | RandomForest pipeline, ~79% accuracy on the unseen 2022–2024 seasons. Gitignored + named `model_new` so re-runs never clobber the live `artifacts/model.pkl` |

**Columns — the simple v1 schema** (exactly what the API and model consume,
from Kaggle `results.csv`): `Season, Round, CircuitID, DriverID,
ConstructorName, Grid`; target `top10` = finished positions 1–10. All six
features are known before the race (no leakage).

**2. Demo data (Defense-1 deliverables)** — prepares the ingestion DAG's
input. Flow: `inference.csv` → inject errors → split → `data/raw_data/`.

| Script | Does |
|---|---|
| `inject_errors.py` | Corrupts a CSV: 7 error types, **one configurable probability per type** (`--p-<type>`, 0 disables) |
| `split_data.py` | Splits a CSV into **N files of exactly 10 rows** (argument = number of files, per the brief) |

Error types (5 mandatory categories + 2 extra):

| Type | Flag | Level | Example |
|---|---|---|---|
| missing_value | `--p-missing-value` | row | required cell emptied (Completeness) |
| wrong_type | `--p-wrong-type` | row | `"abc"` in `Grid` (Type) |
| out_of_range | `--p-out-of-range` | row | `Grid = -5` (Validity) |
| invalid_category | `--p-invalid-category` | row | `ConstructorName = "XYZ Racing"` (Consistency) |
| bad_format | `--p-bad-format` | row | `DriverID = "@@..!!"` (Format) |
| duplicate_rows | `--p-duplicate-rows` | row | rows appended twice (Uniqueness) |
| missing_column | `--p-missing-column` | **file** | required column dropped (Schema) |

`missing_column` defaults to 0 (dropping a column from the big pool would
break every batch); `make_demo_data.sh` applies it to one single batch after
splitting instead — so the demo has clean, row-corrupted and schema-broken
files. Alert levels: Low <10% invalid rows, Medium 10–50%, High >50% or
missing column.

Manual equivalents of the runners:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
python3 download_data.py kaggle_data
.venv/bin/python prepare_data_and_model.py kaggle_data
.venv/bin/python inject_errors.py ../data/inference.csv ../data/corrupted.csv
.venv/bin/python split_data.py ../data/corrupted.csv ../data/raw_data 30
```

(Windows: `.venv\Scripts\pip` / `.venv\Scripts\python`.)

---

## Notes

- Gitignored (all reproducible): `.venv/`, `kaggle_data/`,
  `data/corrupted.csv`, `data/raw_data|good_data|bad_data/*.csv`,
  `artifacts/model_new.pkl`, `data/.prediction_state.json`.
- The Kaggle download works without an account today; the committed
  `data/*.csv` are the safety net if that ever changes.
- Re-run the setup scripts only to change the feature list, the season
  cutoff (`TRAIN_MAX_SEASON`), or the model.
