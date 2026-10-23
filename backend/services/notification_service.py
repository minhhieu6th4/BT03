import asyncio
import threading
from typing import Dict, Optional, Set, Tuple

from sqlalchemy.orm import Session

from backend.models.notification import Notification

_subscribers: Dict[int, Set[Tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {}
_subscriber_lock = threading.RLock()


class NotificationService:
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        kind: str,
        title: str,
        message: str,
        link: Optional[str] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            kind=kind,
            title=title,
            message=message,
            link=link,
        )
        db.add(notification)
        payload = {
            "type": "notification",
            "kind": kind,
            "title": title,
            "message": message,
            "link": link,
        }
        with _subscriber_lock:
            subscribers = tuple(_subscribers.get(user_id, set()))
        for loop, queue in subscribers:
            if not loop.is_closed():
                try:
                    loop.call_soon_threadsafe(queue.put_nowait, payload)
                except RuntimeError:
                    pass
        return notification

    @staticmethod
    def subscribe(user_id: int, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
        with _subscriber_lock:
            _subscribers.setdefault(user_id, set()).add((loop, queue))

    @staticmethod
    def unsubscribe(user_id: int, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
        with _subscriber_lock:
            subscriptions = _subscribers.get(user_id)
            if not subscriptions:
                return
            subscriptions.discard((loop, queue))
            if not subscriptions:
                _subscribers.pop(user_id, None)