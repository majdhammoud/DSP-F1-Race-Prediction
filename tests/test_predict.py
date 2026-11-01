# from unittest.mock import MagicMock
# from model_service.app import ml


def test_predict(client):

    # fake_model = MagicMock()

    # fake_model.predict.return_value = np.array([1])

    # fake_model.predict_proba.return_value = np.array([[0.10, 0.90]])

    # ml["model"] = fake_model

    payload = {
        "features": [
            {
                "Season": 2025,
                "Round": 1,
                "CircuitID": "bahrain",
                "DriverID": "verstappen",
                "ConstructorName": "Red Bull",
                "Grid": 1,
            }
        ],
        "source": "webapp",
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body[0]["prediction"] is True
