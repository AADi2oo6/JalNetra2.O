"""
IoT Monitoring Engine.
Orchestrates active monitoring sessions: baseline collection, CSV recording,
anomaly detection, in-memory alert history, and Telegram alerting.
"""
import asyncio
from datetime import datetime, timezone
import logging
import threading
import time
import uuid
from typing import Any, List, Optional

from app.core.config import settings
from app.services.iot.models import IoTConnectionState, IoTReading
from app.services.iot.monitoring.alerts import dispatch_telegram_alert
from app.services.iot.monitoring.detector import AnomalyDetector
from app.services.iot.monitoring.models import (
    IoTAlert,
    MonitoringSessionStatus,
    StartMonitoringResponse,
    StopMonitoringResponse,
)
from app.services.iot.monitoring.storage import TemporaryMonitoringStorage
from app.services.iot.service import iot_service

logger = logging.getLogger("jalnetra.iot.monitoring")


class IoTMonitoringEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._active: bool = False
        self._session_id: Optional[str] = None
        self._water_body_id: Optional[str] = None
        self._water_body_name: str = settings.IOT_TARGET_WATER_BODY_NAME
        self._latitude: float = 19.9291418
        self._longitude: float = 75.3364885
        self._google_maps_url: str = f"https://www.google.com/maps/search/?api=1&query={self._latitude},{self._longitude}"

        self._started_at_dt: Optional[datetime] = None
        self._started_at_ts: float = 0.0
        self._sample_count: int = 0
        self._alerts: List[IoTAlert] = []

        self._storage = TemporaryMonitoringStorage()
        self._detector: Optional[AnomalyDetector] = None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active

    def start_session(
        self,
        water_body_id: str,
        water_body_name: str,
        latitude: float,
        longitude: float,
        google_maps_url: Optional[str] = None,
        force_start: bool = False,
    ) -> StartMonitoringResponse:
        """
        Start a new temporary monitoring session.
        Verifies IoT hardware is connected and clears any previous state.
        """
        # 1. Verify connection
        state, _ = iot_service.compute_connection_state()
        if state == IoTConnectionState.DISCONNECTED and not force_start:
            return StartMonitoringResponse(
                success=False,
                message="ESP32 is not connected. Connect hardware to COM6 before starting monitoring.",
                water_body_id=water_body_id,
                water_body_name=water_body_name,
            )

        with self._lock:
            # If an old session is still lingering, cleanly stop and delete its temporary data
            if self._active and self._session_id:
                logger.info("[IoT Engine] Stopping previous session %s before starting new one", self._session_id)
                self._storage.delete_session(self._session_id)

            session_id = str(uuid.uuid4())
            self._session_id = session_id
            self._water_body_id = water_body_id
            self._water_body_name = water_body_name
            self._latitude = latitude
            self._longitude = longitude
            self._google_maps_url = (
                google_maps_url or f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
            )

            now = datetime.now(timezone.utc)
            self._started_at_dt = now
            self._started_at_ts = time.time()
            self._sample_count = 0
            self._alerts.clear()

            # Start temporary CSV storage
            self._storage.start_session(session_id)

            # Initialize fresh anomaly detector
            self._detector = AnomalyDetector(
                session_id=session_id,
                water_body_id=water_body_id,
                water_body_name=water_body_name,
                latitude=latitude,
                longitude=longitude,
                google_maps_url=self._google_maps_url,
            )

            self._active = True
            logger.info(
                "[IoT Engine] Monitoring started for %s (Session ID: %s)",
                water_body_name,
                session_id,
            )

            return StartMonitoringResponse(
                success=True,
                session_id=session_id,
                water_body_id=water_body_id,
                water_body_name=water_body_name,
                message="Monitoring session started. Establishing baseline...",
            )

    def stop_session(self) -> StopMonitoringResponse:
        """
        Stop monitoring session.
        Deletes the temporary CSV file, resets all state, and clears alerts.
        """
        with self._lock:
            if not self._active:
                return StopMonitoringResponse(
                    success=True,
                    samples_recorded=0,
                    alerts_generated=0,
                    temporary_data_deleted=True,
                    message="No active monitoring session to stop.",
                )

            session_id = self._session_id or "unknown"
            samples = self._sample_count
            alert_count = len(self._alerts)

            # 1. Stop recording & delete temporary storage
            deleted = self._storage.delete_session(session_id)

            # 2. Reset all in-memory state
            self._active = False
            self._session_id = None
            self._started_at_dt = None
            self._started_at_ts = 0.0
            self._sample_count = 0
            self._alerts.clear()
            self._detector = None

            logger.info(
                "[IoT Engine] Monitoring stopped for %s. Samples: %d, Alerts: %d, Temporary CSV deleted: %s",
                self._water_body_name,
                samples,
                alert_count,
                deleted,
            )

            return StopMonitoringResponse(
                success=True,
                samples_recorded=samples,
                alerts_generated=alert_count,
                temporary_data_deleted=deleted,
                message="Monitoring stopped. Temporary session data deleted.",
            )

    def get_status(self) -> MonitoringSessionStatus:
        """Return live session monitoring statistics."""
        with self._lock:
            if not self._active:
                return MonitoringSessionStatus(
                    active=False,
                    water_body_name=self._water_body_name,
                    water_body_id=self._water_body_id,
                )

            duration = int(time.time() - self._started_at_ts)
            baseline_est = self._detector.baseline_established if self._detector else False
            baseline_prog = len(self._detector.baseline_samples) if self._detector else 0
            baseline_target = self._detector.baseline_target if self._detector else 10
            baseline_vals = self._detector.baseline_values if self._detector else None

            return MonitoringSessionStatus(
                active=True,
                session_id=self._session_id,
                water_body_id=self._water_body_id,
                water_body_name=self._water_body_name,
                started_at=self._started_at_dt.isoformat() if self._started_at_dt else None,
                duration_seconds=duration,
                sample_count=self._sample_count,
                alert_count=len(self._alerts),
                baseline_established=baseline_est,
                baseline_progress=min(baseline_prog, baseline_target),
                baseline_target=baseline_target,
                baseline_values=baseline_vals,
            )

    def get_alerts(self) -> List[IoTAlert]:
        """Return list of alerts generated during current active session."""
        with self._lock:
            return list(self._alerts)

    def process_new_reading(self, reading: IoTReading) -> None:
        """
        Called when a new sensor packet arrives from the serial reader.
        If monitoring is active, records the sample, runs anomaly detection,
        and triggers alerts if thresholds are exceeded.
        """
        with self._lock:
            if not self._active or not self._detector:
                return

            # Record sample
            self._storage.append_reading(reading)
            self._sample_count += 1

            # Run detection
            new_alerts = self._detector.process_reading(reading)
            for alert in new_alerts:
                self._alerts.insert(0, alert)  # newest first
                logger.info(
                    "[IoT Engine] 🚨 ALERT TRIGGERED: %s | %s",
                    alert.title,
                    alert.message,
                )

        # Dispatch alerts to Telegram outside lock
        if new_alerts:
            for alert in new_alerts:
                self._dispatch_alert_async(alert)

    def _dispatch_alert_async(self, alert: IoTAlert) -> None:
        """Launch background task to send alert to Telegram."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(dispatch_telegram_alert(alert))
        except RuntimeError:
            # No running event loop in thread; run in separate thread or worker
            def _send():
                asyncio.run(dispatch_telegram_alert(alert))
            t = threading.Thread(target=_send, daemon=True)
            t.start()


# Global singleton monitoring engine
iot_monitoring_engine = IoTMonitoringEngine()
