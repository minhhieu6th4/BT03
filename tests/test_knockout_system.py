import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from backend.database.base import Base
from backend.models.user import User
from backend.models.tournament import Tournament, TournamentParticipant, TournamentRound, TournamentMatch
from backend.services.tournament_service import TournamentService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_tournament_minimum_4_participants(db_session):
    creator = User(username="admin", email="admin@test.com", hashed_password="pwd")
    db_session.add(creator)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, creator, "Giải Mùa Xuân", "Giải đấu thử nghiệm")
    
    # Chỉ đăng ký 3 người
    users = [User(username=f"p{i}", email=f"p{i}@test.com", hashed_password="pwd") for i in range(1, 4)]
    db_session.add_all(users)
    db_session.commit()

    for u in users:
        TournamentService.register_participant(db_session, t.id, u)

    # Thử bắt đầu giải với 3 người -> phải ném lỗi 400
    with pytest.raises(HTTPException) as exc:
        TournamentService.start_tournament(db_session, t.id, creator)
    assert "tối thiểu 4" in str(exc.value.detail).lower()

def test_tournament_knockout_with_4_participants(db_session):
    creator = User(username="admin4", email="a4@test.com", hashed_password="pwd")
    users = [User(username=f"u4_{i}", email=f"u4_{i}@test.com", hashed_password="pwd") for i in range(1, 5)]
    db_session.add_all([creator] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, creator, "Giải 4 Đội")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u)

    detail = TournamentService.start_tournament(db_session, t.id, creator)
    assert detail.tournament.status == "IN_PROGRESS"
    # Với N=4: Bracket size = 4 -> 2 vòng đấu (Bán kết và Chung kết)
    assert len(detail.rounds) == 2
    assert detail.rounds[0].round_name == "Bán kết"
    assert detail.rounds[1].round_name == "Chung kết"
    assert len(detail.rounds[0].matches) == 2
    assert len(detail.rounds[1].matches) == 1

def test_tournament_knockout_with_bye_odd_participants(db_session):
    """Kiểm tra thuật toán xử lý đặc cách BYE cho số lượng tuyển thủ không phải lũy thừa của 2 (N=5, 6)"""
    creator = User(username="admin5", email="a5@test.com", hashed_password="pwd")
    users = [User(username=f"u5_{i}", email=f"u5_{i}@test.com", hashed_password="pwd") for i in range(1, 6)]
    db_session.add_all([creator] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, creator, "Giải 5 Đội")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u)

    detail = TournamentService.start_tournament(db_session, t.id, creator)
    assert detail.tournament.status == "IN_PROGRESS"
    # Với N=5: Bracket size = 8 (2^3 = 8), 3 vòng đấu: Tứ kết, Bán kết, Chung kết
    assert len(detail.rounds) == 3
    # Số BYE = 8 - 5 = 3
    round1_matches = detail.rounds[0].matches
    byes = [m for m in round1_matches if m.is_bye]
    assert len(byes) == 3
    for b in byes:
        assert b.status == "COMPLETED"
        assert b.winner_id is not None # Hạt giống BYE tự động thắng và tiến vào vòng 2

def test_tournament_progression_to_champion(db_session):
    """Kiểm tra toàn bộ luồng thi đấu tiến từ vòng 1 đến khi tìm ra Nhà Vô Địch"""
    creator = User(username="admin_prog", email="aprog@test.com", hashed_password="pwd")
    users = [User(username=f"champ_{i}", email=f"champ_{i}@test.com", hashed_password="pwd") for i in range(1, 5)]
    db_session.add_all([creator] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, creator, "Giải Tiến Đến Vô Địch")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u)

    detail = TournamentService.start_tournament(db_session, t.id, creator)

    # Thi đấu Bán kết trận 1
    m1 = detail.rounds[0].matches[0]
    detail = TournamentService.play_match(db_session, t.id, m1.id, winner_id=m1.player1_id)

    # Thi đấu Bán kết trận 2
    m2 = detail.rounds[0].matches[1]
    detail = TournamentService.play_match(db_session, t.id, m2.id, winner_id=m2.player1_id)

    # Kiểm tra trận Chung kết đã có 2 người thắng từ bán kết
    final_match = detail.rounds[1].matches[0]
    assert final_match.player1_id == m1.player1_id
    assert final_match.player2_id == m2.player1_id

    # Thi đấu trận Chung kết!
    detail = TournamentService.play_match(db_session, t.id, final_match.id, winner_id=final_match.player1_id)

    # Kiểm tra giải đấu hoàn tất và xác định Nhà Vô Địch
    assert detail.tournament.status == "COMPLETED"
    assert detail.tournament.champion_id == final_match.player1_id

def test_registration_approval_flow(db_session):
    """Kiểm tra quy trình đăng ký, duyệt và từ chối tuyển thủ của người tổ chức"""
    from datetime import datetime
    creator = User(username="organizer", email="org@test.com", hashed_password="pwd")
    intruder = User(username="intruder", email="int@test.com", hashed_password="pwd")
    users = [User(username=f"reg_{i}", email=f"reg_{i}@test.com", hashed_password="pwd") for i in range(1, 6)]
    db_session.add_all([creator, intruder] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, creator, "Giải Duyệt Tuyển Thủ", min_participants=4, max_participants=4)

    # 4 tuyển thủ đầu đăng ký -> trạng thái PENDING
    for u in users[:4]:
        res = TournamentService.register_participant(db_session, t.id, u)
        assert res["status"] == "PENDING"

    # Người lạ không có quyền duyệt
    requests = TournamentService.list_registration_requests(db_session, t.id, creator)
    assert len(requests) == 4
    with pytest.raises(HTTPException) as exc:
        TournamentService.respond_registration(db_session, t.id, requests[0].id, intruder, "ACCEPTED")
    assert exc.value.status_code == 403

    # Người tổ chức duyệt 4 tuyển thủ
    for req in requests:
        res = TournamentService.respond_registration(db_session, t.id, req.id, creator, "ACCEPTED")
        assert res["status"] == "ACCEPTED"

    # Tuyển thủ thứ 5 đăng ký -> Từ chối vì vượt quá max_participants hoặc người tổ chức reject
    res5 = TournamentService.register_participant(db_session, t.id, users[4])
    assert res5["status"] == "PENDING"
    p5 = db_session.query(TournamentParticipant).filter(TournamentParticipant.tournament_id == t.id, TournamentParticipant.user_id == users[4].id).first()
    # Thử accept khi đã đạt max 4 -> lỗi 400
    with pytest.raises(HTTPException) as exc:
        TournamentService.respond_registration(db_session, t.id, p5.id, creator, "ACCEPTED")
    assert "tối đa" in str(exc.value.detail).lower()

    # Reject tuyển thủ 5
    rej_res = TournamentService.respond_registration(db_session, t.id, p5.id, creator, "REJECTED")
    assert rej_res["status"] == "REJECTED"


    # Bắt đầu giải đấu với 4 người đã duyệt
    detail = TournamentService.start_tournament(db_session, t.id, creator)
    assert detail.tournament.status == "IN_PROGRESS"
    assert len(detail.participants) == 5
    # Các trận vòng 1 được tạo ở trạng thái READY với thời hạn 10 phút
    for m in detail.rounds[0].matches:
        assert m.status == "READY"
        assert m.participation_deadline is not None

def test_match_checkin_and_single_forfeit(db_session):
    """Kiểm tra thời hạn 10 phút và xử thua (FORFEIT - NO_SHOW) khi một tuyển thủ vắng mặt"""
    from datetime import datetime, timedelta
    creator = User(username="org_deadline", email="orgd@test.com", hashed_password="pwd")
    users = [User(username=f"pl_{i}", email=f"pl_{i}@test.com", hashed_password="pwd") for i in range(1, 5)]
    db_session.add_all([creator] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, creator, "Giải Hạn Giờ 10 Phút")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u, auto_accept=True)

    detail = TournamentService.start_tournament(db_session, t.id, creator)
    match1 = detail.rounds[0].matches[0]
    p1 = db_session.query(User).filter(User.id == match1.player1_id).first()
    p2 = db_session.query(User).filter(User.id == match1.player2_id).first()

    # Tuyển thủ 1 bấm Tham gia thi đấu
    m_res = TournamentService.join_match(db_session, t.id, match1.id, p1)
    assert m_res.player1_joined_at is not None
    assert m_res.player2_joined_at is None
    assert m_res.status == "READY"

    # Giả lập quá thời hạn 10 phút (tua ngược thời gian deadline)
    m_db = db_session.query(TournamentMatch).filter(TournamentMatch.id == match1.id).first()
    m_db.participation_deadline = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    # Kích hoạt kiểm tra hạn chót
    TournamentService.check_tournament_deadlines(db_session, t.id)

    db_session.refresh(m_db)
    # Tuyển thủ 2 không tham gia nên bị xử thua FORFEIT - NO_SHOW, tuyển thủ 1 thắng
    assert m_db.status == "FORFEIT"
    assert m_db.result_reason == "NO_SHOW"
    assert m_db.winner_id == p1.id

    # Tuyển thủ 1 phải được tiến vào Chung kết
    detail_after = TournamentService.get_tournament_detail(db_session, t.id)
    final_m = detail_after.rounds[1].matches[0]
    assert final_m.player1_id == p1.id

def test_match_double_forfeit_and_champion(db_session):
    """Kiểm tra trường hợp cả hai tuyển thủ đều vắng mặt (DOUBLE_NO_SHOW) và nhánh sau nhận BYE"""
    from datetime import datetime, timedelta
    creator = User(username="org_double", email="orgdouble@test.com", hashed_password="pwd")
    users = [User(username=f"df_{i}", email=f"df_{i}@test.com", hashed_password="pwd") for i in range(1, 5)]
    db_session.add_all([creator] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, creator, "Giải Double Forfeit")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u, auto_accept=True)

    detail = TournamentService.start_tournament(db_session, t.id, creator)
    m1 = detail.rounds[0].matches[0]
    m2 = detail.rounds[0].matches[1]

    # Trận 1: Player 1 điểm danh, Player 2 vắng mặt
    p1 = db_session.query(User).filter(User.id == m1.player1_id).first()
    TournamentService.join_match(db_session, t.id, m1.id, p1)

    # Cả hai trận đều hết hạn 10 phút
    m1_db = db_session.query(TournamentMatch).filter(TournamentMatch.id == m1.id).first()
    m2_db = db_session.query(TournamentMatch).filter(TournamentMatch.id == m2.id).first()
    m1_db.participation_deadline = datetime.utcnow() - timedelta(seconds=5)
    m2_db.participation_deadline = datetime.utcnow() - timedelta(seconds=5)
    db_session.commit()

    # Kiểm tra hạn chót
    detail_after = TournamentService.get_tournament_detail(db_session, t.id)

    # Trận 1: Player 1 thắng do đối thủ vắng
    db_session.refresh(m1_db)
    assert m1_db.status == "FORFEIT"
    assert m1_db.winner_id == p1.id

    # Trận 2: Cả 2 cùng vắng -> DOUBLE_NO_SHOW
    db_session.refresh(m2_db)
    assert m2_db.status == "FORFEIT"
    assert m2_db.result_reason == "DOUBLE_NO_SHOW"
    assert m2_db.winner_id is None

    # Do trận 2 không có ai đi tiếp, Player 1 ở trận Chung kết nhận suất BYE và vô địch luôn!
    final_db = db_session.query(TournamentMatch).filter(
        TournamentMatch.round_id == detail_after.rounds[1].id
    ).first()
    assert final_db.is_bye is True
    assert final_db.winner_id == p1.id
    t_db = db_session.query(Tournament).filter(Tournament.id == t.id).first()
    assert t_db.status == "COMPLETED"
    assert t_db.champion_id == p1.id

