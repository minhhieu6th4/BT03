from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.user import UserResponse, UserUpdate
from backend.schemas.player_stat import PlayerStatResponse
from backend.dependencies.auth import get_current_user
from backend.database.connection import get_db
from backend.services.player_service import PlayerService
from backend.models.match import Match
from backend.models.tournament import TournamentMatch, Tournament

router = APIRouter()

@router.patch("/me", response_model=UserResponse)
def update_users_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.username and data.username != current_user.username:
        if db.query(User).filter(User.username == data.username).first():
            raise HTTPException(status_code=409, detail="Username đã được sử dụng")
        current_user.username = data.username
    if data.email and data.email != current_user.email:
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status_code=409, detail="Email đã được sử dụng")
        current_user.email = data.email
        current_user.email_verified = False
    db.commit()
    db.refresh(current_user)
    return current_user

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

@router.get("/me/match-stats")
def get_current_user_match_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    matches = db.query(Match).filter(
        Match.status == "COMPLETED",
        ((Match.red_user_id == current_user.id) | (Match.blue_user_id == current_user.id)),
    ).all()
    bot_stats = {}
    for match in matches:
        bot_id = match.red_bot_id if match.red_user_id == current_user.id else match.blue_bot_id
        if not bot_id:
            continue
        summary = bot_stats.setdefault(bot_id, {"bot_id": bot_id, "matches": 0, "wins": 0, "draws": 0, "losses": 0})
        summary["matches"] += 1
        if match.is_draw:
            summary["draws"] += 1
        elif match.winner_user_id == current_user.id:
            summary["wins"] += 1
        else:
            summary["losses"] += 1

    from backend.models.bot import Bot
    for bot_id, summary in bot_stats.items():
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        summary["bot_name"] = bot.name if bot else f"Bot {bot_id}"

    tournament_matches = db.query(TournamentMatch, Tournament.name).join(
        Tournament, Tournament.id == TournamentMatch.tournament_id
    ).filter(
        ((TournamentMatch.player1_id == current_user.id) | (TournamentMatch.player2_id == current_user.id)),
        TournamentMatch.status.in_(["COMPLETED", "FORFEIT"]),
    ).all()
    tournament_stats = {}
    for match, tournament_name in tournament_matches:
        summary = tournament_stats.setdefault(match.tournament_id, {
            "tournament_id": match.tournament_id, "tournament_name": tournament_name,
            "matches": 0, "wins": 0, "losses": 0,
        })
        summary["matches"] += 1
        if match.winner_id == current_user.id:
            summary["wins"] += 1
        else:
            summary["losses"] += 1
    return {
        "by_bot": sorted(bot_stats.values(), key=lambda item: item["matches"], reverse=True),
        "by_tournament": sorted(tournament_stats.values(), key=lambda item: item["matches"], reverse=True),
    }

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
