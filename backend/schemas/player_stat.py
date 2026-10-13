from pydantic import BaseModel
from typing import Optional

class PlayerStatResponse(BaseModel):
    user_id: int
    username: str
    total_matches: int
    wins: int
    draws: int
    losses: int
    total_points: int
    server_rank: int
    win_rate: float

    class Config:
        from_attributes = True

class ServerLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    total_matches: int
    wins: int
    draws: int
    losses: int
    total_points: int
    win_rate: float

    class Config:
        from_attributes = True
