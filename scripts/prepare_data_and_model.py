"""One-time bootstrap: build the F1 top-10 dataset, train the initial model,
and split the data into the pools the pipeline needs.

Run this ONCE before starting the project (it is not part of the running
stack), from INSIDE the scripts/ folder:

    python prepare_data_and_model.py <kaggle_data_dir>

where <kaggle_data_dir> contains the Kaggle "Formula One Data 2000-2024" CSVs
(only results.csv is used).

The dataset uses the SIMPLE v1 schema - exactly the six columns the API and
model consume:

    Season, Round, CircuitID, DriverID, ConstructorName, Grid

Target: top10 (1 if the driver finished the race in positions 1-10).

Outputs (paths relative to the repo root):
    artifacts/model_new.pkl   initial model (RandomForest pipeline) -- named
                              model_new so re-runs never clobber the live
                              artifacts/model.pkl the API loads
    data/training_data.csv    labeled training seed (seasons <= 2021, has top10)
    data/inference.csv        unlabeled "incoming" pool (seasons >= 2022, no top10)

Next step after running:
    python split_data.py ../data/inference.csv ../data/raw_data <n_files>
"""

import os
import sys

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

TRAIN_MAX_SEASON = 2021  # <= trains the model; later seasons = incoming data

NUMERIC_FEATURES = ["Season", "Round", "Grid"]
CATEGORICAL_FEATURES = ["CircuitID", "DriverID", "ConstructorName"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "top10"


def build_dataset(data_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(data_dir, "results.csv"))
    df[TARGET] = (df["Position"] <= 10).astype(int)
    # Grid 0 = pit-lane start / unknown -> treat as starting last
    df.loc[df["Grid"] == 0, "Grid"] = 20
    return df[FEATURES + [TARGET]]


def train_model(train: pd.DataFrame) -> Pipeline:
    model = Pipeline(
        [
            (
                "prep",
                ColumnTransformer(
                    [
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore"),
                            CATEGORICAL_FEATURES,
                        )
                    ],
                    remainder="passthrough",
                ),
            ),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=200,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(train[FEATURES], train[TARGET])
    return model


def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: python {sys.argv[0]} <kaggle_data_dir>")

    df = build_dataset(sys.argv[1])
    train = df[df["Season"] <= TRAIN_MAX_SEASON]
    incoming = df[df["Season"] > TRAIN_MAX_SEASON]
    print(
        f"dataset: {len(df)} rows | train {len(train)} "
        f"(2000-{TRAIN_MAX_SEASON}) | incoming {len(incoming)} "
        f"({TRAIN_MAX_SEASON + 1}-{df['Season'].max()}) | "
        f"top10 rate {df[TARGET].mean():.1%}"
    )

    model = train_model(train)

    # honest check: evaluate on the later seasons the model never saw
    preds = model.predict(incoming[FEATURES])
    print(
        classification_report(
            incoming[TARGET], preds, target_names=["not top10", "top10"]
        )
    )

    os.makedirs("../artifacts", exist_ok=True)
    joblib.dump(model, "../artifacts/model_new.pkl")
    print("saved artifacts/model_new.pkl (rename to model.pkl to deploy)")

    os.makedirs("../data", exist_ok=True)
    train.to_csv("../data/training_data.csv", index=False)
    print(f"saved data/training_data.csv ({len(train)} labeled rows)")

    # incoming pool: target removed -- in production you don't know the answer
    incoming.drop(columns=[TARGET]).to_csv("../data/inference.csv", index=False)
    print(f"saved data/inference.csv ({len(incoming)} unlabeled rows)")


if __name__ == "__main__":
    main()
