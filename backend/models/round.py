from sqlalchemy import Column, Integer, String, ForeignKey
from backend.database.base import Base

class Round(Base):
    __tablename__ = "rounds"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    competition_id = Column(Integer, ForeignKey("competitions.id"))
