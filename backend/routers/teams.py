from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.models.team import Team
from backend.models.team_member import TeamMember
from backend.schemas.team import TeamCreate, TeamResponse, TeamMemberAdd, TeamOwnerChange, TeamDetailResponse
from backend.dependencies.auth import get_current_user
from backend.models.user import User

router = APIRouter()

@router.post("/", response_model=TeamResponse)
def create_team(team: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_team = db.query(Team).filter(Team.name == team.name).first()
    if db_team:
        raise HTTPException(status_code=400, detail="Tên đội đã tồn tại")
    new_team = Team(name=team.name, owner_id=current_user.id)
    db.add(new_team)
    db.flush()
    db.add(TeamMember(team_id=new_team.id, user_id=current_user.id, role="OWNER"))
    db.commit()
    db.refresh(new_team)
    return new_team

@router.get("/", response_model=List[TeamResponse])
def get_teams(db: Session = Depends(get_db)):
    return db.query(Team).all()

@router.get("/mine", response_model=List[TeamResponse])
def get_my_teams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Team).join(TeamMember).filter(TeamMember.user_id == current_user.id).order_by(Team.name).all()

@router.get("/{team_id}", response_model=TeamDetailResponse)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Không tìm thấy đội")
    members = (
        db.query(TeamMember, User.username)
        .join(User, User.id == TeamMember.user_id)
        .filter(TeamMember.team_id == team.id)
        .order_by(TeamMember.role.desc(), User.username)
        .all()
    )
    return {
        "id": team.id,
        "name": team.name,
        "owner_id": team.owner_id,
        "created_at": team.created_at,
        "members": [{"user_id": member.user_id, "username": username, "role": member.role} for member, username in members],
    }

@router.post("/{team_id}/members", response_model=TeamDetailResponse)
def add_team_member(
    team_id: int,
    data: TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Không tìm thấy đội")
    if team.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Chỉ chủ đội hoặc admin được quản lý thành viên")
    if not db.query(User).filter(User.id == data.user_id, User.is_active.is_(True)).first():
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản đang hoạt động")
    if db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == data.user_id).first():
        raise HTTPException(status_code=409, detail="Người chơi đã là thành viên đội")
    db.add(TeamMember(team_id=team_id, user_id=data.user_id, role="MEMBER"))
    db.commit()
    return get_team(team_id, db)

@router.delete("/{team_id}/members/{user_id}", response_model=TeamDetailResponse)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Không tìm thấy đội")
    if user_id != current_user.id and team.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Không có quyền xóa thành viên này")
    if team.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Hãy chuyển quyền chủ đội trước khi rời đội")
    member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy thành viên")
    db.delete(member)
    db.commit()
    return get_team(team_id, db)

@router.put("/{team_id}/owner", response_model=TeamDetailResponse)
def transfer_team_owner(
    team_id: int,
    data: TeamOwnerChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Không tìm thấy đội")
    if team.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Chỉ chủ đội hoặc admin được chuyển quyền")
    new_owner = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == data.user_id).first()
    if not new_owner:
        raise HTTPException(status_code=400, detail="Chủ mới phải là thành viên hiện tại của đội")
    previous_owner = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == team.owner_id).first()
    if previous_owner:
        previous_owner.role = "MEMBER"
    team.owner_id = data.user_id
    new_owner.role = "OWNER"
    db.commit()
    return get_team(team_id, db)
