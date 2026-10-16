"""
In-memory IoT State Service.
Maintains the latest reading received from the ESP32 and provides connection state tracking.
"""
from datetime import datetime, timezone
import logging
import threading
from typing import Optional

from app.core.config import settings
from app.services.iot.models import (
    IoTConnectionState,
    IoTReading,
    IoTStatusInfo,
    IoTLatestResponse,
)

logger = logging.getLogger("jalnetra.iot")


class IoTService:
    def __init__(self):
        self._lock = threading.Lock()
        self._latest_reading: Optional[IoTReading] = None
        self._port_connected: bool = False
        self._last_received_datetime: Optional[datetime] = None
        self._subscribers = []

    def register_reading_subscriber(self, callback) -> None:
        """Register a callback invoked whenever a new reading arrives."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def update_reading(self, reading: IoTReading) -> None:
        """Update the in-memory latest reading in a thread-safe manner and notify subscribers."""
        with self._lock:
            self._latest_reading = reading
            self._last_received_datetime = datetime.now(timezone.utc)
            self._port_connected = True
            subs = list(self._subscribers)

        for callback in subs:
            try:
                callback(reading)
            except Exception as exc:
                logger.error("[IoT] Error invoking reading subscriber: %s", exc)

    def set_port_connected(self, connected: bool) -> None:
        """Set hardware serial port connectivity state."""
        with self._lock:
            self._port_connected = connected

    def get_latest_reading(self) -> Optional[IoTReading]:
        """Return raw latest reading if present."""
        with self._lock:
            return self._latest_reading

    def compute_connection_state(self) -> tuple[IoTConnectionState, Optional[float]]:
        """
        Calculates status based on freshness of latest reading:
          - <= 5 seconds: CONNECTED
          - > 5s and <= 15 seconds: STALE
          - > 15 seconds or no reading: DISCONNECTED
        """
        with self._lock:
            if not self._last_received_datetime or not self._latest_reading:
                return IoTConnectionState.DISCONNECTED, None

            elapsed = (datetime.now(timezone.utc) - self._last_received_datetime).total_seconds()
            if elapsed <= 5.0:
                return IoTConnectionState.CONNECTED, round(elapsed, 1)
            elif elapsed <= 15.0:
                return IoTConnectionState.STALE, round(elapsed, 1)
            else:
                return IoTConnectionState.DISCONNECTED, round(elapsed, 1)

    def get_status(self) -> IoTStatusInfo:
        """Return the current device and connection status."""
        state, elapsed = self.compute_connection_state()
        with self._lock:
            last_received = self._latest_reading.received_at if self._latest_reading else None
            device_name = self._latest_reading.device if self._latest_reading else "jalnetra_iot"

            return IoTStatusInfo(
                enabled=settings.IOT_ENABLED,
                connected=(state == IoTConnectionState.CONNECTED),
                port=settings.IOT_SERIAL_PORT,
                baud_rate=settings.IOT_SERIAL_BAUDRATE,
                device=device_name,
                status=state,
                last_received_at=last_received,
                seconds_since_last_reading=elapsed,
                target_water_body_name=settings.IOT_TARGET_WATER_BODY_NAME,
            )

    def get_latest_response(self) -> IoTLatestResponse:
        """Return structured response suitable for GET /api/v1/iot/latest."""
        state, elapsed = self.compute_connection_state()
        with self._lock:
            if not self._latest_reading:
                return IoTLatestResponse(
                    available=False,
                    status=IoTConnectionState.DISCONNECTED,
                    target_water_body_name=settings.IOT_TARGET_WATER_BODY_NAME,
                    message="No IoT reading received yet.",
                )

            r = self._latest_reading
            return IoTLatestResponse(
                available=True,
                device=r.device,
                temperature_c=r.temperature_c,
                temperature_valid=r.temperature_valid,
                turbidity_raw=r.turbidity_raw,
                clarity_index=r.clarity_index,
                turbidity_status=r.turbidity_status,
                tds_raw=r.tds_raw,
                tds_ppm=r.tds_ppm,
                water_level_raw=r.water_level_raw,
                water_level_percent=r.water_level_percent,
                received_at=r.received_at,
                status=state,
                seconds_ago=elapsed,
                target_water_body_name=settings.IOT_TARGET_WATER_BODY_NAME,
            )

    def reset(self) -> None:
        """Reset service state (primarily for automated testing)."""
        with self._lock:
            self._latest_reading = None
            self._last_received_datetime = None
            self._port_connected = False


iot_service = IoTService()
