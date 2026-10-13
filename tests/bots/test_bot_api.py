import pytest
from bots.api.game_state import GameState
from bots.api.move import Move
from bots.api.bot import BaseBot

def test_game_state_api_helpers():
    raw_board = [[0]*9 for _ in range(9)]
    raw_board[1][1] = 1 # RED ROCK
    raw_board[8][8] = 4 # BLUE ROCK
    
    state_dict = {
        "turn": 1,
        "team": "RED",
        "board": raw_board
    }
    api_state = GameState(state_dict)
    assert api_state.team == "RED"
    assert api_state.size == 9
    assert api_state.turn == 1
    
    my_pieces = api_state.get_my_pieces()
    assert len(my_pieces) == 1
    assert my_pieces[0] == (1, 1)

    enemy_pieces = api_state.get_enemy_pieces()
    assert len(enemy_pieces) == 1
    assert enemy_pieces[0] == (8, 8)

def test_move_api():
    m = Move((0, 1), (1, 1))
    assert m.to_dict() == {"from": [0, 1], "to": [1, 1]}
