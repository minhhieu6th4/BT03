import pytest
from game.game_engine import GameEngine
from game.rule_set import RuleSet
from game.move import Move
from game.piece import Piece, Team, PieceType
from game.game_result import ResultType

def test_engine_initial_board_pieces(game_engine):
    # Mỗi bên phải có đúng 6 quân (2 Búa, 2 Kéo, 2 Bao)
    state = game_engine.state
    red_count = 0
    blue_count = 0
    for r in range(state.board.size):
        for c in range(state.board.size):
            p = state.board.get_piece((r, c))
            if p:
                if p.team == Team.RED: red_count += 1
                elif p.team == Team.BLUE: blue_count += 1
                
    assert red_count == 6
    assert blue_count == 6

def test_valid_8_directions_movement(game_engine):
    state = game_engine.state
    # Quân đỏ tại (0, 1) có thể đi xuống (1, 1) nếu trống hoặc hợp lệ
    # Đặt thử 1 quân đỏ độc lập ở giữa bàn cờ (4, 4)
    piece = Piece(Team.RED, PieceType.ROCK)
    state.board.set_piece((4, 4), piece)
    state.current_team = Team.RED
    
    directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
    for dr, dc in directions:
        target = (4 + dr, 4 + dc)
        move = Move((4, 4), target)
        assert game_engine.is_valid_move(state, move) is True

def test_invalid_move_distance_greater_than_1(game_engine):
    state = game_engine.state
    state.board.set_piece((4, 4), Piece(Team.RED, PieceType.ROCK))
    state.current_team = Team.RED
    
    # Nhảy 2 ô
    invalid_move = Move((4, 4), (6, 4))
    assert game_engine.is_valid_move(state, invalid_move) is False

def test_invalid_move_to_own_base(game_engine):
    state = game_engine.state
    # Quân đỏ ở (0, 1) không được phép đi lùi vào ô đích nhà mình (0, 0)
    move = Move((0, 1), (0, 0))
    state.current_team = Team.RED
    assert game_engine.is_valid_move(state, move) is False

def test_combat_rock_paper_scissors(game_engine):
    rock = Piece(Team.RED, PieceType.ROCK)
    scissors = Piece(Team.BLUE, PieceType.SCISSORS)
    paper = Piece(Team.BLUE, PieceType.PAPER)
    
    # Búa thắng Kéo
    assert game_engine._resolve_combat(rock, scissors) == rock
    # Bao thắng Búa
    assert game_engine._resolve_combat(paper, rock) == paper
    # Cùng loại thì tự hủy cả 2
    rock_blue = Piece(Team.BLUE, PieceType.ROCK)
    assert game_engine._resolve_combat(rock, rock_blue) is None

def test_win_condition_destination(game_engine):
    state = game_engine.state
    # Đặt quân Đỏ vào ô đích (8, 8)
    state.board.set_piece((8, 8), Piece(Team.RED, PieceType.ROCK))
    res = game_engine.check_winner(state)
    assert res is not None
    assert res.result_type == ResultType.WIN
    assert res.winner == Team.RED

def test_win_condition_total_pieces_eliminated(game_engine):
    state = game_engine.state
    # Ban đầu mỗi bên 6 quân
    # Xóa sạch quân Kéo của Đỏ (nhưng vẫn còn Đá và Giấy)
    for r in range(state.board.size):
        for c in range(state.board.size):
            p = state.board.get_piece((r, c))
            if p and p.team == Team.RED and p.piece_type == PieceType.SCISSORS:
                state.board.remove_piece((r, c))

    # Theo luật mới: Mất hết quân cùng một loại KHÔNG BỊ THUA!
    res = game_engine.check_winner(state)
    assert res is None  # Trận đấu vẫn tiếp tục bình thường

    # Xóa sạch toàn bộ quân cờ của Đỏ trên bàn (0 quân đỏ còn lại)
    for r in range(state.board.size):
        for c in range(state.board.size):
            p = state.board.get_piece((r, c))
            if p and p.team == Team.RED:
                state.board.remove_piece((r, c))

    # Theo luật mới: Khi mất sạch TẤT CẢ các quân cờ của mình -> Bị xử thua!
    res = game_engine.check_winner(state)
    assert res is not None
    assert res.result_type == ResultType.WIN
    assert res.winner == Team.BLUE
    assert "Red lost all pieces" in res.reason

