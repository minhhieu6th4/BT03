from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.models.team import Team
from backend.schemas.team import TeamCreate

class TeamService:
    @staticmethod
    def create_team(db: Session, team_data: TeamCreate):
        db_team = db.query(Team).filter(Team.name == team_data.name).first()
        if db_team:
            raise HTTPException(status_code=400, detail="Tên đội đã tồn tại")
        new_team = Team(name=team_data.name)
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        return new_team
        
    @staticmethod
    def get_all_teams(db: Session):
        return db.query(Team).all()
