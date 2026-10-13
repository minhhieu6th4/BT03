from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.models.user import User
from backend.schemas.tournament import (
    TournamentCreate, TournamentResponse, TournamentDetailResponse,
    TournamentParticipantResponse, TournamentMatchResponse,
    TournamentRegisterRequest, TournamentRespondRequest
)
from backend.dependencies.auth import get_current_user
from backend.services.tournament_service import TournamentService

router = APIRouter()

class PlayMatchRequest(BaseModel):
    winner_id: Optional[int] = None

@router.post("/", response_model=TournamentResponse)
def create_tournament(
    data: TournamentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tạo giải đấu loại trực tiếp mới với số lượng tối thiểu và tối đa"""
    t = TournamentService.create_tournament(
        db=db,
        creator=current_user,
        name=data.name,
        description=data.description or "",
        min_participants=data.min_participants or 4,
        max_participants=data.max_participants or 32
    )
    return TournamentService._to_response(db, t)

@router.get("/", response_model=List[TournamentResponse])
def list_tournaments(db: Session = Depends(get_db)):
    """Danh sách các giải đấu"""
    return TournamentService.list_tournaments(db)

@router.get("/{tournament_id}", response_model=TournamentDetailResponse)
def get_tournament_details(tournament_id: int, db: Session = Depends(get_db)):
    """Xem chi tiết giải đấu, danh sách tuyển thủ và cây thi đấu (Bracket)"""
    return TournamentService.get_tournament_detail(db, tournament_id)

@router.post("/{tournament_id}/register")
def register_tournament(
    tournament_id: int,
    data: Optional[TournamentRegisterRequest] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đăng ký tham gia giải đấu (chọn Bot đã nạp)"""
    bot_id = data.bot_id if data else None
    return TournamentService.register_participant(db, tournament_id, current_user, bot_id=bot_id)

@router.post("/{tournament_id}/unregister")
def unregister_tournament(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hủy đăng ký tham gia giải đấu (khi giải chưa bắt đầu)"""
    return TournamentService.unregister_participant(db, tournament_id, current_user)

@router.get("/{tournament_id}/requests", response_model=List[TournamentParticipantResponse])
def list_tournament_requests(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Danh sách yêu cầu đăng ký dành cho người tổ chức xem và duyệt"""
    return TournamentService.list_registration_requests(db, tournament_id, current_user)

@router.post("/{tournament_id}/requests/{request_id}/respond")
def respond_tournament_request(
    tournament_id: int,
    request_id: int,
    data: TournamentRespondRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Người tổ chức chấp nhận hoặc từ chối yêu cầu tham gia giải"""
    return TournamentService.respond_registration(
        db=db,
        tournament_id=tournament_id,
        participant_id=request_id,
        user=current_user,
        action=data.action
    )

@router.post("/{tournament_id}/start", response_model=TournamentDetailResponse)
def start_tournament(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bắt đầu giải đấu Knockout:
    - Yêu cầu tối thiểu min_participants người chơi được chấp nhận (>= 4)
    - Tự động sinh cây thi đấu (Bracket) và phân bổ đặc cách BYE cho mọi số lượng tuyển thủ N >= 4
    - Khởi tạo thời hạn 10 phút tham gia cho các trận đấu Vòng 1.
    """
    return TournamentService.start_tournament(db, tournament_id, current_user)

@router.get("/{tournament_id}/matches/{match_id}", response_model=TournamentMatchResponse)
def get_tournament_match(
    tournament_id: int,
    match_id: int,
    db: Session = Depends(get_db)
):
    """Xem chi tiết trận đấu và thời gian đếm ngược 10 phút"""
    return TournamentService.get_match_detail(db, tournament_id, match_id)

@router.post("/{tournament_id}/matches/{match_id}/join", response_model=TournamentMatchResponse)
def join_tournament_match(
    tournament_id: int,
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tuyển thủ điểm danh tham gia trận đấu trong thời hạn 10 phút:
    - Khi cả 2 tuyển thủ cùng điểm danh thành công trước thời hạn, trận đấu sẽ tự động diễn ra!
    - Nếu quá 10 phút mà vắng mặt, hệ thống sẽ tự động xử thua (FORFEIT).
    """
    return TournamentService.join_match(db, tournament_id, match_id, current_user)

@router.post("/{tournament_id}/matches/{match_id}/play", response_model=TournamentDetailResponse)
def play_tournament_match(
    tournament_id: int,
    match_id: int,
    data: PlayMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Thi đấu / Mô phỏng trận đấu trong giải (hỗ trợ chỉ định winner_id):
    - Phân định người thắng
    - Đẩy người thắng vào vòng kế tiếp
    - Nếu là trận Chung kết: vinh danh Champion và hoàn tất giải đấu!
    """
    return TournamentService.play_match(
        db=db,
        tournament_id=tournament_id,
        tournament_match_id=match_id,
        winner_id=data.winner_id
    )
