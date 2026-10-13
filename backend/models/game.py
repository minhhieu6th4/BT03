from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database.base import Base

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    log_file_path = Column(String(255), nullable=True)
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
