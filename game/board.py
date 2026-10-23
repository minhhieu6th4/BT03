from typing import Optional, List
from .piece import Piece, Team, PieceType

class Board:
    def __init__(self, size: int = 9):
        self.size = size
        self.grid: List[List[Optional[Piece]]] = [[None for _ in range(size)] for _ in range(size)]
        self.rocks: set[tuple[int, int]] = set()

    def is_rock(self, pos: tuple[int, int]) -> bool:
        r, c = pos
        return (r, c) in self.rocks

    def add_rock(self, pos: tuple[int, int]):
        r, c = pos
        if 0 <= r < self.size and 0 <= c < self.size:
            self.rocks.add((r, c))
            self.grid[r][c] = None

    def remove_rock(self, pos: tuple[int, int]):
        r, c = pos
        self.rocks.discard((r, c))

    def get_piece(self, pos: tuple[int, int]) -> Optional[Piece]:
        r, c = pos
        if 0 <= r < self.size and 0 <= c < self.size:
            if self.is_rock(pos):
                return None
            return self.grid[r][c]
        return None

    def set_piece(self, pos: tuple[int, int], piece: Optional[Piece]):
        r, c = pos
        if 0 <= r < self.size and 0 <= c < self.size:
            if self.is_rock(pos):
                return
            self.grid[r][c] = piece

    def move_piece(self, from_pos: tuple[int, int], to_pos: tuple[int, int]):
        piece = self.get_piece(from_pos)
        self.set_piece(from_pos, None)
        self.set_piece(to_pos, piece)

    def remove_piece(self, pos: tuple[int, int]):
        self.set_piece(pos, None)

