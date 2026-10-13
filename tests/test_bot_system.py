import os
import pytest
from fastapi import HTTPException
from backend.models.user import User
from backend.models.bot import Bot, BotVersion
from backend.services.bot_service import BotService
from backend.services.room_service import RoomService
from judge.validator import BotValidator

def test_bot_validator_static_and_sandbox():
    # 1. Valid code
    valid_code = """
class Bot:
    def get_move(self, state_dict: dict) -> dict:
        return state_dict.get('legal_moves', [{'from': [0, 1], 'to': [1, 1]}])[0]
"""
    is_valid, msg = BotValidator.validate(valid_code)
    assert is_valid is True

    # 2. Syntax error
    is_valid, msg = BotValidator.validate("def invalid_syntax(:")
    assert is_valid is False
    assert "Syntax Error" in msg or "cú pháp" in msg

    # 3. Missing class Bot
    is_valid, msg = BotValidator.validate("def get_move(self, state): pass")
    assert is_valid is False
    assert "Missing class 'Bot'" in msg

    # 4. Missing method get_move
    is_valid, msg = BotValidator.validate("class Bot:\n    pass")
    assert is_valid is False
    assert "Missing method 'get_move'" in msg

    # 5. Forbidden imports
    is_valid, msg = BotValidator.validate("import os\nclass Bot:\n    def get_move(self, s): pass")
    assert is_valid is False
    assert "Forbidden import: os" in msg

    is_valid, msg = BotValidator.validate("from subprocess import Popen\nclass Bot:\n    def get_move(self, s): pass")
    assert is_valid is False
    assert "Forbidden import: subprocess" in msg


def test_bot_service_create_and_versioning(db_session):
    user = User(username="bot_master", email="botmaster@test.com", hashed_password="pwd")
    db_session.add(user)
    db_session.commit()

    # 1. Create bot with valid code
    valid_code = open("bots/examples/random_bot.py", "rb").read()
    bot = BotService.create_bot(
        db=db_session,
        user=user,
        name="Siêu Bot Alpha",
        description="Bot ngẫu nhiên chiến thuật",
        filename="random_bot.py",
        content=valid_code
    )
    assert bot.id is not None
    assert bot.name == "Siêu Bot Alpha"
    assert bot.status == "READY"
    assert bot.current_version_id is not None

    # 2. List user bots
    my_bots = BotService.list_user_bots(db_session, user.id)
    assert len(my_bots) == 1
    assert my_bots[0]["name"] == "Siêu Bot Alpha"
    assert my_bots[0]["current_version_number"] == 1
    assert my_bots[0]["status"] == "READY"

    # 3. Upload version 2 (Greedy code)
    greedy_code = open("bots/examples/greedy_bot.py", "rb").read()
    v2 = BotService.create_new_version(
        db=db_session,
        user=user,
        bot_id=bot.id,
        filename="greedy_bot.py",
        content=greedy_code
    )
    assert v2.version_number == 2
    assert v2.status == "READY"

    # Verify history has 2 versions
    detail = BotService.get_bot_detail(db_session, user.id, bot.id)
    assert detail["total_versions"] == 2
    assert detail["current_version_number"] == 2
    assert len(detail["versions"]) == 2

    # 4. Upload version 3 with invalid syntax -> should be INVALID without affecting v1/v2 history
    invalid_code = b"class Bot:\n    def get_move(self, s): invalid syntax"
    v3 = BotService.create_new_version(
        db=db_session,
        user=user,
        bot_id=bot.id,
        filename="bad_bot.py",
        content=invalid_code
    )
    assert v3.version_number == 3
    assert v3.status == "INVALID"
    assert v3.validation_error is not None

    # Ready bots only return READY status bots
    # Bot status is now INVALID because latest version is invalid
    ready_bots = BotService.get_ready_bots(db_session, user.id)
    assert len(ready_bots) == 0


def test_bot_vs_bot_match_in_room(db_session):
    u1 = User(username="player_red", email="red@test.com", hashed_password="pwd")
    u2 = User(username="player_blue", email="blue@test.com", hashed_password="pwd")
    db_session.add_all([u1, u2])
    db_session.commit()

    code1 = open("bots/examples/random_bot.py", "rb").read()
    code2 = open("bots/examples/greedy_bot.py", "rb").read()

    b1 = BotService.create_bot(db_session, u1, "Bot Red", "RED Bot", "r.py", code1)
    b2 = BotService.create_bot(db_session, u2, "Bot Blue", "BLUE Bot", "b.py", code2)
    assert b1.status == "READY"
    assert b2.status == "READY"

    room = RoomService.create_room(db_session, u1, "Trận Chiến Bot")
    # u2 joins
    req = RoomService.request_join_room(db_session, room.room_code, u2)
    RoomService.respond_to_request(db_session, room.id, req.id, u1, "ACCEPT")

    # Ready without bot should fail
    with pytest.raises(HTTPException) as exc:
        RoomService.set_ready_status(db_session, room.id, u1, is_ready=True)
    assert "chọn Bot" in exc.value.detail

    # Both select bots
    RoomService.select_bot(db_session, room.id, u1, b1.id)
    RoomService.select_bot(db_session, room.id, u2, b2.id)

    # Both ready up
    RoomService.set_ready_status(db_session, room.id, u1, is_ready=True)
    RoomService.set_ready_status(db_session, room.id, u2, is_ready=True)

    db_session.refresh(room)
    assert room.status == "READY"

    # Start match between Bot Red and Bot Blue
    match = RoomService.start_room_match(db_session, room.id, u1)
    assert match.id is not None
    assert match.status == "COMPLETED"
    assert match.total_turns > 0
    assert match.points_awarded is True
    assert match.moves_json is not None
    assert match.initial_board_json is not None

    # Check match state endpoint response
    state = RoomService.get_room_match_state(db_session, room.id)
    assert state["has_match"] is True
    assert state["status"] == "COMPLETED"
    assert state["red_bot_name"] == "Bot Red"
    assert state["blue_bot_name"] == "Bot Blue"
    assert len(state["moves"]) == match.total_turns


def test_bot_api_endpoints(client, db_session):
    from backend.services.auth_service import AuthService
    user = User(username="api_player", email="api_player@test.com", hashed_password="pwd")
    db_session.add(user)
    db_session.commit()

    token = AuthService.create_access_token({"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Download example bot
    res_ex = client.get("/api/bots/examples/random")
    assert res_ex.status_code == 200
    assert "class Bot" in res_ex.text

    # 2. Upload bot
    code = open("bots/examples/random_bot.py", "rb")
    res_up = client.post(
        "/api/bots/upload",
        headers=headers,
        data={"name": "Bot API Test", "description": "Mo ta"},
        files={"file": ("random_bot.py", code, "text/x-python")}
    )
    assert res_up.status_code == 200
    bot_data = res_up.json()
    assert bot_data["name"] == "Bot API Test"
    assert bot_data["status"] == "READY"
    bot_id = bot_data["id"]

    # 3. List my bots
    res_my = client.get("/api/bots/my-bots", headers=headers)
    assert res_my.status_code == 200
    assert len(res_my.json()) >= 1

    # 4. List ready bots
    res_ready = client.get("/api/bots/ready", headers=headers)
    assert res_ready.status_code == 200
    assert any(b["id"] == bot_id for b in res_ready.json())

    # 5. Upload new version
    code2 = open("bots/examples/greedy_bot.py", "rb")
    res_v2 = client.post(
        f"/api/bots/{bot_id}/version",
        headers=headers,
        files={"file": ("greedy_bot.py", code2, "text/x-python")}
    )
    assert res_v2.status_code == 200
    v2_data = res_v2.json()
    assert v2_data["version_number"] == 2
    assert v2_data["status"] == "READY"

    # 6. Select bot in room
    room = RoomService.create_room(db_session, user, "Phòng API Test")
    res_sel = client.post(
        f"/api/rooms/{room.id}/select-bot",
        headers=headers,
        json={"bot_id": bot_id}
    )
    assert res_sel.status_code == 200
    room_data = res_sel.json()
    assert room_data["player1_bot_id"] == bot_id
    assert room_data["player1_bot_name"] == "Bot API Test"

    # 7. Check match state when not started
    res_st = client.get(f"/api/rooms/{room.id}/match-state", headers=headers)
    assert res_st.status_code == 200
    assert res_st.json()["has_match"] is False
