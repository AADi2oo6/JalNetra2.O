import uuid
from datetime import datetime, timezone
import logging
from typing import List, Optional, Set
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.db.database import engine
from app.db.models.telegram_subscriber import TelegramSubscriber

logger = logging.getLogger("jalnetra.db.telegram_subscribers")


class TelegramSubscriberRepository:
    def __init__(self, db: Session):
        self.db = db
        # Ensure table exists even in dynamic SQLite environments
        try:
            TelegramSubscriber.__table__.create(bind=engine, checkfirst=True)
        except Exception as e:
            logger.debug("Table checkfirst notice: %s", e)

    def get_by_chat_id(self, chat_id: int) -> Optional[TelegramSubscriber]:
        return self.db.execute(
            select(TelegramSubscriber).where(TelegramSubscriber.chat_id == chat_id)
        ).scalar_one_or_none()

    def list_active_subscribers(self, allowed_chat_ids: Optional[Set[str]] = None) -> List[TelegramSubscriber]:
        """
        Returns all subscribers where is_active == True.
        If allowed_chat_ids is configured, enforces allowed_chat_ids whitelist.
        """
        stmt = select(TelegramSubscriber).where(TelegramSubscriber.is_active == True)
        results = self.db.execute(stmt).scalars().all()
        if allowed_chat_ids is not None:
            return [s for s in results if str(s.chat_id) in allowed_chat_ids]
        return list(results)

    def count_active_subscribers(self, allowed_chat_ids: Optional[Set[str]] = None) -> int:
        return len(self.list_active_subscribers(allowed_chat_ids=allowed_chat_ids))

    def register_or_update(
        self,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        chat_type: Optional[str] = "private",
        is_active: bool = True,
    ) -> TelegramSubscriber:
        """
        Upsert a Telegram subscriber. If exists, update activity status and metadata.
        """
        now = datetime.now(timezone.utc)
        sub = self.get_by_chat_id(chat_id)
        if sub is None:
            sub = TelegramSubscriber(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                chat_type=chat_type or "private",
                is_active=is_active,
                created_at=now,
                last_seen_at=now,
            )
            self.db.add(sub)
        else:
            sub.is_active = is_active
            sub.last_seen_at = now
            if username is not None:
                sub.username = username
            if first_name is not None:
                sub.first_name = first_name
            if last_name is not None:
                sub.last_name = last_name
            if chat_type is not None:
                sub.chat_type = chat_type

        self.db.commit()
        self.db.refresh(sub)
        return sub

    def set_active_status(self, chat_id: int, is_active: bool) -> Optional[TelegramSubscriber]:
        """Update is_active flag (e.g. for /stop or on blocked 403)."""
        sub = self.get_by_chat_id(chat_id)
        if sub:
            sub.is_active = is_active
            sub.last_seen_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(sub)
        return sub

    def update_last_seen(self, chat_id: int) -> Optional[TelegramSubscriber]:
        sub = self.get_by_chat_id(chat_id)
        if sub:
            sub.last_seen_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(sub)
        return sub
