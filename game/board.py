from typing import Optional, List
from .piece import Piece, Team, PieceType

class Board:
    def __init__(self, size: int = 9):
        self.size = size
        self.grid: List[List[Optional[Piece]]] = [[None for _ in range(size)] for _ in range(size)]

    def get_piece(self, pos: tuple[int, int]) -> Optional[Piece]:
        r, c = pos
        if 0 <= r < self.size and 0 <= c < self.size:
            return self.grid[r][c]
        return None

    def set_piece(self, pos: tuple[int, int], piece: Optional[Piece]):
        r, c = pos
        if 0 <= r < self.size and 0 <= c < self.size:
            self.grid[r][c] = piece

    def move_piece(self, from_pos: tuple[int, int], to_pos: tuple[int, int]):
        piece = self.get_piece(from_pos)
        self.set_piece(from_pos, None)
        self.set_piece(to_pos, piece)

    def remove_piece(self, pos: tuple[int, int]):
        self.set_piece(pos, None)
