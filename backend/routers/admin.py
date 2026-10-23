from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.dependencies.permissions import get_current_admin
from backend.models.match import Match
from backend.models.tournament import Tournament
from backend.models.user import User
from backend.models.user_report import UserReport
from backend.services.notification_service import NotificationService

router = APIRouter()


class ReportUpdate(BaseModel):
    status: str = Field(pattern="^(IN_REVIEW|RESOLVED|DISMISSED)$")
    admin_note: str = Field(default="", max_length=2000)


class AccountStatusUpdate(BaseModel):
    is_active: bool


@router.get("/reports")
def list_reports(
    status: str = Query("OPEN", pattern="^(OPEN|IN_REVIEW|RESOLVED|DISMISSED|ALL)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    query = db.query(UserReport)
    if status != "ALL":
        query = query.filter(UserReport.status == status)
    reports = query.order_by(UserReport.created_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": report.id,
            "reporter_id": report.reporter_id,
            "reported_user_id": report.reported_user_id,
            "match_id": report.match_id,
            "reason": report.reason,
            "details": report.details,
            "status": report.status,
            "admin_note": report.admin_note,
            "created_at": report.created_at,
            "resolved_at": report.resolved_at,
        }
        for report in reports
    ]


@router.patch("/reports/{report_id}")
def update_report(
    report_id: int,
    data: ReportUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    report = db.query(UserReport).filter(UserReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo")
    report.status = data.status
    report.admin_note = data.admin_note
    report.resolved_at = datetime.utcnow() if data.status in {"RESOLVED", "DISMISSED"} else None
    NotificationService.create(
        db, report.reporter_id, "REPORT_UPDATED", "Báo cáo đã được cập nhật",
        f"Báo cáo #{report.id} hiện ở trạng thái {report.status}.",
        "profile.html",
    )
    db.commit()
    return {"id": report.id, "status": report.status}


@router.get("/users")
def list_users(
    search: str = Query("", max_length=50),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    query = db.query(User)
    if search.strip():
        query = query.filter(User.username.ilike(f"%{search.strip()}%"))
    return [
        {"id": user.id, "username": user.username, "email": user.email,
         "is_admin": user.is_admin, "is_active": user.is_active,
         "email_verified": user.email_verified, "created_at": user.created_at}
        for user in query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    ]


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    data: AccountStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    if user.id == admin.id and not data.is_active:
        raise HTTPException(status_code=400, detail="Không thể tự vô hiệu hóa tài khoản admin đang dùng")
    user.is_active = data.is_active
    if not data.is_active:
        NotificationService.create(
            db, user.id, "ACCOUNT_DISABLED", "Tài khoản đã bị vô hiệu hóa",
            "Bạn không thể đăng nhập hoặc sử dụng API cần xác thực khi tài khoản bị khóa.",
        )
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.get("/tournaments")
def monitor_tournaments(
    status: str = Query("ALL", max_length=20),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    query = db.query(Tournament)
    if status.upper() != "ALL":
        query = query.filter(Tournament.status == status.upper())
    return [
        {"id": item.id, "name": item.name, "status": item.status,
         "creator_id": item.creator_id,
         "creator_name": item.creator.username if item.creator else None,
         "champion_id": item.champion_id, "created_at": item.created_at}
        for item in query.order_by(Tournament.created_at.desc()).all()
    ]


@router.get("/matches")
def monitor_matches(
    status: str = Query("ALL", max_length=50),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    query = db.query(Match)
    if status.upper() != "ALL":
        query = query.filter(Match.status == status.upper())
    return [
        {"id": match.id, "status": match.status, "match_type": match.match_type,
         "red_user_id": match.red_user_id, "blue_user_id": match.blue_user_id,
         "winner_user_id": match.winner_user_id, "is_draw": match.is_draw,
         "created_at": match.created_at, "termination_reason": match.termination_reason}
        for match in query.order_by(Match.created_at.desc()).offset(offset).limit(limit).all()
    ]