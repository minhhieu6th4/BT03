from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database.base import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(100), default="Phòng thách đấu", nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    player1_ready = Column(Boolean, default=False, nullable=False)
    player2_ready = Column(Boolean, default=False, nullable=False)
    player1_bot_id = Column(Integer, ForeignKey("bots.id"), nullable=True)
    player2_bot_id = Column(Integer, ForeignKey("bots.id"), nullable=True)
    player1_bot_version_id = Column(Integer, ForeignKey("bot_versions.id"), nullable=True)
    player2_bot_version_id = Column(Integer, ForeignKey("bot_versions.id"), nullable=True)
    status = Column(String(20), default="WAITING", nullable=False)  # WAITING, READY, PLAYING, FINISHED, CANCELLED
    current_match_id = Column(Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    player1 = relationship("User", foreign_keys=[player1_id])
    player2 = relationship("User", foreign_keys=[player2_id])
    player1_bot = relationship("Bot", foreign_keys=[player1_bot_id])
    player2_bot = relationship("Bot", foreign_keys=[player2_bot_id])
    player1_bot_version = relationship("BotVersion", foreign_keys=[player1_bot_version_id])
    player2_bot_version = relationship("BotVersion", foreign_keys=[player2_bot_version_id])
    current_match = relationship("Match", foreign_keys=[current_match_id])
    join_requests = relationship("RoomJoinRequest", back_populates="room", cascade="all, delete-orphan")


class RoomJoinRequest(Base):
    __tablename__ = "room_join_requests"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING, ACCEPTED, REJECTED
    created_at = Column(DateTime, server_default=func.now())

    room = relationship("Room", back_populates="join_requests")
    user = relationship("User")
