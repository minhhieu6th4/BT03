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

class TournamentMapCreate(BaseModel):
    name: str
    size: int = 5
    rocks: List[List[int]] = []

class TournamentMapUpdate(BaseModel):
    name: Optional[str] = None
    rocks: Optional[List[List[int]]] = None

class TournamentMapResponse(BaseModel):
    id: int
    tournament_id: int
    name: str
    size: int
    rocks: List[List[int]] = []
    version: int = 1
    is_valid: bool = True
    creator_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AssignRoundMapRequest(BaseModel):
    map_id: int
    map_announced_at: Optional[datetime] = None

class TournamentScheduleCreate(BaseModel):
    batch_size: int = 4
    interval_minutes: int = 10
    first_batch_time: Optional[datetime] = None
    check_in_advance_minutes: int = 10
    max_concurrent_matches: int = 4

class TournamentMatchResponse(BaseModel):
    id: int
    round_id: int
    match_order: int
    wave_number: int = 1
    current_wave: int = 1
    total_waves: int = 1
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
    map_id: Optional[int] = None
    map_name: Optional[str] = None
    map_size: Optional[int] = None
    map_reveal_at: Optional[datetime] = None
    is_map_revealed: bool = True
    rocks: Optional[List[List[int]]] = None
    scheduled_at: Optional[datetime] = None
    check_in_opens_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    participation_deadline: Optional[datetime] = None
    seconds_remaining: Optional[int] = None
    result_reason: Optional[str] = None
    match_id: Optional[int] = None
    is_configured: bool = False

    class Config:
        from_attributes = True

class MatchConfigUpdateRequest(BaseModel):
    map_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None

class MatchBotSelectRequest(BaseModel):
    bot_id: int

class SetupOverviewMatch(BaseModel):
    match_id: int
    round_id: int
    round_number: int
    round_name: str
    match_order: int
    wave_number: int = 1
    player1_id: Optional[int] = None
    player1_name: Optional[str] = None
    player2_id: Optional[int] = None
    player2_name: Optional[str] = None
    is_bye: bool
    map_id: Optional[int] = None
    map_name: Optional[str] = None
    map_size: Optional[int] = None
    rock_count: int = 0
    scheduled_at: Optional[datetime] = None
    map_reveal_at: Optional[datetime] = None
    status: str
    is_configured: bool
    validation_errors: List[str] = []

class SetupOverviewResponse(BaseModel):
    tournament_id: int
    status: str
    can_publish: bool
    total_matches: int
    configured_matches: int
    matches: List[SetupOverviewMatch] = []
    errors: List[str] = []

class TournamentRoundResponse(BaseModel):
    id: int
    round_number: int
    round_name: str
    status: str
    current_wave: int = 1
    total_waves: int = 1
    map_id: Optional[int] = None
    map_name: Optional[str] = None
    map_size: Optional[int] = None
    map_announced_at: Optional[datetime] = None
    is_map_announced: bool = True
    rocks: Optional[List[List[int]]] = None
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
    max_concurrent_matches: int = 4
    status: str
    participant_count: int
    accepted_count: int = 0
    pending_count: int = 0
    champion_id: Optional[int] = None
    champion_name: Optional[str] = None
    setup_started_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TournamentDetailResponse(BaseModel):
    tournament: TournamentResponse
    participants: List[TournamentParticipantResponse] = []
    rounds: List[TournamentRoundResponse] = []
    maps: List[TournamentMapResponse] = []

    class Config:
        from_attributes = True


