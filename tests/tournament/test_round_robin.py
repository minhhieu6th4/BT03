import pytest
from tournament.round_robin import generate_round_robin_schedule

def test_round_robin_match_count():
    teams = [f"Team_{i}" for i in range(10)]
    matches = generate_round_robin_schedule(teams)
    # 10 đội đấu vòng tròn = (10 * 9) / 2 = 45 trận
    assert len(matches) == 45

def test_round_robin_all_pairs_unique():
    teams = ["A", "B", "C", "D"]
    matches = generate_round_robin_schedule(teams)
    assert len(matches) == 6
    # Không có trận nào lặp lại
    seen = set()
    for t1, t2 in matches:
        pair = tuple(sorted([t1, t2]))
        assert pair not in seen
        seen.add(pair)
