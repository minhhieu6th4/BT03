import pytest
from game.board import Board
from game.piece import Piece, Team, PieceType

def test_board_initialization():
    board = Board(size=9)
    assert board.size == 9
    for r in range(9):
        for c in range(9):
            assert board.get_piece((r, c)) is None

def test_set_and_get_piece():
    board = Board(size=9)
    piece = Piece(Team.RED, PieceType.ROCK)
    board.set_piece((1, 2), piece)
    assert board.get_piece((1, 2)) == piece
    assert board.get_piece((0, 0)) is None

def test_move_piece():
    board = Board(size=9)
    piece = Piece(Team.RED, PieceType.ROCK)
    board.set_piece((1, 1), piece)
    board.move_piece((1, 1), (2, 2))
    assert board.get_piece((1, 1)) is None
    assert board.get_piece((2, 2)) == piece

def test_remove_piece():
    board = Board(size=9)
    piece = Piece(Team.BLUE, PieceType.SCISSORS)
    board.set_piece((3, 3), piece)
    board.remove_piece((3, 3))
    assert board.get_piece((3, 3)) is None

def test_board_boundary_check():
    board = Board(size=9)
    assert board.get_piece((-1, 0)) is None
    assert board.get_piece((9, 9)) is None
