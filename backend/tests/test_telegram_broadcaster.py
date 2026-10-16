"""
Comprehensive tests for Telegram Alert Broadcaster, Subscriber Registry,
slash command subscriptions (/start, /stop), blocked user deactivation,
and Unified Alert Event Bus.
"""
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models.telegram_subscriber import TelegramSubscriber
from app.db.repositories.telegram_subscriber_repository import TelegramSubscriberRepository
from app.services.iot.monitoring.models import (
    IoTAlert,
    IoTAlertSeverity,
    IoTAlertType,
)
from app.services.iot.monitoring.event_bus import AlertEventBus
from app.services.telegram.alert_broadcaster import (
    TelegramAlertBroadcaster,
    format_telegram_alert,
)
from app.services.telegram.client import TelegramClient
from app.services.telegram.handlers import TelegramCommandHandler
from app.services.telegram.models import (
    TelegramMessage,
    TelegramChat,
    TelegramUser,
)


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session, Session
    session.close()


def make_sample_alert() -> IoTAlert:
    return IoTAlert(
        id="alert-uuid-1234",
        session_id="session-5678",
        water_body_id="wb-1",
        water_body_name="Harsul Reservoir",
        type=IoTAlertType.WATER_LEVEL_INCREASE,
        severity=IoTAlertSeverity.HIGH,
        title="Sudden Water Level Increase",
        message="Water level rose abruptly by 7.1%",
        sensor_name="Water Level",
        previous_value=72.0,
        current_value=79.1,
        change=7.1,
        unit="%",
        detected_at="2026-10-16T12:45:32Z",
        latitude=19.929,
        longitude=75.337,
        google_maps_url="https://maps.google.com/?q=19.929,75.337",
    )


def test_subscriber_registration_and_update(in_memory_db):
    db, _ = in_memory_db
    repo = TelegramSubscriberRepository(db)

    # 1. Register new subscriber
    sub1 = repo.register_or_update(
        chat_id=123456789,
        username="water_watcher",
        first_name="Alice",
        chat_type="private",
        is_active=True,
    )
    assert sub1.chat_id == 123456789
    assert sub1.username == "water_watcher"
    assert sub1.is_active is True

    # 2. Repeated registration does not duplicate
    sub2 = repo.register_or_update(
        chat_id=123456789,
        username="water_watcher_updated",
        first_name="Alice B",
        is_active=True,
    )
    assert sub2.id == sub1.id
    assert sub2.username == "water_watcher_updated"
    assert repo.count_active_subscribers() == 1

    # 3. /stop deactivates user
    repo.set_active_status(123456789, is_active=False)
    assert repo.count_active_subscribers() == 0
    inactive_sub = repo.get_by_chat_id(123456789)
    assert inactive_sub is not None
    assert inactive_sub.is_active is False

    # 4. /start re-enables user
    repo.set_active_status(123456789, is_active=True)
    assert repo.count_active_subscribers() == 1


def test_telegram_handlers_start_and_stop(in_memory_db):
    db, session_factory = in_memory_db
    mock_client = MagicMock(spec=TelegramClient)
    mock_client.send_message = AsyncMock(return_value=True)

    handler = TelegramCommandHandler(
        client=mock_client,
        db_factory=session_factory,
    )

    async def run():
        # 1. Send /start
        msg_start = TelegramMessage(
            message_id=1,
            chat=TelegramChat(id=987654321, type="private", username="alice_user"),
            from_user=TelegramUser(id=987654321, is_bot=False, first_name="Alice", username="alice_user"),
            date=1700000000,
            text="/start",
        )
        await handler.handle_message(msg_start)

        # Verify subscriber registered in database
        repo = TelegramSubscriberRepository(db)
        sub = repo.get_by_chat_id(987654321)
        assert sub is not None
        assert sub.is_active is True
        assert sub.username == "alice_user"

        # Verify welcome message sent
        mock_client.send_message.assert_called_once()
        assert "Welcome to JalNetra" in mock_client.send_message.call_args[0][1]

        # 2. Send /stop
        mock_client.send_message.reset_mock()
        msg_stop = TelegramMessage(
            message_id=2,
            chat=TelegramChat(id=987654321, type="private", username="alice_user"),
            from_user=TelegramUser(id=987654321, is_bot=False, first_name="Alice", username="alice_user"),
            date=1700000005,
            text="/stop",
        )
        await handler.handle_message(msg_stop)

        # Verify subscriber deactivated
        db.expire_all()
        sub_after_stop = repo.get_by_chat_id(987654321)
        assert sub_after_stop.is_active is False
        assert "JalNetra alerts disabled" in mock_client.send_message.call_args[0][1]

    import asyncio
    asyncio.run(run())


def test_broadcaster_multiple_subscribers_independent_failures(in_memory_db):
    from app.services.iot.monitoring.alerts import _active_chat_registry
    _active_chat_registry.clear()

    db, session_factory = in_memory_db
    repo = TelegramSubscriberRepository(db)

    # Register 3 subscribers
    repo.register_or_update(chat_id=101, username="user_a", is_active=True)
    repo.register_or_update(chat_id=102, username="user_b", is_active=True)
    repo.register_or_update(chat_id=103, username="user_c", is_active=True)

    # Mock client: 101 succeeds, 102 fails with 403 (blocked), 103 succeeds
    mock_client = MagicMock(spec=TelegramClient)
    mock_client.is_configured = True

    async def mock_send_detailed(chat_id, text, reply_markup=None, parse_mode=None):
        if chat_id == 101:
            return True, 200, "OK"
        elif chat_id == 102:
            return False, 403, "Forbidden: bot was blocked by the user"
        elif chat_id == 103:
            return True, 200, "OK"
        return False, 500, "Internal error"

    mock_client.send_message_detailed = AsyncMock(side_effect=mock_send_detailed)

    broadcaster = TelegramAlertBroadcaster(
        client=mock_client,
        db_factory=session_factory,
    )

    alert = make_sample_alert()

    async def run():
        res = await broadcaster.broadcast_alert(alert)

        assert res["total_recipients"] == 3
        assert res["successful"] == 2
        assert res["failed"] == 1

        # Verify subscriber 102 was auto-deactivated due to HTTP 403
        db.expire_all()
        assert repo.get_by_chat_id(101).is_active is True
        assert repo.get_by_chat_id(102).is_active is False
        assert repo.get_by_chat_id(103).is_active is True

    import asyncio
    asyncio.run(run())


def test_telegram_alert_formatting():
    alert = make_sample_alert()
    formatted = format_telegram_alert(alert)

    assert "🚨 JALNETRA IoT ALERT" in formatted
    assert "💧 Harsul Reservoir" in formatted
    assert "🔴 WATER LEVEL INCREASE" in formatted
    assert "72.0%" in formatted
    assert "79.1%" in formatted
    assert "+7.1 percentage points" in formatted
    assert "19.929°N, 75.337°E" in formatted
    assert "https://maps.google.com/?q=19.929,75.337" in formatted


def test_alert_event_bus():
    import asyncio
    bus = AlertEventBus()
    queue = asyncio.Queue()

    bus.subscribe(queue)
    assert bus.subscriber_count == 1

    bus.publish("iot_alert", {"id": "test-1", "severity": "HIGH"})
    event_type, payload = queue.get_nowait()
    assert event_type == "iot_alert"
    assert payload["id"] == "test-1"

    bus.unsubscribe(queue)
    assert bus.subscriber_count == 0
