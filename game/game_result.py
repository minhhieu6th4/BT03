from enum import Enum
from .piece import Team

class ResultType(Enum):
    WIN = "WIN"
    DRAW = "DRAW"

class GameResult:
    def __init__(self, result_type: ResultType, winner: Team = None, reason: str = ""):
        self.result_type = result_type
        self.winner = winner
        self.reason = reason

    def to_dict(self):
        return {
            "result_type": self.result_type.value,
            "winner": self.winner.value if self.winner else None,
            "reason": self.reason
        }
