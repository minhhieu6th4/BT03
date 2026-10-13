from sqlalchemy.orm import Session
from backend.models.competition import Competition
from backend.schemas.competition import CompetitionCreate

class CompetitionService:
    @staticmethod
    def create_competition(db: Session, comp_data: CompetitionCreate):
        comp = Competition(name=comp_data.name)
        db.add(comp)
        db.commit()
        db.refresh(comp)
        return comp
        
    @staticmethod
    def get_all_competitions(db: Session):
        return db.query(Competition).all()
