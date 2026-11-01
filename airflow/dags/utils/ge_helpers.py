"""Helper for running Great Expectations validation in the ingestion DAG.

Uses the SAVED checkpoint built once by build_expectation_suite.py
(file-mode GX project, mounted at /opt/airflow/great_expectations).

validate_dataframe(df) returns everything downstream tasks need:
    total_rows, invalid_rows, percent_invalid
    criticality        "none" | "low" | "medium" | "high"
    schema_error       True when required columns are missing (-> high)
    missing_columns    which ones
    bad_row_indices    row positions with at least one violation
    error_counts       per error type, for the ingestion_stats table
    report_filename    newest Data Docs page, for the Teams alert link
"""

import glob
import os

import pandas as pd

GX_PROJECT_ROOT = os.getenv("GX_PROJECT_ROOT", "/opt/airflow/great_expectations")
CHECKPOINT_NAME = "f1_ingestion_checkpoint"

REQUIRED_COLUMNS = [
    "Season",
    "Round",
    "CircuitID",
    "DriverID",
    "ConstructorName",
    "Grid",
]
NUMERIC_COLUMNS = ["Season", "Round", "Grid"]

# GX expectation type -> our error category (per-type stats for the DB)
CATEGORY_BY_TYPE = {
    "expect_column_values_to_not_be_null": "null",
    "expect_column_values_to_be_between": "range",
    "expect_column_values_to_be_in_set": "consistency",
    "expect_column_values_to_match_regex": "format",
    "expect_compound_columns_to_be_unique": "duplicate",
}


def get_context():
    import great_expectations as gx  # heavy: import at call time, not DAG-parse time

    return gx.get_context(mode="file", project_root_dir=GX_PROJECT_ROOT)


def compute_criticality(schema_error, percent_invalid):
    """Brief rules: High = missing column OR >50% invalid; Medium = 10-50%;
    Low = >0%; none otherwise."""
    if schema_error or percent_invalid > 50:
        return "high"
    elif percent_invalid >= 10:
        return "medium"
    elif percent_invalid > 0:
        return "low"
    return "none"


def _newest_report():
    pages = glob.glob(
        os.path.join(GX_PROJECT_ROOT, "**", "validations", "**", "*.html"),
        recursive=True,
    )
    if not pages:
        return ""
    newest = max(pages, key=os.path.getmtime)
    return os.path.basename(newest)


def validate_dataframe(df):
    total_rows = len(df)
    error_counts = {
        "null": 0,
        "type_error": 0,
        "range": 0,
        "consistency": 0,
        "format": 0,
        "duplicate": 0,
        "schema": 0,
    }

    # ---- schema pre-check: GX cannot validate a missing column, and the
    # brief says missing column = High criticality, all rows unusable -------
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        error_counts["schema"] = len(missing)
        return {
            "total_rows": total_rows,
            "invalid_rows": total_rows,
            "percent_invalid": 100.0,
            "criticality": "high",
            "schema_error": True,
            "missing_columns": missing,
            "bad_row_indices": list(range(total_rows)),
            "error_counts": error_counts,
            "report_filename": "",
        }

    # ---- coerce numerics: text like "abc" in Grid becomes NaN so the range
    # check sees numbers; those cells are counted as type errors below ------
    df_gx = df.copy()
    for col in NUMERIC_COLUMNS:
        df_gx[col] = pd.to_numeric(df_gx[col], errors="coerce")

    context = get_context()
    checkpoint = context.checkpoints.get(CHECKPOINT_NAME)
    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df_gx})
    validation_result = list(checkpoint_result.run_results.values())[0]

    bad_indices = set()
    gx_null_cells = 0
    for r in validation_result.results:
        etype = r.expectation_config.type
        count = r.result.get("unexpected_count") or 0
        bad_indices.update(
            int(i) for i in (r.result.get("unexpected_index_list") or [])
        )
        if etype == "expect_column_values_to_not_be_null":
            gx_null_cells += count
        elif etype in CATEGORY_BY_TYPE:
            error_counts[CATEGORY_BY_TYPE[etype]] += count

    # cells that had a value but weren't numeric = type errors, not nulls
    type_cells = 0
    for col in NUMERIC_COLUMNS:
        coerced = pd.to_numeric(df[col], errors="coerce")
        type_cells += int((coerced.isna() & df[col].notna()).sum())
    error_counts["type_error"] = type_cells
    error_counts["null"] = max(0, gx_null_cells - type_cells)

    invalid_rows = len(bad_indices)
    percent_invalid = round(invalid_rows / total_rows * 100, 2) if total_rows else 0.0

    return {
        "total_rows": total_rows,
        "invalid_rows": invalid_rows,
        "percent_invalid": percent_invalid,
        "criticality": compute_criticality(False, percent_invalid),
        "schema_error": False,
        "missing_columns": [],
        "bad_row_indices": sorted(bad_indices),
        "error_counts": error_counts,
        "report_filename": _newest_report(),
    }
