from pydantic import BaseModel
from datetime import datetime
from typing import List

class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    pass

class TeamResponse(TeamBase):
    id: int
    owner_id: int | None = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TeamMemberAdd(BaseModel):
    user_id: int

class TeamOwnerChange(BaseModel):
    user_id: int

class TeamMemberResponse(BaseModel):
    user_id: int
    username: str
    role: str

class TeamDetailResponse(TeamResponse):
    members: List[TeamMemberResponse]
