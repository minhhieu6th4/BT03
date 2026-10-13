from pydantic import BaseModel
from datetime import datetime

class SubmissionBase(BaseModel):
    team_id: int

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionResponse(SubmissionBase):
    id: int
    file_path: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
