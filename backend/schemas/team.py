from pydantic import BaseModel
from datetime import datetime

class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    pass

class TeamResponse(TeamBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
