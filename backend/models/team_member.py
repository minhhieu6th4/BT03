from sqlalchemy import Column, Integer, String, ForeignKey
from backend.database.base import Base

class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20), default="MEMBER", nullable=False)
