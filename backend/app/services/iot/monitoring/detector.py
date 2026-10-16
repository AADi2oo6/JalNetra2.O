"""
Sudden-change anomaly detector for IoT live monitoring.
Calculates initial baseline, maintains a rolling window, checks configurable thresholds,
and enforces cooldown and re-arming hysteresis.
"""
from collections import deque
from datetime import datetime, timezone
import logging
import statistics
import time
import uuid
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.iot.models import IoTReading
from app.services.iot.monitoring.models import (
    IoTAlert,
    IoTAlertSeverity,
    IoTAlertType,
)

logger = logging.getLogger("jalnetra.iot.detector")


class AnomalyDetector:
    def __init__(
        self,
        session_id: str,
        water_body_id: str,
        water_body_name: str,
        latitude: float,
        longitude: float,
        google_maps_url: str,
        baseline_target: Optional[int] = None,
    ):
        self.session_id = session_id
        self.water_body_id = water_body_id
        self.water_body_name = water_body_name
        self.latitude = latitude
        self.longitude = longitude
        self.google_maps_url = google_maps_url

        self.baseline_target = baseline_target or settings.IOT_ALERT_BASELINE_SAMPLE_COUNT
        self.baseline_samples: List[IoTReading] = []
        self.baseline_established: bool = False
        self.baseline_values: Dict[str, float] = {}

        # Rolling window of recent readings: (timestamp_float, IoTReading)
        self.window_seconds: int = settings.IOT_ALERT_WINDOW_SECONDS
        self.rolling_window: deque[Tuple[float, IoTReading]] = deque()

        # Cooldown & Hysteresis tracking per alert type
        self.cooldown_seconds: int = settings.IOT_ALERT_COOLDOWN_SECONDS
        self.last_alert_times: Dict[IoTAlertType, float] = {}
        self.in_alarm_states: Dict[IoTAlertType, bool] = {
            t: False for t in IoTAlertType
        }

    def process_reading(self, reading: IoTReading) -> List[IoTAlert]:
        """
        Process a new reading through baseline accumulation or rolling-window anomaly detection.
        Returns a list of any newly triggered alerts.
        """
        now_ts = time.time()

        # ── Phase A: Establishing Baseline ─────────────────────────────────────
        if not self.baseline_established:
            self.baseline_samples.append(reading)
            if len(self.baseline_samples) >= self.baseline_target:
                self._compute_baseline()
            # No alerts during baseline establishment
            return []

        # ── Phase B: Maintain Rolling Window ───────────────────────────────────
        self.rolling_window.append((now_ts, reading))
        # Purge entries older than window_seconds
        cutoff = now_ts - self.window_seconds
        while self.rolling_window and self.rolling_window[0][0] < cutoff:
            self.rolling_window.popleft()

        # Recent readings excluding the newest one, falling back to baseline samples when rolling window is just starting
        past_window = [r for _, r in list(self.rolling_window)[:-1]]
        if not past_window:
            past_window = self.baseline_samples

        if not past_window:
            return []

        alerts: List[IoTAlert] = []

        # 1. Water Level Check
        wl_alert = self._check_water_level(reading, past_window, now_ts)
        if wl_alert:
            alerts.append(wl_alert)

        # 2. Turbidity / Clarity Check
        clarity_alert = self._check_clarity(reading, past_window, now_ts)
        if clarity_alert:
            alerts.append(clarity_alert)

        # 3. Temperature Check
        temp_alert = self._check_temperature(reading, past_window, now_ts)
        if temp_alert:
            alerts.append(temp_alert)

        # 4. TDS Check
        tds_alert = self._check_tds(reading, past_window, now_ts)
        if tds_alert:
            alerts.append(tds_alert)

        return alerts

    def _compute_baseline(self) -> None:
        """Calculate median baseline from initial samples."""
        temps = [r.temperature_c for r in self.baseline_samples if r.temperature_valid]
        clarities = [r.clarity_index for r in self.baseline_samples]
        wlevels = [r.water_level_percent for r in self.baseline_samples]
        tds_vals = [r.tds_ppm for r in self.baseline_samples]

        self.baseline_values = {
            "temperature_c": round(statistics.median(temps), 2) if temps else 25.0,
            "clarity_index": round(statistics.median(clarities), 2),
            "water_level_percent": round(statistics.median(wlevels), 2),
            "tds_ppm": round(statistics.median(tds_vals), 2),
        }
        self.baseline_established = True
        logger.info(
            "[IoT Detector] Baseline established for %s: %s",
            self.water_body_name,
            self.baseline_values,
        )

    def _is_cooling_down(self, alert_type: IoTAlertType, now_ts: float) -> bool:
        last = self.last_alert_times.get(alert_type)
        if last is None:
            return False
        return (now_ts - last) < self.cooldown_seconds

    # ─── Individual Sensor Checks ─────────────────────────────────────────────

    def _check_water_level(
        self, current: IoTReading, past: List[IoTReading], now_ts: float
    ) -> Optional[IoTAlert]:
        recent_median = statistics.median([r.water_level_percent for r in past])
        diff = current.water_level_percent - recent_median
        threshold = settings.IOT_ALERT_WATER_LEVEL_CHANGE_PERCENT

        # Re-arm hysteresis check
        base_val = self.baseline_values.get("water_level_percent", recent_median)
        if abs(current.water_level_percent - base_val) < (threshold * 0.5):
            self.in_alarm_states[IoTAlertType.WATER_LEVEL_INCREASE] = False
            self.in_alarm_states[IoTAlertType.WATER_LEVEL_DECREASE] = False

        if diff >= threshold:
            alert_type = IoTAlertType.WATER_LEVEL_INCREASE
            if self._is_cooling_down(alert_type, now_ts) or self.in_alarm_states[alert_type]:
                return None

            severity = IoTAlertSeverity.HIGH if diff >= 10.0 else IoTAlertSeverity.WARNING
            self.last_alert_times[alert_type] = now_ts
            self.in_alarm_states[alert_type] = True

            return IoTAlert(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                water_body_id=self.water_body_id,
                water_body_name=self.water_body_name,
                type=alert_type,
                severity=severity,
                title="WATER LEVEL INCREASE",
                message=f"Water level: {recent_median:.1f}% → {current.water_level_percent:.1f}% (+{diff:.1f} percentage points)",
                sensor_name="Water Level",
                previous_value=round(recent_median, 1),
                current_value=round(current.water_level_percent, 1),
                change=round(diff, 1),
                unit="%",
                detected_at=datetime.now(timezone.utc).isoformat(),
                latitude=self.latitude,
                longitude=self.longitude,
                google_maps_url=self.google_maps_url,
                extra_details={
                    "possible_cause": "Rapid change detected by the IoT water-level sensor."
                },
            )

        elif diff <= -threshold:
            alert_type = IoTAlertType.WATER_LEVEL_DECREASE
            if self._is_cooling_down(alert_type, now_ts) or self.in_alarm_states[alert_type]:
                return None

            severity = IoTAlertSeverity.HIGH if abs(diff) >= 10.0 else IoTAlertSeverity.WARNING
            self.last_alert_times[alert_type] = now_ts
            self.in_alarm_states[alert_type] = True

            return IoTAlert(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                water_body_id=self.water_body_id,
                water_body_name=self.water_body_name,
                type=alert_type,
                severity=severity,
                title="WATER LEVEL DECREASE",
                message=f"Water level: {recent_median:.1f}% → {current.water_level_percent:.1f}% ({diff:.1f} percentage points)",
                sensor_name="Water Level",
                previous_value=round(recent_median, 1),
                current_value=round(current.water_level_percent, 1),
                change=round(diff, 1),
                unit="%",
                detected_at=datetime.now(timezone.utc).isoformat(),
                latitude=self.latitude,
                longitude=self.longitude,
                google_maps_url=self.google_maps_url,
                extra_details={
                    "possible_cause": "Rapid water level drop detected by the IoT sensor."
                },
            )

        return None

    def _check_clarity(
        self, current: IoTReading, past: List[IoTReading], now_ts: float
    ) -> Optional[IoTAlert]:
        recent_median = statistics.median([r.clarity_index for r in past])
        diff = current.clarity_index - recent_median
        threshold = settings.IOT_ALERT_CLARITY_CHANGE_PERCENT

        # Re-arm hysteresis check
        base_val = self.baseline_values.get("clarity_index", recent_median)
        if abs(current.clarity_index - base_val) < (threshold * 0.5):
            self.in_alarm_states[IoTAlertType.CLARITY_CHANGE] = False

        if abs(diff) >= threshold:
            alert_type = IoTAlertType.CLARITY_CHANGE
            if self._is_cooling_down(alert_type, now_ts) or self.in_alarm_states[alert_type]:
                return None

            severity = IoTAlertSeverity.HIGH if abs(diff) >= 35.0 else IoTAlertSeverity.WARNING
            self.last_alert_times[alert_type] = now_ts
            self.in_alarm_states[alert_type] = True

            # Past status from past reading
            past_status = past[-1].turbidity_status if past else "UNKNOWN"

            direction = "deteriorated" if diff < 0 else "improved"
            return IoTAlert(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                water_body_id=self.water_body_id,
                water_body_name=self.water_body_name,
                type=alert_type,
                severity=severity,
                title="TURBIDITY / CLARITY CHANGE",
                message=f"Clarity Index: {recent_median:.1f} → {current.clarity_index:.1f} ({diff:+.1f} points). Status: {past_status} → {current.turbidity_status}",
                sensor_name="Clarity Index",
                previous_value=round(recent_median, 1),
                current_value=round(current.clarity_index, 1),
                change=round(diff, 1),
                unit="points",
                detected_at=datetime.now(timezone.utc).isoformat(),
                latitude=self.latitude,
                longitude=self.longitude,
                google_maps_url=self.google_maps_url,
                extra_details={
                    "status_change": f"{past_status} → {current.turbidity_status}",
                    "direction": direction,
                    "clarity_note": "A sudden change in optical clarity was detected. Optical clarity is a relative sensor index, not a laboratory NTU or toxicity measurement.",
                },
            )

        return None

    def _check_temperature(
        self, current: IoTReading, past: List[IoTReading], now_ts: float
    ) -> Optional[IoTAlert]:
        if not current.temperature_valid:
            return None

        valid_past = [r.temperature_c for r in past if r.temperature_valid]
        if not valid_past:
            valid_past = [r.temperature_c for r in self.baseline_samples if r.temperature_valid]
        if not valid_past:
            return None

        recent_median = statistics.median(valid_past)
        diff = current.temperature_c - recent_median
        threshold = settings.IOT_ALERT_TEMPERATURE_CHANGE_C

        # Re-arm hysteresis check
        base_val = self.baseline_values.get("temperature_c", recent_median)
        if abs(current.temperature_c - base_val) < (threshold * 0.5):
            self.in_alarm_states[IoTAlertType.TEMPERATURE_CHANGE] = False

        if abs(diff) >= threshold:
            alert_type = IoTAlertType.TEMPERATURE_CHANGE
            if self._is_cooling_down(alert_type, now_ts) or self.in_alarm_states[alert_type]:
                return None

            severity = IoTAlertSeverity.HIGH if abs(diff) >= 5.0 else IoTAlertSeverity.WARNING
            self.last_alert_times[alert_type] = now_ts
            self.in_alarm_states[alert_type] = True

            return IoTAlert(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                water_body_id=self.water_body_id,
                water_body_name=self.water_body_name,
                type=alert_type,
                severity=severity,
                title="TEMPERATURE CHANGE",
                message=f"Temperature: {recent_median:.1f}°C → {current.temperature_c:.1f}°C ({diff:+.1f}°C)",
                sensor_name="Temperature",
                previous_value=round(recent_median, 1),
                current_value=round(current.temperature_c, 1),
                change=round(diff, 1),
                unit="°C",
                detected_at=datetime.now(timezone.utc).isoformat(),
                latitude=self.latitude,
                longitude=self.longitude,
                google_maps_url=self.google_maps_url,
                extra_details={
                    "note": "A sudden temperature change was detected by the IoT sensor."
                },
            )

        return None

    def _check_tds(
        self, current: IoTReading, past: List[IoTReading], now_ts: float
    ) -> Optional[IoTAlert]:
        valid_past = [r.tds_ppm for r in past if r.tds_ppm > 0]
        if not valid_past:
            valid_past = [r.tds_ppm for r in self.baseline_samples if r.tds_ppm > 0]
        if not valid_past or current.tds_ppm <= 0:
            return None

        recent_median = statistics.median(valid_past)
        if recent_median <= 0:
            return None

        pct_change = ((current.tds_ppm - recent_median) / recent_median) * 100.0
        threshold = settings.IOT_ALERT_TDS_CHANGE_PERCENT

        # Re-arm hysteresis check
        base_val = self.baseline_values.get("tds_ppm", recent_median)
        if base_val > 0 and abs(current.tds_ppm - base_val) / base_val * 100.0 < (threshold * 0.5):
            self.in_alarm_states[IoTAlertType.TDS_CHANGE] = False

        if abs(pct_change) >= threshold:
            alert_type = IoTAlertType.TDS_CHANGE
            if self._is_cooling_down(alert_type, now_ts) or self.in_alarm_states[alert_type]:
                return None

            severity = IoTAlertSeverity.WARNING
            self.last_alert_times[alert_type] = now_ts
            self.in_alarm_states[alert_type] = True

            diff = current.tds_ppm - recent_median
            return IoTAlert(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                water_body_id=self.water_body_id,
                water_body_name=self.water_body_name,
                type=alert_type,
                severity=severity,
                title="TDS CHANGE",
                message=f"Estimated TDS: {recent_median:.1f} → {current.tds_ppm:.1f} ppm ({pct_change:+.1f}%)",
                sensor_name="Estimated TDS",
                previous_value=round(recent_median, 1),
                current_value=round(current.tds_ppm, 1),
                change=round(diff, 1),
                unit="ppm",
                detected_at=datetime.now(timezone.utc).isoformat(),
                latitude=self.latitude,
                longitude=self.longitude,
                google_maps_url=self.google_maps_url,
                extra_details={
                    "percentage_change": round(pct_change, 1),
                    "note": "This is a sensor-derived TDS estimate and should not be treated as a laboratory water-quality measurement.",
                },
            )

        return None
