"""Split a dataset into files of EXACTLY 10 rows each for the ingestion DAG.

    python scripts/split_data.py <dataset.csv> <raw_data_dir> <n_files>

Takes the dataset path, the raw_data folder path and the NUMBER OF FILES to
generate (not the number of rows per file - course requirement). Rows are
shuffled so each file mixes seasons/drivers, then written as
raw_data/batch_001.csv, batch_002.csv, ...
"""

import argparse
import os
import sys

import pandas as pd

ROWS_PER_FILE = 10  # fixed by the course brief - penalty if not exactly 10


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="path to the input CSV")
    parser.add_argument("raw_data_dir", help="output folder (e.g. data/raw_data)")
    parser.add_argument("n_files", type=int, help="number of files to generate")
    parser.add_argument("--seed", type=int, default=42, help="shuffle seed")
    args = parser.parse_args()

    df = pd.read_csv(args.dataset)
    needed = args.n_files * ROWS_PER_FILE
    if len(df) < needed:
        sys.exit(
            f"error: need {needed} rows for {args.n_files} files "
            f"of {ROWS_PER_FILE}, dataset has only {len(df)}"
        )

    df = df.sample(frac=1, random_state=args.seed).reset_index(drop=True)

    os.makedirs(args.raw_data_dir, exist_ok=True)
    for i in range(args.n_files):
        chunk = df.iloc[i * ROWS_PER_FILE : (i + 1) * ROWS_PER_FILE]
        path = os.path.join(args.raw_data_dir, f"batch_{i + 1:03d}.csv")
        chunk.to_csv(path, index=False)

    print(
        f"wrote {args.n_files} files of {ROWS_PER_FILE} rows "
        f"to {args.raw_data_dir}/ ({needed}/{len(df)} rows used)"
    )


if __name__ == "__main__":
    main()
