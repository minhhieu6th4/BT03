from pydantic import BaseModel

class RankingBase(BaseModel):
    team_id: int

class RankingResponse(RankingBase):
    id: int
    score: int
    wins: int
    losses: int
    team_name: str | None = None
    
    class Config:
        from_attributes = True
