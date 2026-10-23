import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
import jwt
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.database.connection import get_db
from backend.dependencies.auth import get_current_user
from backend.models.notification import Notification
from backend.models.user import User
from backend.services.notification_service import NotificationService

router = APIRouter()


@router.websocket("/ws")
async def notification_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        token = auth_message.get("token")
        if not token:
            await websocket.close(code=1008)
            return
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("uid")
    except (jwt.PyJWTError, asyncio.TimeoutError, AttributeError):
        await websocket.close(code=1008)
        return

    db_generator = get_db()
    db = next(db_generator)
    try:
        query = db.query(User).filter(User.is_active.is_(True))
        try:
            user = query.filter(User.id == int(user_id)).first() if user_id is not None else query.filter(User.username == username).first()
        except (TypeError, ValueError):
            user = None
        if not user:
            await websocket.close(code=1008)
            return
        user_id = user.id
    finally:
        db.close()
        db_generator.close()

    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    NotificationService.subscribe(user_id, loop, queue)
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_json(message)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "keepalive"})
    except WebSocketDisconnect:
        pass
    finally:
        NotificationService.unsubscribe(user_id, loop, queue)


@router.get("/")
def list_notifications(
    unread_only: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    total = query.count()
    items = query.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(offset).limit(limit).all()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).count()
    return {
        "items": [
            {
                "id": item.id,
                "kind": item.kind,
                "title": item.title,
                "message": item.message,
                "link": item.link,
                "is_read": item.is_read,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total": total,
        "unread_count": unread_count,
        "offset": offset,
        "limit": limit,
    }


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    item.is_read = True
    db.commit()
    return {"message": "Đã đánh dấu đã đọc"}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"message": "Đã đánh dấu tất cả thông báo là đã đọc"}