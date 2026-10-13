import pytest

def test_reject_non_py_submission(client):
    files = {"file": ("bot.txt", b"print('hello')", "text/plain")}
    data = {"team_id": 1}
    response = client.post("/api/submissions/", data=data, files=files)
    assert response.status_code == 400
