import threading
from sqlalchemy.orm import Session
from backend.models.match import Match
from backend.services.judge_service import JudgeService

class MatchService:
    @staticmethod
    def create_and_run_match(db: Session, red_team_id: int, blue_team_id: int):
        # 1. Tạo Match record trong MySQL
        match = Match(red_team_id=red_team_id, blue_team_id=blue_team_id, status="RUNNING")
        db.add(match)
        db.commit()
        db.refresh(match)
        
        # 2. Bắn luồng background để chạy Sandbox, tránh block API
        thread = threading.Thread(target=JudgeService.run_match_background, args=(match.id, red_team_id, blue_team_id))
        thread.start()
        
        return match
