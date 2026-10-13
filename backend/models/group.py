from sqlalchemy import Column, Integer, String, ForeignKey  # type: ignore
from backend.database.base import Base

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    competition_id = Column(Integer, ForeignKey("competitions.id"))
