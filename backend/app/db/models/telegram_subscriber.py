import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, Boolean, DateTime
from app.db.database import Base


class TelegramSubscriber(Base):
    """
    Persistent registry of connected Telegram subscribers eligible for IoT real-time alerts.
    """
    __tablename__ = "telegram_subscribers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=True, default="private")
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<TelegramSubscriber chat_id={self.chat_id} username={self.username} active={self.is_active}>"
