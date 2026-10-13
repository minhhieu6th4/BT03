from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class BotVersionResponse(BaseModel):
    id: int
    bot_id: int
    version_number: int
    status: str
    validation_error: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BotResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    status: str
    current_version_id: Optional[int] = None
    current_version_number: Optional[int] = 1
    validation_error: Optional[str] = None
    total_versions: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BotDetailResponse(BotResponse):
    versions: List[BotVersionResponse] = []

    class Config:
        from_attributes = True
