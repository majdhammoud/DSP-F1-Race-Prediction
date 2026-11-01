"""One-time setup: build the Expectation Suite + Checkpoint for ingestion.

Creates (or replaces) in the file-mode GX project:
    suite      f1_ingestion_suite        - one expectation per error type
    validation f1_ingestion_validation
    checkpoint f1_ingestion_checkpoint   - runs the suite + updates Data Docs

Run it once (and re-run whenever the schema or the rules change):

    python build_expectation_suite.py

Inside the Airflow container the GX project lives at
/opt/airflow/great_expectations (mounted from airflow/great_expectations).
Override with GX_PROJECT_ROOT when running elsewhere.

The suite validates the SIMPLE v1 schema - the six columns the API consumes:
    Season, Round, CircuitID, DriverID, ConstructorName, Grid
"""

import os

GX_PROJECT_ROOT = os.getenv("GX_PROJECT_ROOT", "/opt/airflow/great_expectations")
TRAINING_DATA = os.getenv("TRAINING_DATA_PATH", "/opt/airflow/data/training_data.csv")

SUITE_NAME = "f1_ingestion_suite"
VALIDATION_NAME = "f1_ingestion_validation"
CHECKPOINT_NAME = "f1_ingestion_checkpoint"

REQUIRED_COLUMNS = [
    "Season",
    "Round",
    "CircuitID",
    "DriverID",
    "ConstructorName",
    "Grid",
]


def known_values(column):
    """Allowed categorical values, learned from the committed training seed."""
    import pandas as pd

    return sorted(
        pd.read_csv(TRAINING_DATA, usecols=[column])[column].dropna().unique().tolist()
    )


def main():
    import great_expectations as gx
    import great_expectations.expectations as gxe

    context = gx.get_context(mode="file", project_root_dir=GX_PROJECT_ROOT)

    # --- replace any previous versions so re-running is safe -------------
    for coll, name in (
        (context.checkpoints, CHECKPOINT_NAME),
        (context.validation_definitions, VALIDATION_NAME),
        (context.suites, SUITE_NAME),
    ):
        try:
            coll.delete(name)
        except Exception:
            pass
    try:
        context.data_sources.delete("f1_pandas")
    except Exception:
        pass

    source = context.data_sources.add_pandas(name="f1_pandas")
    asset = source.add_dataframe_asset(name="ingested_batch")
    batch_def = asset.add_batch_definition_whole_dataframe("batch")

    suite = context.suites.add(gx.ExpectationSuite(name=SUITE_NAME))

    # Completeness - no nulls in any required column
    for col in REQUIRED_COLUMNS:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

    # Validity - business ranges (numeric columns are coerced by the helper,
    # so text like "abc" shows up as null -> reclassified as type error)
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="Season", min_value=2000, max_value=2030
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(column="Round", min_value=1, max_value=25)
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(column="Grid", min_value=0, max_value=40)
    )

    # Consistency - categoricals must be values seen in the training data
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="ConstructorName", value_set=known_values("ConstructorName")
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="CircuitID", value_set=known_values("CircuitID")
        )
    )

    # Format - DriverID is lowercase snake_case (catches "@@...!!" garbage)
    suite.add_expectation(
        gxe.ExpectColumnValuesToMatchRegex(column="DriverID", regex=r"^[a-z0-9_]+$")
    )

    # Uniqueness - no duplicated rows
    suite.add_expectation(
        gxe.ExpectCompoundColumnsToBeUnique(column_list=REQUIRED_COLUMNS)
    )

    validation = context.validation_definitions.add(
        gx.ValidationDefinition(name=VALIDATION_NAME, data=batch_def, suite=suite)
    )

    context.checkpoints.add(
        gx.Checkpoint(
            name=CHECKPOINT_NAME,
            validation_definitions=[validation],
            actions=[gx.checkpoint.UpdateDataDocsAction(name="update_data_docs")],
            result_format={"result_format": "COMPLETE"},
        )
    )

    print(f"suite '{SUITE_NAME}' built: {len(suite.expectations)} expectations")
    print(f"checkpoint '{CHECKPOINT_NAME}' ready in {GX_PROJECT_ROOT}")


if __name__ == "__main__":
    main()
