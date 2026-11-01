import pandas as pd
import streamlit as st
from services.api import get_options, predict

st.title("🔮 Prediction")

OTHER = "Other…"

REQUIRED_COLUMNS = [
    "Season",
    "Round",
    "CircuitID",
    "DriverID",
    "ConstructorName",
    "Grid",
]


@st.cache_data
def load_options():
    """
    One API call per session: the allowed categorical values, straight from
    the trained model. Returns None if the API is unreachable, so the form
    can fall back to free-text inputs.
    """

    result = get_options()

    if isinstance(result, dict) and "error" in result:
        return None

    return result


def categorical_input(label, key, options):
    """
    Dropdown of known values plus an "Other…" entry revealing a free-text
    field (new drivers/constructors are allowed - the model handles unknown
    values). Falls back to a plain text input when options are unavailable.
    """

    if options is None or not options.get(key):
        return st.text_input(label, key=f"{key}_text")

    choice = st.selectbox(label, options[key] + [OTHER], key=f"{key}_select")

    if choice == OTHER:
        return st.text_input(f"{label} (new value)", key=f"{key}_other")

    return choice


options = load_options()

if options is None:
    st.warning("Could not load known values from the API - using free-text inputs.")

st.header("Single Prediction")

season = st.number_input("Season", min_value=2000, max_value=2030, value=2024)

round_number = st.number_input("Round", min_value=1, max_value=25, value=1)

circuit = categorical_input("Circuit", "CircuitID", options)

driver = categorical_input("Driver", "DriverID", options)

constructor = categorical_input("Constructor", "ConstructorName", options)

grid_position = st.number_input("Grid Position", min_value=0, max_value=40, value=1)

if st.button("Predict"):
    if not (circuit and driver and constructor):
        st.error("Please fill in circuit, driver and constructor.")
    else:
        row = {
            "Season": int(season),
            "Round": int(round_number),
            "CircuitID": circuit,
            "DriverID": driver,
            "ConstructorName": constructor,
            "Grid": int(grid_position),
        }

        with st.spinner("Calling prediction API..."):
            result = predict([row])

        if isinstance(result, dict) and "error" in result:
            st.error(f"Prediction failed: {result['error']}")
        else:
            pred = result[0]
            label = "✅ Top 10" if pred["prediction"] else "❌ Not Top 10"
            st.success(f"{label} — probability: {pred['probability']:.1%}")

st.divider()

st.header("Batch Prediction")

uploaded_file = st.file_uploader("Upload CSV", type="csv")

if uploaded_file is not None:
    dataframe = pd.read_csv(uploaded_file)

    st.subheader("Preview")

    st.dataframe(dataframe)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in dataframe.columns]

    if missing_columns:
        st.error(
            "CSV is missing required column(s): "
            + ", ".join(missing_columns)
            + f". Expected columns: {REQUIRED_COLUMNS}"
        )
    elif st.button("Predict Batch"):
        rows = dataframe[REQUIRED_COLUMNS].to_dict(orient="records")

        with st.spinner(f"Calling prediction API for {len(rows)} row(s)..."):
            result = predict(rows)

        if isinstance(result, dict) and "error" in result:
            st.error(f"Batch prediction failed: {result['error']}")
        else:
            result_df = pd.DataFrame(result)
            st.subheader("Results")
            st.dataframe(result_df, use_container_width=True)
