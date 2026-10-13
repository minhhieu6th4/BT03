from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database.base import Base

class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    status = Column(String(20), default="UPLOADED", nullable=False)  # UPLOADED, VALIDATING, READY, INVALID, DISABLED
    current_version_id = Column(Integer, ForeignKey("bot_versions.id", use_alter=True, name="fk_bot_current_version"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    versions = relationship("BotVersion", foreign_keys="BotVersion.bot_id", back_populates="bot", cascade="all, delete-orphan", order_by="desc(BotVersion.version_number)")
    current_version = relationship("BotVersion", foreign_keys=[current_version_id], post_update=True)


class BotVersion(Base):
    __tablename__ = "bot_versions"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    file_path = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=True)
    status = Column(String(20), default="VALIDATING", nullable=False)  # VALIDATING, READY, INVALID, DISABLED
    validation_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    bot = relationship("Bot", foreign_keys=[bot_id], back_populates="versions")
