from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.models.team import Team
from backend.schemas.team import TeamCreate, TeamResponse
from backend.dependencies.auth import get_current_user
from backend.models.user import User

router = APIRouter()

@router.post("/", response_model=TeamResponse)
def create_team(team: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_team = db.query(Team).filter(Team.name == team.name).first()
    if db_team:
        raise HTTPException(status_code=400, detail="Tên đội đã tồn tại")
    new_team = Team(name=team.name)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    return new_team

@router.get("/", response_model=List[TeamResponse])
def get_teams(db: Session = Depends(get_db)):
    return db.query(Team).all()
