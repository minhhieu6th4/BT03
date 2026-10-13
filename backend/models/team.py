from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from backend.database.base import Base

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
