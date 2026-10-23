from .board import Board
from .piece import Team
from .rule_set import RuleSet

class GameState:
    def __init__(self, rule_set: RuleSet):
        self.turn = 1
        self.current_team = Team.RED
        self.board = Board(size=rule_set.board_size)
        self.rule_set = rule_set
        self.move_log = []
        for rock in getattr(rule_set, "rocks", []):
            self.board.add_rock(tuple(rock))

    def get_legal_moves(self, team=None):
        from .move import Move
        moves = []
        size = self.board.size
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        target_team = team if team is not None else self.current_team
        for r in range(size):
            for c in range(size):
                if self.board.is_rock((r, c)):
                    continue
                piece = self.board.get_piece((r, c))
                if piece and piece.team == target_team:
                    for dr, dc in directions:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < size and 0 <= nc < size:
                            if self.board.is_rock((nr, nc)):
                                continue
                            if self.current_team == Team.RED and nr == 0 and nc == 0:
                                continue
                            if self.current_team == Team.BLUE and nr == size - 1 and nc == size - 1:
                                continue
                            target = self.board.get_piece((nr, nc))
                            if target and target.team == self.current_team:
                                continue
                            moves.append(Move((r, c), (nr, nc)))
        return moves

    def to_dict(self):
        """
        Export state as JSON for Bot API.
        Piece mapping:
        0 = Empty
        1 = RED ROCK, 2 = RED PAPER, 3 = RED SCISSORS
        4 = BLUE ROCK, 5 = BLUE PAPER, 6 = BLUE SCISSORS
        7 = ROCK OBSTACLE (Đá cản)
        """
        board_repr = []
        for r in range(self.board.size):
            row_repr = []
            for c in range(self.board.size):
                if self.board.is_rock((r, c)):
                    row_repr.append(7)
                    continue
                piece = self.board.grid[r][c]
                if piece is None:
                    row_repr.append(0)
                else:
                    val = 1 if piece.piece_type.name == "ROCK" else (2 if piece.piece_type.name == "PAPER" else 3)
                    if piece.team == Team.BLUE:
                        val += 3
                    row_repr.append(val)
            board_repr.append(row_repr)

        legal_moves = [m.to_dict() for m in self.get_legal_moves()]

        return {
            "turn": self.turn,
            "team": self.current_team.value,
            "player": self.current_team.value.lower(),
            "board_size": self.board.size,
            "board": board_repr,
            "rocks": [list(pos) for pos in sorted(self.board.rocks)],
            "legal_moves": legal_moves
        }

