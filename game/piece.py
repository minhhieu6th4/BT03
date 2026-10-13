from enum import Enum

class Team(Enum):
    RED = "RED"
    BLUE = "BLUE"

class PieceType(Enum):
    ROCK = "ROCK"
    PAPER = "PAPER"
    SCISSORS = "SCISSORS"

class Piece:
    def __init__(self, team: Team, piece_type: PieceType):
        self.team = team
        self.piece_type = piece_type

    def __repr__(self):
        return f"{self.team.value[0]}_{self.piece_type.value[:2]}"
