from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database.base import Base

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    
    # Mode và quan hệ
    match_type = Column(String(20), default="REGULAR", nullable=False) # REGULAR, TOURNAMENT
    room_id = Column(Integer, nullable=True)
    
    # Đấu theo đội (Legacy)
    red_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    blue_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    # Đấu theo cá nhân người chơi (User vs User)
    red_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    blue_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    winner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_draw = Column(Boolean, default=False, nullable=False)

    # Bot tham gia thi đấu
    red_bot_id = Column(Integer, ForeignKey("bots.id"), nullable=True)
    blue_bot_id = Column(Integer, ForeignKey("bots.id"), nullable=True)
    red_bot_version_id = Column(Integer, ForeignKey("bot_versions.id"), nullable=True)
    blue_bot_version_id = Column(Integer, ForeignKey("bot_versions.id"), nullable=True)

    # Kết quả chi tiết và replay
    termination_reason = Column(String(255), nullable=True)
    moves_json = Column(Text().with_variant(LONGTEXT, "mysql"), nullable=True)
    initial_board_json = Column(Text().with_variant(LONGTEXT, "mysql"), nullable=True)
    total_turns = Column(Integer, default=0)
    
    # Cờ bảo đảm tính bất biến (Idempotent), tránh cộng điểm 2 lần
    points_awarded = Column(Boolean, default=False, nullable=False)

    status = Column(String(50), default="PENDING") # PENDING, PLAYING, COMPLETED, CANCELLED
    created_at = Column(DateTime, server_default=func.now())

    red_user = relationship("User", foreign_keys=[red_user_id])
    blue_user = relationship("User", foreign_keys=[blue_user_id])
    winner_user = relationship("User", foreign_keys=[winner_user_id])
    red_bot = relationship("Bot", foreign_keys=[red_bot_id])
    blue_bot = relationship("Bot", foreign_keys=[blue_bot_id])
    red_bot_version = relationship("BotVersion", foreign_keys=[red_bot_version_id])
    blue_bot_version = relationship("BotVersion", foreign_keys=[blue_bot_version_id])
