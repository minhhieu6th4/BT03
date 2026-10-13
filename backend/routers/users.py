from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.user import UserResponse
from backend.schemas.player_stat import PlayerStatResponse
from backend.dependencies.auth import get_current_user
from backend.database.connection import get_db
from backend.services.player_service import PlayerService

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin tài khoản đang đăng nhập"""
    return current_user

@router.get("/profile", response_model=PlayerStatResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy hồ sơ cá nhân của người chơi hiện tại:
    Tên, ID, Tổng số trận, Thắng, Thua, Hòa, Tổng điểm (wins*3 + draws), Thứ hạng server
    """
    return PlayerService.get_player_profile(db, current_user)

@router.get("/{user_id}/profile", response_model=PlayerStatResponse)
def get_user_profile_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Xem hồ sơ cá nhân của người chơi khác theo user_id"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người chơi")
    return PlayerService.get_player_profile(db, user)
