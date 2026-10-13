from sqlalchemy import Column, Integer, String
from backend.database.base import Base

class RuleSet(Base):
    __tablename__ = "rule_sets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    board_size = Column(Integer, default=9)
