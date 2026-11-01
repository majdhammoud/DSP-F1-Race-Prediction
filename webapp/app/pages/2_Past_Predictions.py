import pandas as pd
import streamlit as st
from services.api import get_past_predictions

st.title("📊 Past Predictions")

SOURCE_MAP = {
    "All": "all",
    "Webapp": "webapp",
    "Scheduled": "scheduled",
}

col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Start Date")

with col2:
    end_date = st.date_input("End Date")

source = st.selectbox("Prediction Source", list(SOURCE_MAP.keys()))

st.divider()

st.subheader("Prediction History")

with st.spinner("Loading past predictions..."):
    result = get_past_predictions(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        source=SOURCE_MAP[source],
    )

if isinstance(result, dict) and "error" in result:
    st.error(f"Could not load past predictions: {result['error']}")
elif result:
    df = pd.json_normalize(result)

    # Flatten "features" dict columns if present, for a friendlier table
    if "features" in df.columns:
        features_df = pd.json_normalize(df["features"])
        df = pd.concat([df.drop(columns=["features"]), features_df], axis=1)

    st.dataframe(df, use_container_width=True)
else:
    st.info("No prediction history available.")
