from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TournamentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    min_participants: Optional[int] = 4
    max_participants: Optional[int] = 32

class TournamentRegisterRequest(BaseModel):
    bot_id: Optional[int] = None

class TournamentRespondRequest(BaseModel):
    action: str  # "ACCEPTED" | "REJECTED" | "approve" | "reject"

class TournamentParticipantResponse(BaseModel):
    id: int
    user_id: int
    username: str
    bot_id: Optional[int] = None
    bot_name: Optional[str] = None
    status: str = "PENDING"
    seed: int = 0
    registered_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TournamentMatchResponse(BaseModel):
    id: int
    round_id: int
    match_order: int
    player1_id: Optional[int] = None
    player1_name: Optional[str] = None
    player1_bot_id: Optional[int] = None
    player1_bot_name: Optional[str] = None
    player1_joined_at: Optional[datetime] = None
    player2_id: Optional[int] = None
    player2_name: Optional[str] = None
    player2_bot_id: Optional[int] = None
    player2_bot_name: Optional[str] = None
    player2_joined_at: Optional[datetime] = None
    winner_id: Optional[int] = None
    winner_name: Optional[str] = None
    is_bye: bool
    status: str
    ready_at: Optional[datetime] = None
    participation_deadline: Optional[datetime] = None
    seconds_remaining: Optional[int] = None
    result_reason: Optional[str] = None
    match_id: Optional[int] = None

    class Config:
        from_attributes = True

class TournamentRoundResponse(BaseModel):
    id: int
    round_number: int
    round_name: str
    status: str
    matches: List[TournamentMatchResponse] = []

    class Config:
        from_attributes = True

class TournamentResponse(BaseModel):
    id: int
    name: str
    description: str
    creator_id: int
    creator_name: Optional[str] = None
    min_participants: int = 4
    max_participants: int = 32
    status: str
    participant_count: int
    accepted_count: int = 0
    pending_count: int = 0
    champion_id: Optional[int] = None
    champion_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TournamentDetailResponse(BaseModel):
    tournament: TournamentResponse
    participants: List[TournamentParticipantResponse] = []
    rounds: List[TournamentRoundResponse] = []

    class Config:
        from_attributes = True

