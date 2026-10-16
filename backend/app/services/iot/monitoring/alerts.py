"""
Telegram alert dispatcher for IoT monitoring anomalies.
Formats structured alert messages with geographic coordinates, Google Maps links,
and sends them to registered Telegram chats without blocking or breaking monitoring.
"""
import asyncio
from datetime import datetime
import logging
from typing import Optional, Set

from app.core.config import settings
from app.services.iot.monitoring.models import IoTAlert, IoTAlertType
from app.services.telegram.client import TelegramClient

logger = logging.getLogger("jalnetra.iot.alerts")

# Registry of discovered/active chat IDs
_active_chat_registry: Set[int] = set()


def register_chat_for_alerts(chat_id: int) -> None:
    """Register an active user chat ID so they receive real-time IoT alerts."""
    _active_chat_registry.add(chat_id)
    try:
        from app.db.database import SessionLocal
        from app.db.repositories.telegram_subscriber_repository import TelegramSubscriberRepository
        with SessionLocal() as db:
            repo = TelegramSubscriberRepository(db)
            repo.register_or_update(chat_id=chat_id, is_active=True)
    except Exception as e:
        logger.debug("Notice persisting chat into db: %s", e)


def get_target_chat_ids() -> Set[int]:
    """Get all allowed/registered chat IDs from config and active sessions."""
    targets = set(_active_chat_registry)
    raw = settings.TELEGRAM_ALLOWED_CHAT_IDS.strip()
    if raw:
        for cid in raw.split(","):
            cid_str = cid.strip()
            if cid_str:
                try:
                    targets.add(int(cid_str))
                except ValueError:
                    pass
    return targets


def format_telegram_alert(alert: IoTAlert) -> str:
    """Format alert object into structured Telegram message with safety wording and location."""
    try:
        dt = datetime.fromisoformat(alert.detected_at.replace("Z", "+00:00"))
        time_str = dt.strftime("%I:%M %p (%Y-%m-%d)")
    except Exception:
        time_str = alert.detected_at

    loc_str = f"{alert.latitude:.4f}°N, {alert.longitude:.4f}°E"

    if alert.type in (IoTAlertType.WATER_LEVEL_INCREASE, IoTAlertType.WATER_LEVEL_DECREASE):
        sign = "+" if alert.change > 0 else ""
        icon = "🔴" if alert.type == IoTAlertType.WATER_LEVEL_INCREASE else "⚠️"
        lines = [
            "🚨 JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            f"{icon} {alert.title}",
            "",
            "Water level:",
            f"{alert.previous_value:.1f}% → {alert.current_value:.1f}%",
            "",
            "Change:",
            f"{sign}{alert.change:.1f} percentage points",
            "",
            "Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "This is a real-time sensor anomaly detected by the JalNetra IoT monitoring unit.",
        ]
        return "\n".join(lines)

    elif alert.type == IoTAlertType.CLARITY_CHANGE:
        status_line = ""
        if alert.extra_details and "status_change" in alert.extra_details:
            status_line = f"\nStatus:\n{alert.extra_details['status_change']}\n"

        sign = "+" if alert.change > 0 else ""
        lines = [
            "🚨 JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "🟠 WATER CLARITY CHANGE",
            "",
            "Clarity Index:",
            f"{alert.previous_value:.1f} → {alert.current_value:.1f}",
            "",
            "Change:",
            f"{sign}{alert.change:.1f} points",
            status_line,
            "A sudden optical clarity change was detected.",
            "",
            "Note: Optical clarity is a relative sensor index, not a laboratory NTU or toxicity measurement.",
            "",
            "Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "This is a real-time sensor anomaly detected by the JalNetra IoT monitoring unit.",
        ]
        return "\n".join(lines)

    elif alert.type == IoTAlertType.TEMPERATURE_CHANGE:
        sign = "+" if alert.change > 0 else ""
        lines = [
            "🌡️ JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "TEMPERATURE CHANGE",
            "",
            "Temperature:",
            f"{alert.previous_value:.1f}°C → {alert.current_value:.1f}°C",
            "",
            "Change:",
            f"{sign}{alert.change:.1f}°C",
            "",
            "A sudden temperature change was detected.",
            "",
            "Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "This is a real-time sensor anomaly detected by the JalNetra IoT monitoring unit.",
        ]
        return "\n".join(lines)

    elif alert.type == IoTAlertType.TDS_CHANGE:
        pct = alert.extra_details.get("percentage_change", alert.change) if alert.extra_details else alert.change
        sign = "+" if pct > 0 else ""
        lines = [
            "⚠️ JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "TDS CHANGE",
            "",
            "Estimated TDS:",
            f"{alert.previous_value:.1f} → {alert.current_value:.1f} ppm",
            "",
            "Change:",
            f"{sign}{pct:.1f}%",
            "",
            "A sudden change in the estimated TDS reading was detected.",
            "",
            "Note:",
            "This is a sensor-derived TDS estimate and should not be treated as a laboratory water-quality measurement.",
            "",
            "Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
        ]
        return "\n".join(lines)

    # Fallback
    return f"🚨 JALNETRA IoT ALERT: {alert.title}\n{alert.message}\n📍 {alert.water_body_name}"


async def dispatch_telegram_alert(alert: IoTAlert, client: Optional[TelegramClient] = None) -> int:
    """
    Sends the alert to all registered and active Telegram subscribers.
    Returns number of successful deliveries.
    Exceptions are caught and logged so Telegram failure NEVER stops monitoring.
    """
    try:
        from app.services.telegram.alert_broadcaster import telegram_alert_broadcaster
        res = await telegram_alert_broadcaster.broadcast_alert(alert, client_override=client)
        return res.get("successful", 0)
    except Exception as e:
        logger.error("[IoT Alerts] Error in telegram broadcaster delegation: %s", e)
        return 0
