import pytest

def test_get_tournament_tree(client):
    response = client.get("/api/matches/tree")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    stages = [s["stage"] for s in data]
    assert "qualification" in stages
    assert "final" in stages

def test_get_replay_endpoint(client):
    response = client.get("/api/matches/game/game_01/replay")
    assert response.status_code == 200
    data = response.json()
    assert "moves" in data
    assert "initial_board" in data
