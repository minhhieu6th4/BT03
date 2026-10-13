class GameState:
    def __init__(self, state_dict: dict):
        self.turn = state_dict.get("turn", 1)
        self.team = state_dict.get("team", "RED")
        self.player = state_dict.get("player", self.team.lower())
        self.board = state_dict.get("board", [])
        self.size = len(self.board) if self.board else 0
        self.legal_moves = state_dict.get("legal_moves", [])

    def get_my_pieces(self) -> list[tuple[int, int]]:
        team_vals = [1, 2, 3] if self.team == "RED" else [4, 5, 6]
        pieces = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] in team_vals:
                    pieces.append((r, c))
        return pieces

    def get_enemy_pieces(self) -> list[tuple[int, int]]:
        enemy_vals = [4, 5, 6] if self.team == "RED" else [1, 2, 3]
        pieces = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] in enemy_vals:
                    pieces.append((r, c))
        return pieces

    def get_legal_moves(self) -> list[dict]:
        return self.legal_moves
