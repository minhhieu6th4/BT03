from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.match_service import MatchService
from backend.services.replay_service import ReplayService

router = APIRouter()

@router.post("/run")
def run_match(team_a_id: int, team_b_id: int, db: Session = Depends(get_db)):
    match = MatchService.create_and_run_match(db, team_a_id, team_b_id)
    return {"message": f"Đã lên lịch trận đấu (Match ID: {match.id}). Hệ thống đang xử lý ngầm..."}

@router.get("/")
def list_matches():
    return []

@router.get("/tree")
def get_tournament_tree():
    """Lấy danh sách phân cấp toàn bộ giải đấu từ thư mục match_logs"""
    return ReplayService.get_tournament_tree()

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


