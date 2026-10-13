from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GameBase(BaseModel):
    match_id: int

class GameCreate(GameBase):
    pass

class GameResponse(GameBase):
    id: int
    log_file_path: Optional[str] = None
    winner_team_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
