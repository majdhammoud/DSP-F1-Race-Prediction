import requests
from utils.config import API_URL


def health_check():
    """
    Check if the API is running.
    """

    try:
        response = requests.get(f"{API_URL}/health", timeout=5)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        return {"error": str(error)}


def get_options():
    """
    Allowed values for the categorical inputs, extracted from the trained
    model: {"CircuitID": [...], "DriverID": [...], "ConstructorName": [...]}
    """

    try:
        response = requests.get(f"{API_URL}/options", timeout=10)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        return {"error": str(error)}


def predict(features, source="webapp"):
    """
    Send prediction request to FastAPI.

    features: list of dicts, each with keys
        Season (int), Round (int), CircuitID (str),
        DriverID (str), ConstructorName (str), Grid (int)
    source: "webapp" or "scheduled"
    """

    try:
        response = requests.post(
            f"{API_URL}/predict",
            json={"features": features, "source": source},
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        return {"error": str(error)}


def get_past_predictions(start_date=None, end_date=None, source="all"):
    """
    Retrieve previous predictions.

    start_date / end_date: ISO date strings, e.g. "2026-07-01"
    source: "all" | "webapp" | "scheduled"
    """

    try:
        params = {"source": source}

        if start_date:
            params["start"] = start_date

        if end_date:
            params["end"] = end_date

        response = requests.get(
            f"{API_URL}/past-predictions", params=params, timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        return {"error": str(error)}
