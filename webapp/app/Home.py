import streamlit as st

st.set_page_config(page_title="F1 Race Prediction", page_icon="🏎️", layout="wide")

st.title("🏎️ Formula 1 Top-10 Prediction")

st.markdown(
    """
Welcome to the **Formula 1 Race Prediction System**.

This application predicts whether a driver will finish inside the **Top 10**
before a race begins.

### Features

- 🔮 Single Prediction
- 📂 Batch Prediction (CSV)
- 📊 View Past Predictions
- 📈 Prediction History

Use the navigation menu on the left to get started.
"""
)

st.info("Select a page from the sidebar.")
