from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from typing import Optional

from backend.database.connection import get_db
from backend.dependencies.auth import get_current_user
from backend.models.match import Match
from backend.models.user import User
from backend.models.user_report import UserReport
from backend.services.notification_service import NotificationService

router = APIRouter()


class ReportCreate(BaseModel):
    reported_user_id: Optional[int] = None
    match_id: Optional[int] = None
    reason: str = Field(min_length=3, max_length=80)
    details: str = Field(min_length=10, max_length=2000)

    @model_validator(mode="after")
    def require_target(self):
        if self.reported_user_id is None and self.match_id is None:
            raise ValueError("Cần chỉ định người chơi hoặc trận đấu cần báo cáo")
        return self


@router.post("/")
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.reported_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Không thể báo cáo chính mình")
    if data.reported_user_id and not db.query(User).filter(User.id == data.reported_user_id).first():
        raise HTTPException(status_code=404, detail="Không tìm thấy người chơi")
    if data.match_id and not db.query(Match).filter(Match.id == data.match_id).first():
        raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu")
    report = UserReport(
        reporter_id=current_user.id,
        reported_user_id=data.reported_user_id,
        match_id=data.match_id,
        reason=data.reason,
        details=data.details,
    )
    db.add(report)
    for admin in db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).all():
        NotificationService.create(
            db, admin.id, "NEW_REPORT", "Báo cáo mới",
            f"{current_user.username} đã gửi báo cáo: {data.reason}.",
            "admin.html",
        )
    db.commit()
    db.refresh(report)
    return {"id": report.id, "status": report.status, "message": "Báo cáo đã được gửi tới ban quản trị."}