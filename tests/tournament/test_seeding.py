import pytest
from tournament.seeding import select_top_32

def test_select_top_32_teams():
    # 10 bảng, mỗi bảng 10 đội
    standings = {}
    for g in range(10):
        standings[f"Group_{g}"] = [
            {"id": g*10 + i, "points": 30 - i*3} for i in range(10)
        ]
    top_32 = select_top_32(standings)
    assert len(top_32) == 32
