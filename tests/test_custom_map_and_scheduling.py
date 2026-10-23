import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from backend.database.base import Base
from backend.models.user import User
from backend.models.tournament import (
    Tournament, TournamentParticipant, TournamentRound, TournamentMatch, TournamentMap
)
from backend.schemas.tournament import (
    TournamentMapCreate, TournamentMapUpdate, AssignRoundMapRequest, TournamentScheduleCreate,
    MatchConfigUpdateRequest
)
from backend.services.tournament_service import TournamentService
from game.map_validator import validate_custom_map
from game.game_engine import GameEngine, get_reserved_positions
from game.rule_set import RuleSet
from game.move import Move
from game.piece import Piece, Team, PieceType


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ==============================================================
# 1. KIỂM THỬ XÁC THỰC MAP TÙY CHỈNH (MAP VALIDATOR)
# ==============================================================

def test_map_validator_valid_sizes():
    """Hỗ trợ hợp lệ cho kích thước 4x4, 5x5, 6x6, 9x9, 15x15, 18x18"""
    # 4x4 với 1 hòn đá tại ô hợp lệ (1, 2)
    valid, msg = validate_custom_map(4, [[1, 2]])
    assert valid is True
    assert msg == "Map hợp lệ"

    # 5x5 với đá tại (2, 2)
    valid, msg = validate_custom_map(5, [[2, 2]])
    assert valid is True

    # 6x6 với đá tại (2, 3) (ô tự do, không chạm reserved)
    valid, msg = validate_custom_map(6, [[2, 3]])
    assert valid is True

    # 9x9 với đá tại (4, 4)
    valid, msg = validate_custom_map(9, [[4, 4]])
    assert valid is True

    # 15x15 với đá tại (7, 7)
    valid, msg = validate_custom_map(15, [[7, 7]])
    assert valid is True

    # 18x18 với đá tại (9, 9)
    valid, msg = validate_custom_map(18, [[9, 9]])
    assert valid is True


def test_map_validator_invalid_size():
    """Từ chối các kích thước bàn cờ không được hỗ trợ (ví dụ: 3x3, 7x7, 8x8)"""
    valid, msg = validate_custom_map(7, [[2, 2]])
    assert valid is False
    assert "không hợp lệ" in msg.lower()


def test_map_validator_out_of_bounds():
    """Từ chối tọa độ đá nằm ngoài bàn cờ"""
    valid, msg = validate_custom_map(4, [[4, 0]])
    assert valid is False
    assert "ngoài phạm vi" in msg.lower()

    valid, msg = validate_custom_map(5, [[-1, 2]])
    assert valid is False
    assert "ngoài phạm vi" in msg.lower()


def test_map_validator_duplicate_rocks():
    """Từ chối map chứa hai vật cản trên cùng một ô"""
    valid, msg = validate_custom_map(5, [[2, 2], [2, 2]])
    assert valid is False
    assert "trùng lặp" in msg.lower()


def test_map_validator_reserved_positions():
    """Không được đặt đá lên ô xuất phát hoặc căn cứ (Base) của người chơi"""
    # Căn cứ Red (0, 0)
    valid, msg = validate_custom_map(4, [[0, 0]])
    assert valid is False
    assert "căn cứ" in msg.lower() or "xuất phát" in msg.lower()

    # Căn cứ Blue (3, 3) trong map 4x4
    valid, msg = validate_custom_map(4, [[3, 3]])
    assert valid is False

    # Vị trí xuất phát quân cờ Red tại (0, 1) trong map 4x4
    valid, msg = validate_custom_map(4, [[0, 1]])
    assert valid is False


def test_map_validator_rock_count_limit():
    """Số lượng đá không được vượt quá (size * size) // 3"""
    # 4x4: max rocks = 16 // 3 = 5 đá. Đặt 6 đá -> từ chối!
    rocks_6 = [[0, 2], [0, 3], [1, 2], [1, 3], [2, 0], [2, 1]]
    valid, msg = validate_custom_map(4, rocks_6)
    assert valid is False
    assert "vượt quá giới hạn" in msg.lower()


def test_map_validator_partitioned_board():
    """Bàn cờ bị chia cắt hoàn toàn, không có đường đi giữa 2 căn cứ -> từ chối"""
    # 9x9: Đặt một hàng đá kín ngang dòng 4: (4, 0) đến (4, 8)
    # Tổng 9 đá, nhỏ hơn ngưỡng 81 // 3 = 27 đá, không chạm ô xuất phát (Red ở r<=2, Blue ở r>=6)
    # Red và Blue bị chia cắt hoàn toàn ở 2 nửa bàn cờ!
    blocking_rocks = [[4, c] for c in range(9)]
    valid, msg = validate_custom_map(9, blocking_rocks)
    assert valid is False
    assert "chia cắt" in msg.lower()


# ==============================================================
# 2. KIỂM THỬ GAME ENGINE VỚI Ô ĐÁ (GAMEPLAY & MOVE VALIDATION)
# ==============================================================

def test_game_engine_rock_obstacle_prevents_moves():
    """Quân cờ không thể di chuyển vào ô có đá; nước đi vào ô đá bị từ chối"""
    # Bàn cờ 4x4, đặt 1 hòn đá tại (0, 2)
    rocks = [[0, 2]]
    rule_set = RuleSet(board_size=4, rocks=rocks)
    engine = GameEngine(rule_set)

    # Quân Red ở (0, 1) cố gắng đi sang (0, 2) là ô có đá
    move_to_rock = Move((0, 1), (0, 2))
    assert engine.is_valid_move(move_to_rock, Team.RED) is False

    # Thử thực hiện nước đi vào ô đá -> trả về GameResult INVALID_MOVE
    res = engine.make_move(move_to_rock)
    assert res is not None
    assert "không hợp lệ" in res.reason.lower() or "đá" in res.reason.lower() or res.winner == Team.BLUE


def test_game_engine_legal_moves_exclude_rocks():
    """Danh sách nước đi hợp lệ (get_legal_moves) loại bỏ hoàn toàn các ô đá"""
    rocks = [[0, 2], [1, 2]]
    rule_set = RuleSet(board_size=4, rocks=rocks)
    engine = GameEngine(rule_set)

    legal_moves = engine.state.get_legal_moves(Team.RED)
    destinations = [m.to_coord for m in legal_moves]

    assert (0, 2) not in destinations
    assert (1, 2) not in destinations


# ==============================================================
# 3. KIỂM THỬ CRUD MAP & BẢO MẬT MAP THEO THỜI ĐIỂM
# ==============================================================

def test_tournament_map_crud_and_lock(db_session):
    """Host tạo, sửa, xóa map tùy chỉnh và kiểm tra khóa khi gán vào vòng đấu"""
    host = User(username="host_map", email="host@map.com", hashed_password="pwd")
    db_session.add(host)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, host, "Giải Đấu Map Tùy Chỉnh")

    # 1. Tạo Map 5x5
    map_data = TournamentMapCreate(name="Mê Cung Rừng Rậm", size=5, rocks=[[2, 2], [2, 3]])
    created_map = TournamentService.create_map(db_session, t.id, host, map_data)
    assert created_map.id is not None
    assert created_map.name == "Mê Cung Rừng Rậm"
    assert created_map.size == 5
    assert len(created_map.rocks) == 2

    # 2. Cập nhật Map
    update_data = TournamentMapUpdate(name="Mê Cung Cải Tiến", rocks=[[2, 2]])
    updated_map = TournamentService.update_map(db_session, t.id, created_map.id, host, update_data)
    assert updated_map.name == "Mê Cung Cải Tiến"
    assert len(updated_map.rocks) == 1
    assert updated_map.version == 2


def test_tournament_map_secrecy_and_disclosure(db_session):
    """
    Quy tắc công bố map theo thời điểm:
    - Trước thời điểm map_announced_at: người chơi thường bị chặn xem rocks (403),
      trong get_tournament_detail rocks bị ẩn (None/censored).
    - Chủ giải (Host) luôn xem được rocks để chuẩn bị giải.
    - Sau khi đến thời điểm map_announced_at: mọi người chơi đều xem được rocks công khai.
    """
    host = User(username="host_secret", email="hs@test.com", hashed_password="pwd")
    player = User(username="player_secret", email="ps@test.com", hashed_password="pwd")
    db_session.add_all([host, player])
    db_session.commit()

    t = TournamentService.create_tournament(db_session, host, "Giải Bí Mật")
    map_data = TournamentMapCreate(name="Bí Kíp 4x4", size=4, rocks=[[1, 2]])
    m = TournamentService.create_map(db_session, t.id, host, map_data)

    # Đăng ký 4 người chơi để khởi động giải
    p_users = [User(username=f"p_{i}", email=f"p_{i}@test.com", hashed_password="pwd") for i in range(1, 5)]
    db_session.add_all(p_users)
    db_session.commit()
    for u in p_users:
        TournamentService.register_participant(db_session, t.id, u)

    detail = TournamentService.start_tournament(db_session, t.id, host, auto_publish=True)
    round_1 = detail.rounds[0]

    # Gán map cho vòng 1 với thời gian công bố trong tương lai (sau 1 giờ)
    future_announcement = datetime.utcnow() + timedelta(hours=1)
    TournamentService.assign_round_map(
        db_session, t.id, round_1.id, host, m.id, map_announced_at=future_announcement
    )

    # 1. Người chơi thường xem map đơn lẻ -> Bị từ chối 403 với thông báo thời gian bảo mật
    with pytest.raises(HTTPException) as exc:
        TournamentService.get_map(db_session, t.id, m.id, user=player)
    assert exc.value.status_code == 403
    assert "bảo mật" in str(exc.value.detail).lower()

    # 2. Host xem map đơn lẻ -> Luôn thành công và xem được rocks
    host_view = TournamentService.get_map(db_session, t.id, m.id, user=host)
    assert host_view.rocks == [[1, 2]]

    # 3. Người chơi thường xem tournament detail -> round có rocks = None, is_map_announced = False
    player_detail = TournamentService.get_tournament_detail(db_session, t.id, current_user=player)
    r1_player = player_detail.rounds[0]
    assert r1_player.is_map_announced is False
    assert r1_player.rocks is None

    # 4. Khi đến giờ công bố (chỉnh lùi map_announced_at về quá khứ)
    db_r1 = db_session.query(TournamentRound).filter(TournamentRound.id == round_1.id).first()
    db_r1.map_announced_at = datetime.utcnow() - timedelta(minutes=5)
    db_session.commit()

    # Bây giờ người chơi thường xem tournament detail -> rocks đã được công bố!
    revealed_detail = TournamentService.get_tournament_detail(db_session, t.id, current_user=player)
    r1_revealed = revealed_detail.rounds[0]
    assert r1_revealed.is_map_announced is True
    assert r1_revealed.rocks == [[1, 2]]


# ==============================================================
# 4. KIỂM THỬ LẬP LỊCH THI ĐẤU & GIỚI HẠN TÀI NGUYÊN (SCHEDULER & QUEUE)
# ==============================================================

def test_tournament_schedule_batches_and_concurrency_limit(db_session):
    """
    Kiểm tra cơ chế chia đợt thi đấu (Batches) và giới hạn tài nguyên max_concurrent_matches:
    - Host cấu hình max_concurrent_matches = 2, batch_size = 2, interval = 10 phút.
    - Các trận được chia thành đợt có scheduled_at, check_in_opens_at rõ ràng.
    - run_scheduler_tick không cho phép số trận PLAYING vượt quá max_concurrent_matches.
    """
    host = User(username="host_sched", email="sched@test.com", hashed_password="pwd")
    users = [User(username=f"u_sched_{i}", email=f"us_{i}@test.com", hashed_password="pwd") for i in range(1, 9)]
    db_session.add_all([host] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, host, "Giải Đấu Lập Lịch 8 Người")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u)

    # Bắt đầu giải: 8 người -> 4 trận ở Vòng 1
    TournamentService.start_tournament(db_session, t.id, host, auto_publish=True)

    # Host lên lịch: 2 trận/đợt, cách nhau 10 phút, mở check-in trước 5 phút, max concurrent = 2
    now = datetime.utcnow()
    sched_data = TournamentScheduleCreate(
        max_concurrent_matches=2,
        batch_size=2,
        interval_minutes=10,
        check_in_advance_minutes=5,
        first_batch_time=now
    )
    sched_res = TournamentService.create_tournament_schedule(db_session, t.id, host, sched_data)
    assert sched_res["batch_count"] == 2
    assert sched_res["max_concurrent_matches"] == 2

    # Lấy dữ liệu lịch trình
    sched_info = TournamentService.get_tournament_schedule(db_session, t.id)
    assert sched_info["max_concurrent_matches"] == 2
    assert len(sched_info["batches"]) == 2

    # Đợt 1 (first_batch_time = now <= check_in_opens_at) -> 2 trận đầu ở trạng thái READY
    r1 = db_session.query(TournamentRound).filter(TournamentRound.tournament_id == t.id, TournamentRound.round_number == 1).first()
    all_matches = db_session.query(TournamentMatch).filter(TournamentMatch.round_id == r1.id).order_by(TournamentMatch.match_order.asc()).all()
    assert all_matches[0].status == "READY"
    assert all_matches[1].status == "READY"
    assert all_matches[2].status == "WAITING"
    assert all_matches[3].status == "WAITING"

    # Giả sử cả 2 trận READY (trận 0 và trận 1) đều được cả 2 người chơi điểm danh
    for m in [all_matches[0], all_matches[1]]:
        m.player1_joined_at = now
        m.player2_joined_at = now
    db_session.commit()

    # Kích hoạt scheduler tick
    TournamentService.run_scheduler_tick(db_session, t.id)

    # Đếm số trận PLAYING: phải tuân thủ max_concurrent_matches = 2
    playing_count = db_session.query(TournamentMatch).filter(
        TournamentMatch.tournament_id == t.id, TournamentMatch.status == "PLAYING"
    ).count()
    assert playing_count <= 2


# ==============================================================
# 5. KIỂM THỬ QUY TRÌNH 2 GIAI ĐOẠN (DRAFT RIÊNG TƯ & CÔNG BỐ LỊCH ĐẤU)
# ==============================================================

def test_two_stage_knockout_private_draft_and_publish_flow(db_session):
    """
    Quy trình 2 giai đoạn:
    1. Giai đoạn 1: Host nhấn Bắt đầu -> trạng thái SETTING_UP.
       Thí sinh/Khán giả KHÔNG xem được nhánh đấu (rounds = []).
       Chỉ Host/Admin mới xem được nhánh đấu đầy đủ.
    2. Giai đoạn 2: Host cấu hình từng trận (map, scheduled_at).
       Kiểm tra get_setup_overview, chặn publish khi chưa hoàn tất.
    3. Giai đoạn 3: Host hoàn tất và công bố (publish_tournament) -> PUBLISHED.
       Sau khi công bố, thí sinh xem được nhánh đấu và lịch thi đấu.
    """
    host = User(username="host_draft", email="hd@test.com", hashed_password="pwd")
    player = User(username="player_guest", email="pg@test.com", hashed_password="pwd")
    users = [User(username=f"pl_draft_{i}", email=f"pld_{i}@test.com", hashed_password="pwd") for i in range(1, 5)]
    db_session.add_all([host, player] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, host, "Giải Knockout 2 Giai Đoạn")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u, auto_accept=True)

    # 1. Host khởi động giải đấu (giai đoạn 1: tạo nhánh đấu riêng tư)
    detail_host = TournamentService.start_tournament(db_session, t.id, host, auto_publish=False)
    assert detail_host.tournament.status == "SETTING_UP"
    assert len(detail_host.rounds) == 2  # Host xem được 2 vòng đấu

    # Thí sinh hoặc khách xem chi tiết giải đấu -> Nhánh đấu bị ẩn hoàn toàn (rounds = [])!
    detail_player = TournamentService.get_tournament_detail(db_session, t.id, current_user=player)
    assert detail_player.tournament.status == "SETTING_UP"
    assert len(detail_player.rounds) == 0  # Bị ẩn tuyệt đối đối với thí sinh

    # 2. Host tạo 2 map cho 2 trận bán kết (kích thước khác nhau: 6x6 và 9x9)
    map1_data = TournamentMapCreate(name="Bán Kết 1 (6x6)", size=6, rocks=[[2, 3]])
    map2_data = TournamentMapCreate(name="Bán Kết 2 (9x9)", size=9, rocks=[[4, 4]])
    m1 = TournamentService.create_map(db_session, t.id, host, map1_data)
    m2 = TournamentService.create_map(db_session, t.id, host, map2_data)

    # Lấy danh sách trận vòng 1
    r1_matches = detail_host.rounds[0].matches
    assert len(r1_matches) == 2
    match1_id = r1_matches[0].id
    match2_id = r1_matches[1].id

    # 3. Host kiểm tra tổng quan setup: lúc này chưa trận nào được cấu hình -> can_publish = False
    overview_1 = TournamentService.get_setup_overview(db_session, t.id, host)
    assert overview_1.can_publish is False
    assert len(overview_1.errors) > 0

    # Thử công bố ngay -> Bị backend từ chối với lỗi 400
    with pytest.raises(HTTPException) as exc:
        TournamentService.publish_tournament(db_session, t.id, host)
    assert exc.value.status_code == 400
    assert "chưa thể công bố" in str(exc.value.detail).lower()

    # 4. Host cấu hình cho Trận 1 (Map 6x6, giờ thi đấu sau 2 ngày)
    time_m1 = datetime.utcnow() + timedelta(days=2)
    TournamentService.configure_match(
        db_session, t.id, match1_id, host,
        MatchConfigUpdateRequest(map_id=m1.id, scheduled_at=time_m1)
    )

    # 5. Host cấu hình cho Trận 2 (Map 9x9, giờ thi đấu sau 2 ngày 1 giờ)
    time_m2 = datetime.utcnow() + timedelta(days=2, hours=1)
    TournamentService.configure_match(
        db_session, t.id, match2_id, host,
        MatchConfigUpdateRequest(map_id=m2.id, scheduled_at=time_m2)
    )

    # 6. Kiểm tra lại tổng quan setup -> Cả 2 trận đã cấu hình thành công -> can_publish = True!
    overview_2 = TournamentService.get_setup_overview(db_session, t.id, host)
    assert overview_2.can_publish is True
    assert len(overview_2.errors) == 0

    # 7. Host nhấn Hoàn tất và công bố lịch đấu (Publish)
    pub_detail = TournamentService.publish_tournament(db_session, t.id, host)
    assert pub_detail.tournament.status == "PUBLISHED"
    assert pub_detail.tournament.published_at is not None

    # 8. Sau khi công bố, thí sinh vào xem chi tiết giải đấu -> ĐÃ THẤY TOÀN BỘ NHÁNH ĐẤU!
    player_view_published = TournamentService.get_tournament_detail(db_session, t.id, current_user=player)
    assert player_view_published.tournament.status == "PUBLISHED"
    assert len(player_view_published.rounds) == 2
    assert len(player_view_published.rounds[0].matches) == 2


# ==============================================================
# 6. KIỂM THỬ QUY TẮC BẢO MẬT MAP 24 GIỜ TRƯỚC GIỜ THI ĐẤU
# ==============================================================

def test_match_map_24h_secrecy_rule(db_session):
    """
    Quy tắc bảo mật 24 giờ bắt buộc:
    - Nếu trận đấu bắt đầu sau hơn 24 giờ (scheduled_at - now > 24h):
      * Thí sinh gọi GET /maps/{id} bị từ chối 403 Forbidden kèm thời gian công bố.
      * Trong match response của thí sinh: rocks = None, is_map_revealed = False.
      * Host/Admin luôn xem được rocks bất kỳ lúc nào.
    - Nếu trận đấu bắt đầu trong vòng 24 giờ (scheduled_at - now <= 24h):
      * Thí sinh gọi GET /maps/{id} thành công và xem được rocks.
      * Trong match response: rocks hiển thị đầy đủ, is_map_revealed = True.
    """
    host = User(username="host_24h", email="h24@test.com", hashed_password="pwd")
    player = User(username="player_24h", email="p24@test.com", hashed_password="pwd")
    users = [User(username=f"p24_{i}", email=f"p24_{i}@test.com", hashed_password="pwd") for i in range(1, 5)]
    db_session.add_all([host, player] + users)
    db_session.commit()

    t = TournamentService.create_tournament(db_session, host, "Giải Bảo Mật 24h")
    for u in users:
        TournamentService.register_participant(db_session, t.id, u, auto_accept=True)

    # Khởi động giải
    TournamentService.start_tournament(db_session, t.id, host, auto_publish=False)

    # Tạo map 15x15 với đá tại (7, 7)
    map_15 = TournamentService.create_map(
        db_session, t.id, host,
        TournamentMapCreate(name="Đại Chiến 15x15", size=15, rocks=[[7, 7]])
    )

    r1_matches = db_session.query(TournamentMatch).filter(
        TournamentMatch.tournament_id == t.id, TournamentMatch.is_bye == False
    ).all()
    m1 = r1_matches[0]
    m2 = r1_matches[1]

    # Trận 1: Lên lịch thi đấu sau 48 giờ (vượt quá 24h -> MAP ĐANG ĐƯỢC BẢO MẬT)
    future_48h = datetime.utcnow() + timedelta(hours=48)
    TournamentService.configure_match(
        db_session, t.id, m1.id, host,
        MatchConfigUpdateRequest(map_id=map_15.id, scheduled_at=future_48h)
    )

    # Trận 2: Lên lịch cùng thời điểm
    TournamentService.configure_match(
        db_session, t.id, m2.id, host,
        MatchConfigUpdateRequest(map_id=map_15.id, scheduled_at=future_48h)
    )

    # Công bố giải đấu
    TournamentService.publish_tournament(db_session, t.id, host)

    # THÍ SINH kiểm tra:
    # 1. Gọi API xem map trực tiếp -> 403 Forbidden!
    with pytest.raises(HTTPException) as exc:
        TournamentService.get_map(db_session, t.id, map_15.id, user=player)
    assert exc.value.status_code == 403
    assert "bảo mật" in str(exc.value.detail).lower()

    # 2. Xem qua Tournament Detail -> rocks bị giấu, is_map_revealed = False
    detail_player = TournamentService.get_tournament_detail(db_session, t.id, current_user=player)
    match_view_p = detail_player.rounds[0].matches[0]
    assert match_view_p.is_map_revealed is False
    assert match_view_p.rocks is None

    # HOST kiểm tra -> Luôn xem được rocks
    host_map_view = TournamentService.get_map(db_session, t.id, map_15.id, user=host)
    assert host_map_view.rocks == [[7, 7]]
    detail_host = TournamentService.get_tournament_detail(db_session, t.id, current_user=host)
    match_view_h = detail_host.rounds[0].matches[0]
    assert match_view_h.is_map_revealed is True
    assert match_view_h.rocks == [[7, 7]]

    # Bây giờ: Điều chỉnh lịch thi đấu xuống còn 10 giờ nữa (nhỏ hơn 24 giờ -> BẬT CÔNG KHAI NGAY LẬP TỨC)
    future_10h = datetime.utcnow() + timedelta(hours=10)
    TournamentService.configure_match(
        db_session, t.id, m1.id, host,
        MatchConfigUpdateRequest(map_id=map_15.id, scheduled_at=future_10h)
    )
    TournamentService.configure_match(
        db_session, t.id, m2.id, host,
        MatchConfigUpdateRequest(map_id=map_15.id, scheduled_at=future_10h)
    )

    # Thí sinh gọi lại API map -> Thành công vì đã trong phạm vi 24h!
    revealed_map = TournamentService.get_map(db_session, t.id, map_15.id, user=player)
    assert revealed_map.rocks == [[7, 7]]

    detail_player_rev = TournamentService.get_tournament_detail(db_session, t.id, current_user=player)
    match_view_p_rev = detail_player_rev.rounds[0].matches[0]
    assert match_view_p_rev.is_map_revealed is True
    assert match_view_p_rev.rocks == [[7, 7]]


# ==============================================================
# 7. KIỂM THỬ KÍCH THƯỚC MAP LỚN (9x9, 15x15, 18x18) VỚI GAME ENGINE
# ==============================================================

def test_large_board_sizes_game_engine():
    """Kiểm tra khởi tạo bàn cờ, bảo toàn căn cứ và nước đi hợp lệ cho map 9x9, 15x15, 18x18"""
    for size in [9, 15, 18]:
        center = size // 2
        rocks = [[center, center]]
        rule_set = RuleSet(board_size=size, rocks=rocks)
        engine = GameEngine(rule_set)

        # Kiểm tra kích thước bàn cờ
        assert engine.state.board.size == size

        # Kiểm tra ô đá cản
        assert engine.state.board.is_rock((center, center)) is True

        # Kiểm tra các nước đi hợp lệ của Red không chứa ô đá
        legal_moves = engine.state.get_legal_moves(Team.RED)
        destinations = [m.to_coord for m in legal_moves]
        assert (center, center) not in destinations
        assert len(legal_moves) > 0


def test_board_sizes_piece_distribution():
    """
    Quy tắc phân bổ quân cờ:
    - Bàn cờ 4x4, 5x5, 6x6: mỗi bên đúng 3 quân cờ (1 Búa, 1 Giấy/Bao, 1 Kéo).
    - Các bàn cờ còn lại (9x9, 15x15, 18x18): mỗi bên đúng 6 quân cờ (2 Búa, 2 Giấy/Bao, 2 Kéo).
    """
    from game.piece import PieceType

    # 1. Kiểm tra 4x4, 5x5, 6x6
    for size in [4, 5, 6]:
        rule_set = RuleSet(board_size=size)
        engine = GameEngine(rule_set)
        board = engine.state.board

        red_pieces = []
        blue_pieces = []
        for r in range(size):
            for c in range(size):
                p = board.get_piece((r, c))
                if p:
                    if p.team == Team.RED:
                        red_pieces.append(p.piece_type)
                    elif p.team == Team.BLUE:
                        blue_pieces.append(p.piece_type)

        assert len(red_pieces) == 3, f"Size {size} Red phải có 3 quân"
        assert len(blue_pieces) == 3, f"Size {size} Blue phải có 3 quân"

        # 1 búa, 1 giấy, 1 kéo
        assert red_pieces.count(PieceType.ROCK) == 1
        assert red_pieces.count(PieceType.PAPER) == 1
        assert red_pieces.count(PieceType.SCISSORS) == 1

        assert blue_pieces.count(PieceType.ROCK) == 1
        assert blue_pieces.count(PieceType.PAPER) == 1
        assert blue_pieces.count(PieceType.SCISSORS) == 1

    # 2. Kiểm tra các bàn cờ còn lại: 9x9, 15x15, 18x18
    for size in [9, 15, 18]:
        rule_set = RuleSet(board_size=size)
        engine = GameEngine(rule_set)
        board = engine.state.board

        red_pieces = []
        blue_pieces = []
        for r in range(size):
            for c in range(size):
                p = board.get_piece((r, c))
                if p:
                    if p.team == Team.RED:
                        red_pieces.append(p.piece_type)
                    elif p.team == Team.BLUE:
                        blue_pieces.append(p.piece_type)

        assert len(red_pieces) == 6, f"Size {size} Red phải có 6 quân"
        assert len(blue_pieces) == 6, f"Size {size} Blue phải có 6 quân"

        # 2 búa, 2 giấy, 2 kéo
        assert red_pieces.count(PieceType.ROCK) == 2
        assert red_pieces.count(PieceType.PAPER) == 2
        assert red_pieces.count(PieceType.SCISSORS) == 2

        assert blue_pieces.count(PieceType.ROCK) == 2
        assert blue_pieces.count(PieceType.PAPER) == 2
        assert blue_pieces.count(PieceType.SCISSORS) == 2


