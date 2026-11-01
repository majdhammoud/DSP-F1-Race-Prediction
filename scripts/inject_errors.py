"""Inject data-quality errors into a clean dataset (for testing validation).

    python scripts/inject_errors.py <clean.csv> <corrupted.csv> [--p-<type> P ...]

Each error type has its own configurable probability (course requirement):
the fraction of rows it corrupts, 0 disables it. Seven types:

  row-level
    missing_value      required cell set to empty        (Completeness)
    wrong_type         text in a numeric column          (Type)
    out_of_range       impossible Grid position          (Validity)
    invalid_category   unknown constructor/circuit       (Consistency)
    bad_format         garbage characters in DriverID    (Format)
    duplicate_rows     rows appended twice               (Uniqueness)
  file-level
    missing_column     a required column dropped         (Schema)

missing_column defaults to 0: when corrupting one big dataset it would affect
every batch made from it. Instead, run this script on individual raw_data
batch files with --p-missing-column 1 to create a few schema-broken batches.
"""

import argparse

import numpy as np
import pandas as pd

NUMERIC_COL = "Grid"
ID_COL = "DriverID"
CATEGORY_COLS = ["ConstructorName", "CircuitID"]
REQUIRED_COLS = ["Season", "Round", "CircuitID", "DriverID", "Grid", "ConstructorName"]

ROW_ERRORS = [
    "missing_value",
    "wrong_type",
    "out_of_range",
    "invalid_category",
    "bad_format",
    "duplicate_rows",
]


def pick_rows(df, prob, rng):
    n = int(round(len(df) * prob))
    return rng.choice(df.index, size=min(n, len(df)), replace=False)


def inject(df, probs, rng):
    counts = {}

    # columns that will receive non-numeric garbage must hold strings
    for col in [NUMERIC_COL, "Season"]:
        df[col] = df[col].astype(object)

    for idx in pick_rows(df, probs["missing_value"], rng):
        df.loc[idx, rng.choice(REQUIRED_COLS)] = np.nan
    counts["missing_value"] = int(round(len(df) * probs["missing_value"]))

    for idx in pick_rows(df, probs["wrong_type"], rng):
        df.loc[idx, NUMERIC_COL] = rng.choice(["abc", "ten", "N/A"])
    counts["wrong_type"] = int(round(len(df) * probs["wrong_type"]))

    for idx in pick_rows(df, probs["out_of_range"], rng):
        df.loc[idx, NUMERIC_COL] = int(rng.choice([-5, 0, 99, 1000]))
    counts["out_of_range"] = int(round(len(df) * probs["out_of_range"]))

    for idx in pick_rows(df, probs["invalid_category"], rng):
        col = rng.choice(CATEGORY_COLS)
        df.loc[idx, col] = rng.choice(["XYZ Racing", "moon_circuit", "???"])
    counts["invalid_category"] = int(round(len(df) * probs["invalid_category"]))

    for idx in pick_rows(df, probs["bad_format"], rng):
        df.loc[idx, ID_COL] = "@@" + str(df.loc[idx, ID_COL])[::-1] + "!!"
    counts["bad_format"] = int(round(len(df) * probs["bad_format"]))

    dup_idx = pick_rows(df, probs["duplicate_rows"], rng)
    df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)
    counts["duplicate_rows"] = len(dup_idx)

    if rng.random() < probs["missing_column"]:
        col = rng.choice(REQUIRED_COLS)
        df = df.drop(columns=[col])
        counts["missing_column"] = f"dropped '{col}'"
    else:
        counts["missing_column"] = 0

    return df, counts


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input", help="clean input CSV")
    parser.add_argument("output", help="corrupted output CSV")
    for err in ROW_ERRORS:
        parser.add_argument(
            f"--p-{err.replace('_', '-')}",
            type=float,
            default=0.05,
            dest=err,
            help=f"fraction of rows for {err} (default 0.05)",
        )
    parser.add_argument(
        "--p-missing-column",
        type=float,
        default=0.0,
        dest="missing_column",
        help="probability of dropping a column (default 0)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="random seed (default: random each run)"
    )
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    df = pd.read_csv(args.input)
    probs = {e: getattr(args, e) for e in ROW_ERRORS + ["missing_column"]}

    corrupted, counts = inject(df, probs, rng)
    corrupted.to_csv(args.output, index=False)

    print(f"wrote {args.output}: {len(df)} rows in, {len(corrupted)} rows out")
    for err, n in counts.items():
        print(f"  {err:18s} {n}")


if __name__ == "__main__":
    main()
