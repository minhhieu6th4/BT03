from pydantic import BaseModel
from datetime import datetime

class CompetitionBase(BaseModel):
    name: str

class CompetitionCreate(CompetitionBase):
    pass

class CompetitionResponse(CompetitionBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
