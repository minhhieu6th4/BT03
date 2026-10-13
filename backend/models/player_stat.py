from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database.base import Base

class PlayerStat(Base):
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    total_matches = Column(Integer, default=0, nullable=False)
    wins = Column(Integer, default=0, nullable=False)
    draws = Column(Integer, default=0, nullable=False)
    losses = Column(Integer, default=0, nullable=False)
    total_points = Column(Integer, default=0, nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="stats")

    def recalculate(self):
        """Tính lại tổng số trận và tổng điểm: wins*3 + draws"""
        self.total_matches = self.wins + self.draws + self.losses
        self.total_points = self.wins * 3 + self.draws
