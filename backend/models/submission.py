from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database.base import Base

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    file_path = Column(String(255), nullable=False)
    status = Column(String(50), default="PENDING")
    created_at = Column(DateTime, server_default=func.now())
