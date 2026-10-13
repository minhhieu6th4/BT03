from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MatchBase(BaseModel):
    red_team_id: int
    blue_team_id: int

class MatchCreate(MatchBase):
    pass

class MatchResponse(MatchBase):
    id: int
    status: str
    winner_team_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
