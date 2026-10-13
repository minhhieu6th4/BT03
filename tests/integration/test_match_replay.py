import pytest
from backend.services.replay_service import ReplayService

def test_load_replay_from_match_logs():
    # Đọc thử file ván 1 trong vòng bảng
    replay = ReplayService.get_replay_by_path("qualification/group_01/match_0001/game_01.json")
    assert replay is not None
    assert replay["match_id"] == "match_0001"
    assert "initial_board" in replay
    assert "moves" in replay
    assert len(replay["moves"]) > 0
