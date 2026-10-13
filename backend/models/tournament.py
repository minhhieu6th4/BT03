from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database.base import Base

class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), default="")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    min_participants = Column(Integer, default=4, nullable=False)
    max_participants = Column(Integer, default=32, nullable=False)
    status = Column(String(20), default="REGISTRATION_OPEN", nullable=False) # REGISTRATION_OPEN, IN_PROGRESS, COMPLETED, CANCELLED
    champion_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    creator = relationship("User", foreign_keys=[creator_id])
    champion = relationship("User", foreign_keys=[champion_id])
    participants = relationship("TournamentParticipant", back_populates="tournament", cascade="all, delete-orphan")
    rounds = relationship("TournamentRound", back_populates="tournament", cascade="all, delete-orphan", order_by="TournamentRound.round_number")


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="PENDING", nullable=False) # PENDING, ACCEPTED, REJECTED, CANCELLED
    seed = Column(Integer, default=0)
    registered_at = Column(DateTime, server_default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    tournament = relationship("Tournament", back_populates="participants")
    user = relationship("User", foreign_keys=[user_id])
    bot = relationship("Bot", foreign_keys=[bot_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])


class TournamentRound(Base):
    __tablename__ = "tournament_rounds"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False) # 1, 2, 3...
    round_name = Column(String(50), nullable=False) # Vòng 1, Tứ kết, Bán kết, Chung kết
    status = Column(String(20), default="PENDING", nullable=False) # PENDING, IN_PROGRESS, COMPLETED

    tournament = relationship("Tournament", back_populates="rounds")
    matches = relationship("TournamentMatch", back_populates="round", cascade="all, delete-orphan", order_by="TournamentMatch.match_order")


class TournamentMatch(Base):
    __tablename__ = "tournament_matches"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    round_id = Column(Integer, ForeignKey("tournament_rounds.id", ondelete="CASCADE"), nullable=False, index=True)
    match_order = Column(Integer, nullable=False)
    player1_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    player1_bot_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    player2_bot_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_bye = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default="WAITING", nullable=False) # WAITING, READY, PLAYING, COMPLETED, FORFEIT, CANCELLED
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)

    # 10-Minute Participation Deadline & Check-in
    ready_at = Column(DateTime, nullable=True)
    participation_deadline = Column(DateTime, nullable=True)
    player1_joined_at = Column(DateTime, nullable=True)
    player2_joined_at = Column(DateTime, nullable=True)
    result_reason = Column(String(255), nullable=True)

    round = relationship("TournamentRound", back_populates="matches")
    player1 = relationship("User", foreign_keys=[player1_id])
    player2 = relationship("User", foreign_keys=[player2_id])
    player1_bot = relationship("Bot", foreign_keys=[player1_bot_id])
    player2_bot = relationship("Bot", foreign_keys=[player2_bot_id])
    winner = relationship("User", foreign_keys=[winner_id])
    match = relationship("Match")

