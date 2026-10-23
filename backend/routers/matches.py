from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from backend.database.connection import get_db
from backend.models.match import Match
from backend.models.user import User
from backend.services.match_service import MatchService
from backend.services.replay_service import ReplayService

router = APIRouter()

@router.post("/run")
def run_match(team_a_id: int, team_b_id: int, db: Session = Depends(get_db)):
    match = MatchService.create_and_run_match(db, team_a_id, team_b_id)
    return {
        "message": f"Đã xếp trận đấu #{match.id} vào hàng đợi.",
        "match_id": match.id,
        "status": match.status,
        "job_id": match.queue_job_id,
    }

@router.get("/")
def list_matches(
    db: Session = Depends(get_db),
    player_id: int = Query(None, ge=1),
    username: str = Query(None, min_length=1, max_length=50),
    status: str = Query(None, min_length=1, max_length=50),
    match_type: str = Query(None, min_length=1, max_length=20),
    result: str = Query(None, pattern="^(win|loss|draw)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    query = db.query(Match)
    if player_id is not None:
        query = query.filter(or_(Match.red_user_id == player_id, Match.blue_user_id == player_id))
    if username:
        pattern = f"%{username.strip()}%"
        query = query.filter(
            or_(
                Match.red_user.has(User.username.ilike(pattern)),
                Match.blue_user.has(User.username.ilike(pattern)),
            )
        )
    if status:
        query = query.filter(Match.status == status.upper())
    if match_type:
        query = query.filter(Match.match_type == match_type.upper())
    if result:
        if player_id is None:
            raise HTTPException(status_code=400, detail="player_id là bắt buộc khi lọc theo kết quả")
        query = query.filter(Match.status == "COMPLETED")
        if result == "draw":
            query = query.filter(Match.is_draw.is_(True))
        elif result == "win":
            query = query.filter(Match.winner_user_id == player_id)
        else:
            query = query.filter(
                Match.winner_user_id.is_not(None), Match.winner_user_id != player_id
            )

    total = query.count()
    matches = query.order_by(desc(Match.created_at), desc(Match.id)).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "id": match.id,
                "match_type": match.match_type,
                "status": match.status,
                "created_at": match.created_at,
                "red_user_id": match.red_user_id,
                "red_username": match.red_user.username if match.red_user else None,
                "red_bot_id": match.red_bot_id,
                "red_bot_name": match.red_bot.name if match.red_bot else None,
                "blue_user_id": match.blue_user_id,
                "blue_username": match.blue_user.username if match.blue_user else None,
                "blue_bot_id": match.blue_bot_id,
                "blue_bot_name": match.blue_bot.name if match.blue_bot else None,
                "winner_user_id": match.winner_user_id,
                "is_draw": match.is_draw,
                "termination_reason": match.termination_reason,
                "total_turns": match.total_turns,
            }
            for match in matches
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }

@router.get("/tree")
def get_tournament_tree():
    """Lấy danh sách phân cấp toàn bộ giải đấu từ thư mục match_logs"""
    return ReplayService.get_tournament_tree()

@router.get("/{match_id}/status")
def get_match_status(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Trận đấu không tồn tại")
    return {
        "match_id": match.id,
        "status": match.status,
        "job_id": match.queue_job_id,
        "termination_reason": match.termination_reason,
        "total_turns": match.total_turns,
        "winner_user_id": match.winner_user_id,
        "is_draw": match.is_draw,
    }

@router.get("/game/{game_id}/replay")
def get_game_replay(game_id: str):
    data = ReplayService.get_replay_data(game_id)
    if data:
        return data
    raise HTTPException(status_code=404, detail=f"Replay cho trận {game_id} chưa tồn tại hoặc đang chạy.")

@router.get("/replay-by-path")
def get_game_replay_by_path(path: str = Query(..., description="Đường dẫn tương đối tới file game (VD: qualification/group_01/match_0001/game_01.json)")):
    data = ReplayService.get_replay_by_path(path)
    if data:
        return data
    raise HTTPException(status_code=404, detail=f"Không tìm thấy file replay: {path}")

@router.get("/{match_id}/replay")
def get_match_replay(match_id: int, db: Session = Depends(get_db)):
    """Lấy dữ liệu replay của trận đấu đã lưu trong MySQL/SQLite"""
    import json
    from backend.models.match import Match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Trận đấu không tồn tại")

    initial_board = json.loads(match.initial_board_json) if match.initial_board_json else []
    moves = json.loads(match.moves_json) if match.moves_json else []

    return {
        "match_id": match.id,
        "status": match.status,
        "red_team": match.red_user.username if match.red_user else "Red Player",
        "blue_team": match.blue_user.username if match.blue_user else "Blue Player",
        "red_bot": match.red_bot.name if match.red_bot else "Bot Red",
        "blue_bot": match.blue_bot.name if match.blue_bot else "Bot Blue",
        "winner_user_id": match.winner_user_id,
        "is_draw": match.is_draw,
        "reason": match.termination_reason,
        "total_turns": match.total_turns,
        "initial_board": initial_board,
        "moves": moves
    }


