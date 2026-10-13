from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.database.connection import get_db
from backend.schemas.player_stat import ServerLeaderboardEntry
from backend.services.player_service import PlayerService

router = APIRouter()

@router.get("/", response_model=List[ServerLeaderboardEntry])
@router.get("/server", response_model=List[ServerLeaderboardEntry])
def get_server_leaderboard(db: Session = Depends(get_db)):
    """
    Bảng xếp hạng toàn server (Cá nhân người chơi):
    - Tiêu chí: total_points DESC, wins DESC, id ASC
    - Hiển thị: rank, tên người chơi, số trận đã đấu, thắng, hòa, thua và tổng điểm
    - Chỉ tính các trận đấu thường hợp lệ đã hoàn thành
    """
    return PlayerService.get_server_leaderboard(db)
