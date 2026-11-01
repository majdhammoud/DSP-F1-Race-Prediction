# tests/test_models.py

from database.models import PredictionLog


def test_prediction_model():
    prediction = PredictionLog(
        season=2025,
        round=1,
        circuit_id="bahrain",
        driver_id="verstappen",
        constructor_name="Red Bull",
        grid=1,
        prediction=True,
        probability=0.98,
        source="webapp",
    )

    assert prediction.season == 2025
    assert prediction.driver_id == "verstappen"
    assert prediction.prediction is True
    assert prediction.source == "webapp"
