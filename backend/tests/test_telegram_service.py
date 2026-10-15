import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.telegram import (
    TelegramClient,
    TelegramCommandHandler,
    TelegramBotService,
    TelegramMessage,
    TelegramChat,
    TelegramUser,
)


@pytest.fixture
def mock_telegram_client():
    client = MagicMock(spec=TelegramClient)
    client.is_configured = True
    client.send_message = AsyncMock(return_value=True)
    client.get_me = AsyncMock(return_value={"id": 12345, "is_bot": True, "username": "jalNetra_Helperbot"})
    client.get_updates = AsyncMock(return_value=[])
    client.close = AsyncMock()
    return client


def make_msg(chat_id: int, text: str) -> TelegramMessage:
    return TelegramMessage(
        message_id=1,
        chat=TelegramChat(id=chat_id, type="private"),
        date=1729000000,
        text=text,
        from_user=TelegramUser(id=chat_id, is_bot=False, first_name="TestUser"),
    )


def test_telegram_status_endpoint(client: TestClient):
    """GET /api/v1/telegram/status returns connection status without exposing tokens."""
    resp = client.get("/api/v1/telegram/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "configured" in data
    assert "connected" in data
    assert "bot_username" in data
    assert "token" not in data
    assert "bot_token" not in data


def test_telegram_start_command(mock_telegram_client):
    """Test /start returns welcome message."""
    async def run():
        handler = TelegramCommandHandler(mock_telegram_client)
        msg = make_msg(123, "/start")
        await handler.handle_message(msg)

        mock_telegram_client.send_message.assert_called_once()
        args = mock_telegram_client.send_message.call_args[0]
        assert args[0] == 123
        assert "Welcome to JalNetra 2.0" in args[1]

    asyncio.run(run())


def test_telegram_help_command(mock_telegram_client):
    """Test /help lists all available commands."""
    async def run():
        handler = TelegramCommandHandler(mock_telegram_client)
        msg = make_msg(123, "/help")
        await handler.handle_message(msg)

        mock_telegram_client.send_message.assert_called_once()
        reply = mock_telegram_client.send_message.call_args[0][1]
        assert "/start" in reply
        assert "/help" in reply
        assert "/ping" in reply
        assert "/status" in reply
        assert "/ai <question>" in reply

    asyncio.run(run())


def test_telegram_ping_command(mock_telegram_client):
    """Test /ping returns connectivity confirmation."""
    async def run():
        handler = TelegramCommandHandler(mock_telegram_client)
        msg = make_msg(123, "/ping")
        await handler.handle_message(msg)

        mock_telegram_client.send_message.assert_called_once()
        reply = mock_telegram_client.send_message.call_args[0][1]
        assert "JalNetra Telegram Bot is working" in reply
        assert "Telegram API: OK" in reply

    asyncio.run(run())


def test_telegram_status_command(mock_telegram_client):
    """Test /status returns system status without secrets."""
    async def run():
        mock_ai = MagicMock()
        mock_ai.get_status.return_value = MagicMock(configured=True)
        handler = TelegramCommandHandler(mock_telegram_client, ai_service=mock_ai)

        msg = make_msg(123, "/status")
        await handler.handle_message(msg)

        mock_telegram_client.send_message.assert_called_once()
        reply = mock_telegram_client.send_message.call_args[0][1]
        assert "JalNetra Status" in reply
        assert "Backend: ONLINE" in reply
        assert "Telegram: CONNECTED" in reply

    asyncio.run(run())


def test_telegram_ai_command(mock_telegram_client):
    """Test /ai <question> dispatches to AI service."""
    async def run():
        mock_ai = MagicMock()
        mock_ai.generate_general_response.return_value = "JalNetra monitors lakes and reservoirs."
        handler = TelegramCommandHandler(mock_telegram_client, ai_service=mock_ai)

        msg = make_msg(123, "/ai What is JalNetra?")
        await handler.handle_message(msg)

        mock_telegram_client.send_message.assert_called_once()
        reply = mock_telegram_client.send_message.call_args[0][1]
        assert "🤖 JalNetra AI" in reply
        assert "JalNetra monitors lakes and reservoirs." in reply

    asyncio.run(run())


def test_telegram_ai_security_rejection(mock_telegram_client):
    """Verify that administrative actions via /ai are rejected as read-only."""
    async def run():
        mock_ai = MagicMock()
        handler = TelegramCommandHandler(mock_telegram_client, ai_service=mock_ai)

        msg = make_msg(123, "/ai delete database")
        await handler.handle_message(msg)

        # AI service should NOT be called
        mock_ai.generate_general_response.assert_not_called()
        mock_telegram_client.send_message.assert_called_once()
        reply = mock_telegram_client.send_message.call_args[0][1]
        assert "read-only" in reply

    asyncio.run(run())


def test_telegram_chat_authorization():
    """Verify TELEGRAM_ALLOWED_CHAT_IDS restricts access."""
    async def run():
        client = MagicMock(spec=TelegramClient)
        client.send_message = AsyncMock(return_value=True)

        with patch.object(settings, "TELEGRAM_ALLOWED_CHAT_IDS", "111,222"):
            handler = TelegramCommandHandler(client)
            assert handler.is_chat_allowed(111) is True
            assert handler.is_chat_allowed(222) is True
            assert handler.is_chat_allowed(999) is False

            # Attempt from unauthorized user
            msg = make_msg(999, "/ping")
            await handler.handle_message(msg)
            reply = client.send_message.call_args[0][1]
            assert "Unauthorized" in reply

    asyncio.run(run())


def test_telegram_bot_service_graceful_on_auth_failure():
    """When get_me returns None, bot service does not raise and connected remains False."""
    async def run():
        client = MagicMock(spec=TelegramClient)
        client.get_me = AsyncMock(return_value=None)
        client.close = AsyncMock()

        bot = TelegramBotService(client)
        with patch.object(settings, "TELEGRAM_ENABLED", True):
            with patch.object(settings, "TELEGRAM_BOT_TOKEN", "bad_token"):
                await bot.start()
                assert bot.is_connected is False
                await bot.stop()

    asyncio.run(run())
