import pytest
from game.move import Move

def test_move_initialization():
    move = Move(from_pos=(1, 2), to_pos=(2, 3))
    assert move.from_pos == (1, 2)
    assert move.to_pos == (2, 3)

def test_move_serialization():
    move = Move(from_pos=(0, 1), to_pos=(1, 1))
    d = move.to_dict()
    assert d == {"from": [0, 1], "to": [1, 1]}
    
    move_reconstructed = Move.from_dict(d)
    assert move_reconstructed.from_pos == (0, 1)
    assert move_reconstructed.to_pos == (1, 1)

def test_move_equality():
    m1 = Move((1, 1), (2, 2))
    m2 = Move((1, 1), (2, 2))
    m3 = Move((1, 1), (1, 2))
    assert m1 == m2
    assert m1 != m3
