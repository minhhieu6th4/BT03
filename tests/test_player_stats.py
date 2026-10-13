import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.base import Base
from backend.models.user import User
from backend.models.match import Match
from backend.models.player_stat import PlayerStat
from backend.services.player_service import PlayerService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_player_stats_points_formula(db_session):
    u1 = User(username="player1", email="p1@test.com", hashed_password="pwd")
    u2 = User(username="player2", email="p2@test.com", hashed_password="pwd")
    db_session.add_all([u1, u2])
    db_session.commit()

    stat1 = PlayerService.get_or_create_stats(db_session, u1.id)
    stat2 = PlayerService.get_or_create_stats(db_session, u2.id)

    # Win match
    m1 = Match(match_type="REGULAR", red_user_id=u1.id, blue_user_id=u2.id, status="PLAYING")
    db_session.add(m1)
    db_session.commit()

    PlayerService.record_match_result(db_session, m1, winner_user_id=u1.id)

    assert stat1.wins == 1
    assert stat1.losses == 0
    assert stat1.total_points == 3 # 1 win * 3 + 0 draws = 3
    assert stat2.wins == 0
    assert stat2.losses == 1
    assert stat2.total_points == 0

    # Draw match
    m2 = Match(match_type="REGULAR", red_user_id=u1.id, blue_user_id=u2.id, status="PLAYING")
    db_session.add(m2)
    db_session.commit()

    PlayerService.record_match_result(db_session, m2, is_draw=True)

    assert stat1.wins == 1
    assert stat1.draws == 1
    assert stat1.total_points == 4 # 1*3 + 1 = 4
    assert stat1.total_matches == 2

    assert stat2.wins == 0
    assert stat2.draws == 1
    assert stat2.losses == 1
    assert stat2.total_points == 1 # 0*3 + 1 = 1
    assert stat2.total_matches == 2

def test_idempotent_scoring(db_session):
    """Đảm bảo gọi hàm tính điểm nhiều lần trên cùng 1 trận không bị cộng điểm 2 lần"""
    u1 = User(username="alice", email="alice@test.com", hashed_password="pwd")
    u2 = User(username="bob", email="bob@test.com", hashed_password="pwd")
    db_session.add_all([u1, u2])
    db_session.commit()

    m = Match(match_type="REGULAR", red_user_id=u1.id, blue_user_id=u2.id, status="PLAYING")
    db_session.add(m)
    db_session.commit()

    # Lần 1: Thắng
    PlayerService.record_match_result(db_session, m, winner_user_id=u1.id)
    stat1 = PlayerService.get_or_create_stats(db_session, u1.id)
    assert stat1.total_points == 3
    assert m.points_awarded == True

    # Lần 2: Gọi lại (xử lý lại do retry / webhook)
    PlayerService.record_match_result(db_session, m, winner_user_id=u1.id)
    assert stat1.total_points == 3 # Vẫn là 3, không bị thành 6!
    assert stat1.wins == 1

def test_server_leaderboard_sorting(db_session):
    """Bảng xếp hạng server sắp xếp theo: total_points DESC, wins DESC"""
    u1 = User(username="p_low", email="l@test.com", hashed_password="pwd")
    u2 = User(username="p_mid", email="m@test.com", hashed_password="pwd")
    u3 = User(username="p_high", email="h@test.com", hashed_password="pwd")
    db_session.add_all([u1, u2, u3])
    db_session.commit()

    s1 = PlayerService.get_or_create_stats(db_session, u1.id)
    s1.wins = 1
    s1.recalculate() # 3 points

    s2 = PlayerService.get_or_create_stats(db_session, u2.id)
    s2.draws = 4
    s2.recalculate() # 4 points

    s3 = PlayerService.get_or_create_stats(db_session, u3.id)
    s3.wins = 3
    s3.recalculate() # 9 points
    db_session.commit()

    leaderboard = PlayerService.get_server_leaderboard(db_session)
    assert leaderboard[0].username == "p_high"
    assert leaderboard[0].rank == 1
    assert leaderboard[1].username == "p_mid"
    assert leaderboard[1].rank == 2
    assert leaderboard[2].username == "p_low"
    assert leaderboard[2].rank == 3
