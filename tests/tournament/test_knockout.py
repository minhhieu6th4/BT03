import pytest
from tournament.knockout import generate_knockout_bracket

def test_knockout_bracket_round_of_32():
    teams = [f"Team_{i}" for i in range(1, 33)]
    bracket = generate_knockout_bracket(teams)
    assert len(bracket) == 16
    # Seed 1 gặp Seed 32
    assert bracket[0] == ("Team_1", "Team_32")
    # Seed 2 gặp Seed 31
    assert bracket[1] == ("Team_2", "Team_31")
