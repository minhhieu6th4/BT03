import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from backend.database.base import Base
from backend.models.user import User
from backend.models.room import Room, RoomJoinRequest
from backend.services.room_service import RoomService

def test_room_lifecycle(db_session):
    owner = User(username="owner_user", email="owner@test.com", hashed_password="pwd")
    player2 = User(username="challenger", email="p2@test.com", hashed_password="pwd")
    db_session.add_all([owner, player2])
    db_session.commit()

    # 1. Create room
    room = RoomService.create_room(db_session, owner, "Thách Đấu Đại Chiến")
    assert room.id is not None
    assert room.room_code is not None
    assert room.owner_id == owner.id
    assert room.player1_id == owner.id
    assert room.player2_id is None
    assert room.status == "WAITING"

    # 2. Check open rooms list
    open_rooms = RoomService.list_open_rooms(db_session)
    assert len(open_rooms) >= 1
    assert any(r.room_code == room.room_code for r in open_rooms)

    # 3. Owner cannot request to join own room
    with pytest.raises(HTTPException):
        RoomService.request_join_room(db_session, room.room_code, owner)

    # 4. Player2 requests to join room
    req = RoomService.request_join_room(db_session, room.room_code, player2)
    assert req.status == "PENDING"
    assert req.user_id == player2.id

    # 5. Duplicate request prevention
    with pytest.raises(HTTPException):
        RoomService.request_join_room(db_session, room.room_code, player2)

    # 6. Owner accepts request
    updated_room = RoomService.respond_to_request(
        db_session, room.id, req.id, owner, action="ACCEPT"
    )
    assert updated_room.player2_id == player2.id

    # 7. Player 3 cannot join full room (capacity strictly 2)
    player3 = User(username="p3", email="p3@test.com", hashed_password="pwd")
    db_session.add(player3)
    db_session.commit()

    with pytest.raises(HTTPException):
        RoomService.request_join_room(db_session, room.room_code, player3)

    # 7.5 Bot selection
    from backend.models.bot import Bot, BotVersion
    bot1 = Bot(name="Bot Red", user_id=owner.id, status="READY")
    bot2 = Bot(name="Bot Blue", user_id=player2.id, status="READY")
    db_session.add_all([bot1, bot2])
    db_session.commit()
    ver1 = BotVersion(bot_id=bot1.id, version_number=1, file_path="bots/examples/random_bot.py", status="READY")
    ver2 = BotVersion(bot_id=bot2.id, version_number=1, file_path="bots/examples/random_bot.py", status="READY")
    db_session.add_all([ver1, ver2])
    db_session.commit()
    bot1.current_version_id = ver1.id
    bot2.current_version_id = ver2.id
    db_session.commit()

    RoomService.select_bot(db_session, room.id, owner, bot1.id)
    RoomService.select_bot(db_session, room.id, player2, bot2.id)

    # 8. Ready status
    # Player 1 readies
    RoomService.set_ready_status(db_session, room.id, owner, is_ready=True)
    db_session.refresh(room)
    assert room.status == "WAITING" # Still waiting for player 2

    # Player 2 readies
    RoomService.set_ready_status(db_session, room.id, player2, is_ready=True)
    db_session.refresh(room)
    assert room.status == "READY" # Both ready!

    # 9. Start match
    match = RoomService.start_room_match(db_session, room.id, owner)
    assert match.id is not None
    assert match.match_type == "REGULAR"
    assert match.status in ["PLAYING", "COMPLETED"]
    db_session.refresh(room)
    assert room.status in ["PLAYING", "FINISHED"]

    # 10. Finish match and idempotent points
    finished_match = RoomService.finish_room_match(db_session, room.id, winner_user_id=owner.id)
    assert finished_match.status == "COMPLETED"
    assert finished_match.points_awarded == True
    db_session.refresh(room)
    assert room.status == "FINISHED"

def test_cancel_room_when_no_participants(db_session):
    owner = User(username="room_host", email="host@test.com", hashed_password="pwd")
    intruder = User(username="intruder", email="int@test.com", hashed_password="pwd")
    db_session.add_all([owner, intruder])
    db_session.commit()

    # Tạo phòng nhưng chưa ai tham gia
    room = RoomService.create_room(db_session, owner, "Phòng Chờ")
    assert room.status == "WAITING"
    assert room.player2_id is None

    # Người khác không thể hủy phòng của chủ phòng
    with pytest.raises(HTTPException) as exc:
        RoomService.cancel_room(db_session, room.id, intruder)
    assert exc.value.status_code == 403

    # Chủ phòng hủy phòng thành công
    cancelled_room = RoomService.cancel_room(db_session, room.id, owner)
    assert cancelled_room.status == "CANCELLED"

    # Phòng đã hủy không còn xuất hiện trong danh sách phòng mở
    open_rooms = RoomService.list_open_rooms(db_session)
    assert not any(r.id == room.id for r in open_rooms)


def test_guest_role_and_join_status_response(db_session):
    host = User(username="host_user", email="host_r@test.com", hashed_password="pwd")
    guest = User(username="guest_user", email="guest_r@test.com", hashed_password="pwd")
    other = User(username="other_user", email="other_r@test.com", hashed_password="pwd")
    db_session.add_all([host, guest, other])
    db_session.commit()

    room = RoomService.create_room(db_session, host, "Test Guest Flow")

    # 1. Before requesting: guest is SPECTATOR
    res_before = RoomService.get_room_response(db_session, room.id, caller_id=guest.id)
    assert res_before.my_role == "SPECTATOR"
    assert res_before.my_join_status is None

    # Host is PLAYER1
    res_host = RoomService.get_room_response(db_session, room.room_code, caller_id=host.id)
    assert res_host.my_role == "PLAYER1"

    # 2. Guest requests to join: guest is PENDING_GUEST
    req = RoomService.request_join_room(db_session, room.room_code, guest)
    res_pending = RoomService.get_room_response(db_session, room.id, caller_id=guest.id)
    assert res_pending.my_role == "PENDING_GUEST"
    assert res_pending.my_join_status == "PENDING"

    # 3. Host accepts: guest becomes PLAYER2
    RoomService.respond_to_request(db_session, room.id, req.id, host, action="ACCEPT")
    res_accepted = RoomService.get_room_response(db_session, room.id, caller_id=guest.id)
    assert res_accepted.my_role == "PLAYER2"
    assert res_accepted.my_join_status == "ACCEPTED"
    assert res_accepted.player2_id == guest.id
    assert res_accepted.player2_name == guest.username

    # 4. Other user is SPECTATOR
    res_other = RoomService.get_room_response(db_session, room.room_code, caller_id=other.id)
    assert res_other.my_role == "SPECTATOR"

