def test_past_predictions(client):

    response = client.get("/past-predictions")

    assert response.status_code == 200

    assert isinstance(response.json(), list)
