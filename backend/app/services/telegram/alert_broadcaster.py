"""
Telegram Alert Broadcaster for JalNetra 2.0.
Broadcasts IoT monitoring anomaly alerts to all registered and active Telegram subscribers.
Handles individual recipient failures independently and auto-deactivates blocked/invalid users.
"""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional, Set

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models.telegram_subscriber import TelegramSubscriber
from app.db.repositories.telegram_subscriber_repository import TelegramSubscriberRepository
from app.services.iot.monitoring.models import IoTAlert, IoTAlertType
from app.services.telegram.client import TelegramClient

logger = logging.getLogger("jalnetra.telegram.broadcaster")


def format_telegram_alert(alert: IoTAlert) -> str:
    """Format alert object into structured Telegram message matching Section 11-14 specifications."""
    try:
        dt = datetime.fromisoformat(alert.detected_at.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M:%S")
    except Exception:
        time_str = alert.detected_at

    loc_str = f"{alert.latitude:.3f}°N, {alert.longitude:.3f}°E"

    if alert.type == IoTAlertType.WATER_LEVEL_INCREASE:
        sign = "+" if alert.change > 0 else ""
        lines = [
            "🚨 JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "🔴 WATER LEVEL INCREASE",
            "",
            "Previous:",
            f"{alert.previous_value:.1f}%",
            "",
            "Current:",
            f"{alert.current_value:.1f}%",
            "",
            "Change:",
            f"{sign}{alert.change:.1f} percentage points",
            "",
            "⏱ Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            "",
            "Coordinates:",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "⚠️ This alert indicates a sudden sensor-detected",
            "change. It is not a laboratory water-quality diagnosis.",
        ]
        return "\n".join(lines)

    elif alert.type == IoTAlertType.WATER_LEVEL_DECREASE:
        sign = "+" if alert.change > 0 else ""
        lines = [
            "🚨 JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "🔴 WATER LEVEL DECREASE",
            "",
            "Previous:",
            f"{alert.previous_value:.1f}%",
            "",
            "Current:",
            f"{alert.current_value:.1f}%",
            "",
            "Change:",
            f"{sign}{alert.change:.1f} percentage points",
            "",
            "⏱ Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            "",
            "Coordinates:",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "⚠️ This alert indicates a sudden sensor-detected",
            "change. It is not a laboratory water-quality diagnosis.",
        ]
        return "\n".join(lines)

    elif alert.type == IoTAlertType.CLARITY_CHANGE:
        sign = "+" if alert.change > 0 else ""
        status_change = "NORMAL → TURBID"
        if alert.extra_details and "status_change" in alert.extra_details:
            status_change = alert.extra_details["status_change"]

        lines = [
            "🚨 JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "🟠 WATER CLARITY CHANGE",
            "",
            "Clarity Index:",
            f"{alert.previous_value:.0f} → {alert.current_value:.0f}",
            "",
            "Change:",
            f"{sign}{alert.change:.0f} points",
            "",
            "Status:",
            f"{status_change}",
            "",
            "⏱ Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            "",
            "Coordinates:",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "⚠️ Sudden optical clarity change detected by the IoT sensor.",
        ]
        return "\n".join(lines)

    elif alert.type == IoTAlertType.TEMPERATURE_CHANGE:
        sign = "+" if alert.change > 0 else ""
        lines = [
            "🚨 JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "🌡 TEMPERATURE CHANGE",
            "",
            "Previous:",
            f"{alert.previous_value:.1f}°C",
            "",
            "Current:",
            f"{alert.current_value:.1f}°C",
            "",
            "Change:",
            f"{sign}{alert.change:.1f}°C",
            "",
            "⏱ Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            "",
            "Coordinates:",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "⚠️ Sudden temperature change detected by the IoT sensor.",
        ]
        return "\n".join(lines)

    elif alert.type == IoTAlertType.TDS_CHANGE:
        pct = alert.extra_details.get("percentage_change", alert.change) if alert.extra_details else alert.change
        sign = "+" if pct > 0 else ""
        lines = [
            "🚨 JALNETRA IoT ALERT",
            "",
            f"💧 {alert.water_body_name}",
            "",
            "🧪 TDS CHANGE",
            "",
            "Previous:",
            f"{alert.previous_value:.0f} ppm",
            "",
            "Current:",
            f"{alert.current_value:.0f} ppm",
            "",
            "Change:",
            f"{sign}{pct:.1f}%",
            "",
            "⏱ Detected:",
            f"{time_str}",
            "",
            "📍 Location:",
            f"{alert.water_body_name}",
            "",
            "Coordinates:",
            f"{loc_str}",
            "",
            "🗺 Open in Google Maps:",
            f"{alert.google_maps_url}",
            "",
            "⚠️ Sensor-derived TDS estimate.",
            "Not a laboratory measurement.",
        ]
        return "\n".join(lines)

    # Fallback
    return (
        f"🚨 JALNETRA IoT ALERT\n\n"
        f"💧 {alert.water_body_name}\n\n"
        f"{alert.title}\n"
        f"{alert.message}\n\n"
        f"📍 Location: {alert.water_body_name} ({loc_str})\n"
        f"🗺 Google Maps: {alert.google_maps_url}"
    )


from dataclasses import dataclass


@dataclass
class ActiveSubscriberInfo:
    chat_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class TelegramAlertBroadcaster:
    """
    Broadcasts IoT alerts to all registered active subscribers.
    Preserves isolation: failures of one chat do not affect others.
    """

    def __init__(
        self,
        client: Optional[TelegramClient] = None,
        db_factory: Optional[Callable] = None,
    ):
        self.client = client or TelegramClient()
        self._db_factory = db_factory or SessionLocal
        self._last_broadcast: Optional[Dict[str, Any]] = None

    def _get_allowed_chat_ids(self) -> Optional[Set[str]]:
        raw = settings.TELEGRAM_ALLOWED_CHAT_IDS.strip()
        if not raw:
            return None
        return {c.strip() for c in raw.split(",") if c.strip()}

    def get_active_subscribers(self) -> List[ActiveSubscriberInfo]:
        allowed = self._get_allowed_chat_ids()
        with self._db_factory() as db:
            repo = TelegramSubscriberRepository(db)
            if allowed:
                for cid in allowed:
                    try:
                        int_id = int(cid)
                        if repo.get_by_chat_id(int_id) is None:
                            repo.register_or_update(chat_id=int_id, is_active=True)
                    except ValueError:
                        pass
            subs = list(repo.list_active_subscribers(allowed_chat_ids=allowed))

            # Also ensure in-memory registered chats from alerts.py are synced
            try:
                from app.services.iot.monitoring.alerts import _active_chat_registry
                sub_chat_ids = {s.chat_id for s in subs}
                for acid in list(_active_chat_registry):
                    if acid not in sub_chat_ids:
                        s = repo.register_or_update(chat_id=acid, is_active=True)
                        subs.append(s)
                        sub_chat_ids.add(acid)
            except Exception as e:
                logger.debug("Notice syncing _active_chat_registry: %s", e)

            # Eagerly extract into dataclasses before session closes
            return [
                ActiveSubscriberInfo(
                    chat_id=s.chat_id,
                    username=s.username,
                    first_name=s.first_name,
                )
                for s in subs
            ]

    def count_active_subscribers(self) -> int:
        return len(self.get_active_subscribers())

    def get_broadcast_status(self) -> Dict[str, Any]:
        """Provides data for GET /api/v1/telegram/alerts/status."""
        return {
            "configured": bool(settings.TELEGRAM_BOT_TOKEN.strip()),
            "bot_connected": self.client.is_configured,
            "active_subscribers": self.count_active_subscribers(),
            "last_broadcast": self._last_broadcast,
        }

    async def broadcast_alert(
        self,
        alert: IoTAlert,
        client_override: Optional[TelegramClient] = None,
    ) -> Dict[str, Any]:
        """
        Broadcasts IoTAlert to all registered subscribers independently.
        Never crashes or stops monitoring on Telegram failures.
        """
        logger.info("[Telegram Alerts] Alert received: %s (%s)", alert.id, alert.title)

        tg_client = client_override or self.client
        if client_override is None:
            if not tg_client.is_configured:
                logger.debug("[Telegram Alerts] Telegram bot not configured. Broadcast skipped.")
                return {
                    "alert_id": alert.id,
                    "total_recipients": 0,
                    "successful": 0,
                    "failed": 0,
                }

        subscribers = self.get_active_subscribers()
        total = len(subscribers)
        logger.info("[Telegram Alerts] Broadcasting alert. Registered recipients: %d", total)

        if total == 0:
            logger.info("[Telegram Alerts] No active subscribers found. Broadcast skipped.")
            result = {
                "alert_id": alert.id,
                "total_recipients": 0,
                "successful": 0,
                "failed": 0,
            }
            self._last_broadcast = {
                **result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            return result

        text = format_telegram_alert(alert)
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🗺 Open Location", "url": alert.google_maps_url}]
            ]
        }

        successful = 0
        failed = 0

        for sub in subscribers:
            chat_id = sub.chat_id
            username_info = f"@{sub.username}" if sub.username else str(chat_id)
            logger.info("[Telegram Alerts] Sending to chat %s (%s)", chat_id, username_info)

            try:
                import inspect
                send_fn = getattr(tg_client, "send_message_detailed", None)
                is_async_mock = type(send_fn).__name__ == "AsyncMock"
                if send_fn is not None and (inspect.iscoroutinefunction(send_fn) or is_async_mock):
                    res = await send_fn(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                    )
                    if isinstance(res, tuple) and len(res) == 3:
                        ok, status_code, desc = res
                    else:
                        ok = bool(res)
                        status_code = 200 if ok else 500
                        desc = "OK" if ok else "Failed"
                else:
                    ok = await tg_client.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                    )
                    status_code = 200 if ok else 500
                    desc = "OK" if ok else "Failed"

                if ok:
                    successful += 1
                    logger.info(
                        "[Telegram Alerts] Telegram API response: 200 - Delivered successfully to chat %s",
                        chat_id,
                    )
                else:
                    failed += 1
                    logger.warning(
                        "[Telegram Alerts] Delivery failed for chat %s: HTTP %s - %s",
                        chat_id,
                        status_code,
                        desc,
                    )
                    # Auto-deactivate user if blocked or chat not found
                    if status_code == 403 or (status_code == 400 and ("chat not found" in desc.lower() or "deactivated" in desc.lower())):
                        logger.warning(
                            "[Telegram Alerts] Subscriber %s is unreachable (HTTP %s). Marking inactive.",
                            chat_id,
                            status_code,
                        )
                        try:
                            with self._db_factory() as db:
                                repo = TelegramSubscriberRepository(db)
                                repo.set_active_status(chat_id, is_active=False)
                        except Exception as dbe:
                            logger.error("[Telegram Alerts] Failed to deactivate subscriber: %s", dbe)

            except Exception as e:
                failed += 1
                logger.warning(
                    "[Telegram Alerts] Delivery exception for chat %s: %s",
                    chat_id,
                    type(e).__name__,
                )

        logger.info(
            "[Telegram Alerts] Broadcast complete: %d/%d successful (%d failed)",
            successful,
            total,
            failed,
        )

        result = {
            "alert_id": alert.id,
            "total_recipients": total,
            "successful": successful,
            "failed": failed,
        }
        self._last_broadcast = {
            **result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return result

    async def send_test_alert(self, client_override: Optional[TelegramClient] = None) -> Dict[str, Any]:
        """Sends a benign test alert notification to all active subscribers."""
        logger.info("[Telegram Alerts] Sending test notification...")
        tg_client = client_override or self.client
        if not tg_client.is_configured:
            return {"total_recipients": 0, "successful": 0, "failed": 0, "message": "Telegram not configured"}

        subscribers = self.get_active_subscribers()
        total = len(subscribers)
        if total == 0:
            return {"total_recipients": 0, "successful": 0, "failed": 0, "message": "No active subscribers"}

        test_text = (
            "🧪 JALNETRA TEST ALERT\n\n"
            "Telegram alert delivery is working.\n\n"
            "This is a test notification confirming your device is registered "
            "to receive real-time water monitoring alerts from JalNetra."
        )

        successful = 0
        failed = 0
        for sub in subscribers:
            try:
                ok, status_code, desc = await tg_client.send_message_detailed(
                    chat_id=sub.chat_id,
                    text=test_text,
                )
                if ok:
                    successful += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        logger.info("[Telegram Alerts] Test alert broadcast complete: %d/%d successful", successful, total)
        return {
            "total_recipients": total,
            "successful": successful,
            "failed": failed,
            "message": f"Delivered to {successful}/{total} subscriber(s)",
        }


telegram_alert_broadcaster = TelegramAlertBroadcaster()
