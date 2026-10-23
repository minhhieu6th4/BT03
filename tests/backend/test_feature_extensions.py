import uuid

from backend.models.match import Match
from backend.models.notification import Notification
from backend.models.account_token import AccountToken
from backend.models.user import User
from backend.services.account_service import AccountService
from backend.services.auth_service import AuthService


def create_user(db_session, is_admin=False):
    suffix = uuid.uuid4().hex
    user = User(
        username=f"feature_{suffix[:12]}",
        email=f"{suffix}@example.com",
        hashed_password="not-used-in-these-tests",
        is_admin=is_admin,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user):
    token = AuthService.create_access_token({"sub": user.username, "uid": user.id})
    return {"Authorization": f"Bearer {token}"}


def test_match_history_filters_and_paginates(client, db_session):
    player = create_user(db_session)
    opponent = create_user(db_session)
    match = Match(
        red_user_id=player.id,
        blue_user_id=opponent.id,
        winner_user_id=player.id,
        match_type="REGULAR",
        status="COMPLETED",
        total_turns=12,
    )
    db_session.add(match)
    db_session.commit()

    response = client.get(f"/api/matches/?player_id={player.id}&result=win&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == match.id
    assert payload["items"][0]["red_username"] == player.username


def test_team_owner_can_manage_members(client, db_session):
    owner = create_user(db_session)
    member = create_user(db_session)
    team_response = client.post(
        "/api/teams/",
        json={"name": f"team_{uuid.uuid4().hex[:12]}"},
        headers=auth_headers(owner),
    )
    assert team_response.status_code == 200
    team_id = team_response.json()["id"]

    add_response = client.post(
        f"/api/teams/{team_id}/members",
        json={"user_id": member.id},
        headers=auth_headers(owner),
    )

    assert add_response.status_code == 200
    assert {item["user_id"] for item in add_response.json()["members"]} == {owner.id, member.id}


def test_notifications_are_private_and_markable(client, db_session):
    recipient = create_user(db_session)
    other = create_user(db_session)
    notification = Notification(
        user_id=recipient.id,
        kind="TEST",
        title="Test notification",
        message="Private content",
    )
    db_session.add(notification)
    db_session.commit()

    own_response = client.get("/api/notifications/", headers=auth_headers(recipient))
    other_response = client.patch(
        f"/api/notifications/{notification.id}/read",
        headers=auth_headers(other),
    )
    read_response = client.patch(
        f"/api/notifications/{notification.id}/read",
        headers=auth_headers(recipient),
    )

    assert own_response.status_code == 200
    assert own_response.json()["unread_count"] == 1
    assert other_response.status_code == 404
    assert read_response.status_code == 200


def test_admin_routes_require_admin(client, db_session):
    regular_user = create_user(db_session)
    admin_user = create_user(db_session, is_admin=True)

    forbidden = client.get("/api/admin/users", headers=auth_headers(regular_user))
    allowed = client.get("/api/admin/users", headers=auth_headers(admin_user))

    assert forbidden.status_code == 403
    assert allowed.status_code == 200


def test_account_action_token_is_single_use(db_session):
    user = create_user(db_session)
    token = "test-token-value"
    import hashlib
    from datetime import datetime, timedelta

    db_session.add(AccountToken(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        purpose="VERIFY_EMAIL",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    ))
    db_session.commit()

    consumed = AccountService.consume_token(db_session, token, "VERIFY_EMAIL")

    assert consumed.user_id == user.id
    db_session.commit()
    try:
        AccountService.consume_token(db_session, token, "VERIFY_EMAIL")
        assert False, "A consumed token must not be reusable"
    except Exception as error:
        assert getattr(error, "status_code", None) == 400


def test_report_submission_and_admin_resolution(client, db_session):
    reporter = create_user(db_session)
    reported = create_user(db_session)
    admin = create_user(db_session, is_admin=True)

    report_response = client.post(
        "/api/reports/",
        json={"reported_user_id": reported.id, "reason": "Rule violation", "details": "Repeatedly ignored the match rules."},
        headers=auth_headers(reporter),
    )
    assert report_response.status_code == 200
    report_id = report_response.json()["id"]

    resolution = client.patch(
        f"/api/admin/reports/{report_id}",
        json={"status": "RESOLVED", "admin_note": "Reviewed"},
        headers=auth_headers(admin),
    )

    assert resolution.status_code == 200
    assert resolution.json()["status"] == "RESOLVED"


def test_username_change_keeps_current_token_valid(client, db_session):
    user = create_user(db_session)
    headers = auth_headers(user)
    new_username = f"renamed_{uuid.uuid4().hex[:10]}"

    update = client.patch("/api/users/me", json={"username": new_username}, headers=headers)
    current = client.get("/api/users/me", headers=headers)

    assert update.status_code == 200
    assert current.status_code == 200
    assert current.json()["username"] == new_username