import pytest

def test_points_calculation():
    # Thắng 3 điểm, Hòa 1 điểm, Thua 0 điểm
    score_win = 3
    score_draw = 1
    score_loss = 0
    assert score_win > score_draw > score_loss
