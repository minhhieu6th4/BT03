from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.models.user import User
from backend.models.room import Room
from backend.schemas.room import (
    RoomCreate, RoomResponse, RoomJoinRequestResponse, RoomJoinRequestAction, SelectBotRequest
)
from backend.dependencies.auth import get_current_user
from backend.services.room_service import RoomService

router = APIRouter()

class ReadyRequest(BaseModel):
    is_ready: bool

class FinishMatchRequest(BaseModel):
    winner_user_id: Optional[int] = None
    is_draw: bool = False

@router.post("/{identifier}/select-bot", response_model=RoomResponse)
def select_room_bot(
    identifier: str,
    data: SelectBotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Người chơi chọn Bot tham gia thi đấu trong phòng"""
    room = RoomService.get_room_by_id_or_code(db, identifier)
    caller_id = current_user.id if current_user else None
    RoomService.select_bot(db, room.id, current_user, data.bot_id)
    return RoomService._to_response(db, room, caller_id)

@router.get("/{identifier}/match-state")
def get_room_match_state(
    identifier: str,
    db: Session = Depends(get_db)
):
    """Lấy trạng thái trực tiếp, danh sách nước đi và kết quả thi đấu của 2 bot trong phòng"""
    room = RoomService.get_room_by_id_or_code(db, identifier)
    return RoomService.get_room_match_state(db, room.id)

@router.post("/", response_model=RoomResponse)
def create_room(
    data: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tạo phòng thi đấu thường mới. Người tạo trở thành chủ phòng."""
    room = RoomService.create_room(db, current_user, data.name)
    return RoomService._to_response(db, room, current_user.id)

@router.get("/", response_model=List[RoomResponse])
def list_open_rooms(db: Session = Depends(get_db)):
    """Danh sách các phòng đang mở và chờ đối thủ (1/2 người)"""
    return RoomService.list_open_rooms(db)

@router.get("/{identifier}", response_model=RoomResponse)
def get_room_details(
    identifier: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xem chi tiết phòng theo ID hoặc mã phòng (ROOM CODE)"""
    room = RoomService.get_room_by_id_or_code(db, identifier)
    caller_id = current_user.id if current_user else None
    return RoomService._to_response(db, room, caller_id)

@router.post("/{identifier}/join", response_model=RoomJoinRequestResponse)
def request_join_room(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gửi yêu cầu tham gia phòng đấu tới chủ phòng"""
    return RoomService.request_join_room(db, identifier, current_user)

@router.post("/{identifier}/requests/{request_id}", response_model=RoomResponse)
def respond_join_request(
    identifier: str,
    request_id: int,
    action_data: RoomJoinRequestAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chủ phòng duyệt yêu cầu tham gia: ACCEPT hoặc REJECT"""
    room = RoomService.get_room_by_id_or_code(db, identifier)
    return RoomService.respond_to_request(
        db=db,
        room_id=room.id,
        request_id=request_id,
        owner=current_user,
        action=action_data.action
    )

@router.post("/{identifier}/ready", response_model=RoomResponse)
def set_ready(
    identifier: str,
    data: ReadyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Người chơi chuyển trạng thái Sẵn sàng / Hủy sẵn sàng"""
    room = RoomService.get_room_by_id_or_code(db, identifier)
    return RoomService.set_ready_status(db, room.id, current_user, data.is_ready)

@router.post("/{identifier}/start")
def start_match(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chủ phòng bắt đầu trận đấu khi cả 2 người chơi đều đã sẵn sàng cùng Bot"""
    room = RoomService.get_room_by_id_or_code(db, identifier)
    match = RoomService.start_room_match(db, room.id, current_user)
    return {
        "message": "Trận đấu giữa 2 bot đã hoàn thành thành công!",
        "match_id": match.id,
        "room_id": room.id,
        "red_user_id": match.red_user_id,
        "blue_user_id": match.blue_user_id,
        "winner_user_id": match.winner_user_id,
        "is_draw": match.is_draw,
        "termination_reason": match.termination_reason,
        "total_turns": match.total_turns
    }

@router.post("/{identifier}/finish")
def finish_match(
    identifier: str,
    data: FinishMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Kết thúc trận đấu và ghi nhận điểm số (Idempotent):
    - Thắng: +3 điểm
    - Hòa: +1 điểm mỗi bên
    - Thua: +0 điểm
    """
    room = RoomService.get_room_by_id_or_code(db, identifier)
    match = RoomService.finish_room_match(
        db,
        room.id,
        winner_user_id=data.winner_user_id,
        is_draw=data.is_draw
    )
    return {
        "message": "Trận đấu đã kết thúc, điểm số và rank server đã được cập nhật!",
        "match_id": match.id,
        "winner_user_id": match.winner_user_id,
        "is_draw": match.is_draw,
        "points_awarded": match.points_awarded
    }

@router.post("/{identifier}/cancel")
def cancel_room(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chủ phòng hủy phòng đấu khi chưa thi đấu hoặc không có người tham gia"""
    room = RoomService.get_room_by_id_or_code(db, identifier)
    cancelled_room = RoomService.cancel_room(db, room.id, current_user)
    return {
        "message": "Đã hủy phòng thành công!",
        "room_id": cancelled_room.id,
        "status": cancelled_room.status
    }
