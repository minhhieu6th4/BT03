from backend.database.connection import SessionLocal
from backend.models.match import Match
from backend.models.room import Room
from backend.models.tournament import TournamentMatch
from backend.services.judge_service import JudgeService


def run_room_match(match_id: int) -> None:
    from backend.services.room_service import RoomService

    db = SessionLocal()
    try:
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match or match.status in {"COMPLETED", "CANCELLED", "FAILED"}:
            return
        match.status = "PLAYING"
        db.commit()
        RoomService._execute_bot_match(db, match_id)
    except Exception as exc:
        db.rollback()
        match = db.query(Match).filter(Match.id == match_id).first()
        if match and match.status != "COMPLETED":
            match.status = "FAILED"
            match.termination_reason = f"Lỗi worker: {str(exc)[:200]}"
            room = db.query(Room).filter(Room.id == match.room_id).first()
            if room:
                room.status = "FAILED"
            db.commit()
        raise
    finally:
        db.close()


def run_tournament_match(tournament_match_id: int) -> None:
    from backend.services.tournament_service import TournamentService

    db = SessionLocal()
    try:
        tournament_match = db.query(TournamentMatch).filter(
            TournamentMatch.id == tournament_match_id
        ).first()
        if not tournament_match or tournament_match.status in {"COMPLETED", "FORFEIT", "FAILED"}:
            return
        tournament_match.status = "PLAYING"
        db.commit()
        TournamentService._execute_tournament_match(db, tournament_match)
    except Exception as exc:
        db.rollback()
        tournament_match = db.query(TournamentMatch).filter(
            TournamentMatch.id == tournament_match_id
        ).first()
        if tournament_match and tournament_match.status != "COMPLETED":
            tournament_match.status = "FAILED"
            tournament_match.result_reason = f"Lỗi worker: {str(exc)[:200]}"
            db.commit()
        raise
    finally:
        db.close()


def run_legacy_match(match_id: int, red_team_id: int, blue_team_id: int) -> None:
    db = SessionLocal()
    try:
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match or match.status in {"COMPLETED", "CANCELLED", "FAILED"}:
            return
        match.status = "PLAYING"
        db.commit()
        JudgeService.run_match_background(match_id, red_team_id, blue_team_id)
    except Exception as exc:
        db.rollback()
        match = db.query(Match).filter(Match.id == match_id).first()
        if match and match.status != "COMPLETED":
            match.status = "FAILED"
            match.termination_reason = f"Lỗi worker: {str(exc)[:200]}"
            db.commit()
        raise
    finally:
        db.close()