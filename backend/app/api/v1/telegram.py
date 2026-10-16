import logging
from fastapi import APIRouter
from typing import Any, Dict
from app.services.telegram import telegram_bot_service, TelegramStatusResponse
from app.services.telegram.alert_broadcaster import telegram_alert_broadcaster

logger = logging.getLogger("jalnetra.api.telegram")
router = APIRouter(prefix="/telegram", tags=["Telegram Bot"])


@router.get(
    "/status",
    response_model=TelegramStatusResponse,
    summary="Get Telegram bot connection and configuration status",
    description="Returns whether the Telegram bot is enabled, configured, and actively connected. Never exposes tokens.",
)
def get_telegram_status() -> TelegramStatusResponse:
    return telegram_bot_service.get_status()


@router.get(
    "/alerts/status",
    summary="Get Telegram alert broadcast status and active subscriber count",
    description="Returns active subscriber count and last broadcast statistics without exposing private chat IDs.",
)
def get_telegram_alerts_status() -> Dict[str, Any]:
    return telegram_alert_broadcaster.get_broadcast_status()


@router.post(
    "/alerts/test",
    summary="Send test alert notification to all active Telegram subscribers",
    description="Sends a benign test alert notification to verified subscribers for diagnostic purposes.",
)
async def post_test_telegram_alert() -> Dict[str, Any]:
    return await telegram_alert_broadcaster.send_test_alert()
