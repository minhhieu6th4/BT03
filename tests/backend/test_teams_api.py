import pytest

def test_get_teams_endpoint(client):
    response = client.get("/api/teams/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
