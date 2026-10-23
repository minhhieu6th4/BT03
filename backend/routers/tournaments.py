from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.database.connection import get_db
from backend.models.user import User
from backend.schemas.tournament import (
    TournamentCreate, TournamentResponse, TournamentDetailResponse,
    TournamentParticipantResponse, TournamentMatchResponse,
    TournamentRegisterRequest, TournamentRespondRequest,
    TournamentMapCreate, TournamentMapUpdate, TournamentMapResponse,
    AssignRoundMapRequest, TournamentScheduleCreate,
    MatchConfigUpdateRequest, SetupOverviewResponse, MatchBotSelectRequest
)
from backend.dependencies.auth import get_current_user, get_optional_current_user
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
def get_tournament_details(
    tournament_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Xem chi tiết giải đấu, danh sách tuyển thủ, bản đồ và cây thi đấu (Bracket)"""
    return TournamentService.get_tournament_detail(db, tournament_id, current_user=current_user)


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

# ==============================================================
# HỆ THỐNG QUẢN LÝ MAP TÙY CHỈNH (4x4, 5x5, 6x6 & ĐÁ CẢN)
# ==============================================================

@router.post("/{tournament_id}/maps/validate")
def validate_tournament_map(
    tournament_id: int,
    data: TournamentMapCreate
):
    """Kiểm tra trước tính hợp lệ của custom map (kích thước, tọa độ đá, liên thông)"""
    return TournamentService.validate_map_candidate(data.size, data.rocks)

@router.post("/{tournament_id}/maps", response_model=TournamentMapResponse)
def create_tournament_map(
    tournament_id: int,
    data: TournamentMapCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Host tạo map mới với kích thước 4x4, 5x5 hoặc 6x6 kèm các ô đá cản"""
    return TournamentService.create_map(db, tournament_id, current_user, data)

@router.get("/{tournament_id}/maps", response_model=List[TournamentMapResponse])
def list_tournament_maps(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Danh sách các map tùy chỉnh đã tạo trong giải đấu"""
    return TournamentService.list_maps(db, tournament_id)

@router.get("/{tournament_id}/maps/{map_id}", response_model=TournamentMapResponse)
def get_tournament_map(
    tournament_id: int,
    map_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Chi tiết một map (kiểm tra quyền truy cập và thời gian công bố ở backend)"""
    return TournamentService.get_map(db, tournament_id, map_id, user=current_user)

@router.put("/{tournament_id}/maps/{map_id}", response_model=TournamentMapResponse)
def update_tournament_map(
    tournament_id: int,
    map_id: int,
    data: TournamentMapUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chỉnh sửa map trước khi bị khóa bởi trận đấu đang thi đấu"""
    return TournamentService.update_map(db, tournament_id, map_id, current_user, data)

@router.delete("/{tournament_id}/maps/{map_id}")
def delete_tournament_map(
    tournament_id: int,
    map_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa map tùy chỉnh (nếu chưa gán cho vòng đấu)"""
    return TournamentService.delete_map(db, tournament_id, map_id, current_user)

@router.post("/{tournament_id}/rounds/{round_id}/map")
def assign_round_map(
    tournament_id: int,
    round_id: int,
    data: AssignRoundMapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Host gán map và thiết lập thời điểm công bố map cho từng vòng Knockout"""
    return TournamentService.assign_round_map(
        db=db,
        tournament_id=tournament_id,
        round_id=round_id,
        user=current_user,
        map_id=data.map_id,
        map_announced_at=data.map_announced_at
    )

# ==============================================================
# HỆ THỐNG LẬP LỊCH THI ĐẤU & GIỚI HẠN TÀI NGUYÊN CHẠY BOT
# ==============================================================

@router.post("/{tournament_id}/schedule")
def create_tournament_schedule(
    tournament_id: int,
    data: TournamentScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Host thiết lập lịch thi đấu theo từng đợt và giới hạn số trận chạy đồng thời"""
    return TournamentService.create_tournament_schedule(db, tournament_id, current_user, data)

@router.get("/{tournament_id}/schedule")
def get_tournament_schedule(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Xem tiến độ lịch thi đấu, các đợt trận và số lượng trận đang thi đấu/chờ"""
    return TournamentService.get_tournament_schedule(db, tournament_id)

# ==============================================================
# HỆ THỐNG CẤU HÌNH MAP & LỊCH TỪNG TRẬN VÀ CÔNG BỐ GIẢI ĐẤU
# ==============================================================

@router.put("/{tournament_id}/matches/{match_id}/config", response_model=TournamentMatchResponse)
def configure_tournament_match(
    tournament_id: int,
    match_id: int,
    data: MatchConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Host cấu hình Map riêng và lịch thi đấu cho từng trận đấu cụ thể"""
    return TournamentService.configure_match(
        db=db,
        tournament_id=tournament_id,
        match_id=match_id,
        user=current_user,
        data=data
    )

@router.get("/{tournament_id}/setup-overview", response_model=SetupOverviewResponse)
def get_tournament_setup_overview(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xem tổng quan tiến độ cấu hình map và lịch thi đấu của tất cả các trận trong giải"""
    return TournamentService.get_setup_overview(db, tournament_id, current_user)

@router.post("/{tournament_id}/publish", response_model=TournamentDetailResponse)
def publish_tournament(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Host hoàn tất thiết lập và công bố lịch đấu cho toàn bộ người chơi/khán giả"""
    return TournamentService.publish_tournament(db, tournament_id, current_user)

@router.post("/{tournament_id}/matches/{match_id}/select-bot", response_model=TournamentMatchResponse)
def select_match_bot(
    tournament_id: int,
    match_id: int,
    data: MatchBotSelectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tuyển thủ xem map và chọn bot hợp lý trong 3 phút chuẩn bị trước khi trận đấu bắt đầu"""
    return TournamentService.select_match_bot(
        db=db,
        tournament_id=tournament_id,
        match_id=match_id,
        user=current_user,
        bot_id=data.bot_id
    )

@router.post("/{tournament_id}/matches/{match_id}/start-now", response_model=TournamentMatchResponse)
def start_match_now(
    tournament_id: int,
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bắt đầu trận đấu ngay lập tức (không cần đợi hết 3 phút chuẩn bị)"""
    return TournamentService.start_match_now(
        db=db,
        tournament_id=tournament_id,
        match_id=match_id,
        user=current_user
    )


