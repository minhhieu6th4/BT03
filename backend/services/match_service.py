from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.models.match import Match
from backend.services.judge_service import JudgeService
from backend.services.match_queue import enqueue_or_run_inline

class MatchService:
    @staticmethod
    def create_and_run_match(db: Session, red_team_id: int, blue_team_id: int):
        # 1. Tạo Match record trong MySQL
        match = Match(red_team_id=red_team_id, blue_team_id=blue_team_id, status="QUEUED")
        db.add(match)
        db.commit()
        db.refresh(match)

        try:
            job_id = enqueue_or_run_inline(
                "backend.jobs.run_legacy_match",
                (match.id, red_team_id, blue_team_id),
                lambda: JudgeService.run_match_background(match.id, red_team_id, blue_team_id),
            )
        except HTTPException:
            match.status = "FAILED"
            match.termination_reason = "Không thể đưa trận đấu vào hàng đợi"
            db.commit()
            raise
        if job_id:
            match.queue_job_id = job_id
            db.commit()
        db.refresh(match)
        return match
