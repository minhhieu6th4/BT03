from sqlalchemy import Column, Integer, ForeignKey
from backend.database.base import Base

class Ranking(Base):
    __tablename__ = "rankings"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    score = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
