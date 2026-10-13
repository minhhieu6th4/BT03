from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class RoomCreate(BaseModel):
    name: Optional[str] = "Phòng thách đấu"

class RoomJoinRequestResponse(BaseModel):
    id: int
    room_id: int
    user_id: int
    username: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RoomResponse(BaseModel):
    id: int
    room_code: str
    name: str
    owner_id: int
    owner_name: str
    player1_id: int
    player1_name: Optional[str] = None
    player2_id: Optional[int] = None
    player2_name: Optional[str] = None
    player1_ready: bool
    player2_ready: bool
    player1_bot_id: Optional[int] = None
    player1_bot_name: Optional[str] = None
    player1_bot_version: Optional[int] = None
    player2_bot_id: Optional[int] = None
    player2_bot_name: Optional[str] = None
    player2_bot_version: Optional[int] = None
    status: str
    current_player_count: int
    capacity: int = 2
    current_match_id: Optional[int] = None
    created_at: Optional[datetime] = None
    join_requests: Optional[List[RoomJoinRequestResponse]] = []
    my_role: Optional[str] = "SPECTATOR"
    my_join_status: Optional[str] = None

    class Config:
        from_attributes = True

class RoomJoinRequestAction(BaseModel):
    action: str  # ACCEPT or REJECT

class SelectBotRequest(BaseModel):
    bot_id: int

