import pytest

def test_get_ranking_endpoint(client):
    response = client.get("/api/ranking/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
