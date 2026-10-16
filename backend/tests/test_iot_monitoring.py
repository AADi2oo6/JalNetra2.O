"""
Unit and integration tests for IoT Live Monitoring and Alert System (Phase 2).
Tests baseline accumulation, anomaly detection, cooldown, re-arming,
temporary CSV lifecycle & deletion, Telegram alert dispatch, and REST API.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.iot.models import IoTReading
from app.services.iot.monitoring.alerts import (
    dispatch_telegram_alert,
    format_telegram_alert,
    register_chat_for_alerts,
)
from app.services.iot.monitoring.detector import AnomalyDetector
from app.services.iot.monitoring.engine import IoTMonitoringEngine
from app.services.iot.monitoring.models import (
    IoTAlert,
    IoTAlertSeverity,
    IoTAlertType,
)
from app.services.iot.monitoring.storage import TemporaryMonitoringStorage
from app.services.iot.service import IoTService


def make_sample_reading(
    temp: float = 28.0,
    clarity: float = 70.0,
    wlevel: float = 72.0,
    tds: float = 200.0,
    temp_valid: bool = True,
    status: str = "NORMAL",
) -> IoTReading:
    return IoTReading(
        device="jalnetra_iot",
        temperature_c=temp,
        temperature_valid=temp_valid,
        turbidity_raw=1800,
        clarity_index=clarity,
        turbidity_status=status,
        tds_raw=1000,
        tds_ppm=tds,
        water_level_raw=1500,
        water_level_percent=wlevel,
        received_at=datetime.now(timezone.utc).isoformat(),
    )


def test_baseline_establishment_and_suppression():
    """Verify that first 10 samples establish baseline median without firing alerts."""
    detector = AnomalyDetector(
        session_id="test-session-1",
        water_body_id="wb-1",
        water_body_name="Harsul Reservoir",
        latitude=19.9291,
        longitude=75.3365,
        google_maps_url="https://maps.google.com/?q=19.9291,75.3365",
        baseline_target=10,
    )

    # Feed 9 normal readings
    for i in range(9):
        alerts = detector.process_reading(make_sample_reading(wlevel=72.0 + (i * 0.1)))
        assert len(alerts) == 0
        assert detector.baseline_established is False

    # 10th reading: even if it has an anomaly, baseline is just completed so no alert during baseline
    alerts = detector.process_reading(make_sample_reading(wlevel=72.5))
    assert len(alerts) == 0
    assert detector.baseline_established is True
    assert "water_level_percent" in detector.baseline_values
    assert 72.0 <= detector.baseline_values["water_level_percent"] <= 73.0


def test_water_level_increase_and_decrease_detection():
    """Verify sudden water level changes trigger alerts with proper severity."""
    detector = AnomalyDetector(
        session_id="test-session-2",
        water_body_id="wb-1",
        water_body_name="Harsul Reservoir",
        latitude=19.9291,
        longitude=75.3365,
        google_maps_url="https://maps.google.com/?q=19.9291,75.3365",
        baseline_target=5,
    )
    # Establish baseline of 5 samples around 70%
    for _ in range(5):
        detector.process_reading(make_sample_reading(wlevel=70.0))
    assert detector.baseline_established is True

    # 1. Natural small fluctuation (70.0 -> 71.0) -> NO alert
    alerts = detector.process_reading(make_sample_reading(wlevel=71.0))
    assert len(alerts) == 0

    # 2. Sudden jump (70.0 -> 78.0, +8%) -> WATER_LEVEL_INCREASE (WARNING)
    alerts = detector.process_reading(make_sample_reading(wlevel=78.0))
    assert len(alerts) == 1
    a = alerts[0]
    assert a.type == IoTAlertType.WATER_LEVEL_INCREASE
    assert a.severity == IoTAlertSeverity.WARNING
    assert a.previous_value >= 70.0
    assert a.current_value == 78.0
    assert a.change >= 7.0
    assert "WATER LEVEL INCREASE" in a.title

    # 3. Cooldown suppression: another jump immediately afterwards is suppressed
    alerts = detector.process_reading(make_sample_reading(wlevel=82.0))
    assert len(alerts) == 0


def test_clarity_turbidity_alert_and_safety_wording():
    """Verify rapid clarity drops trigger alert and never state water is toxic/polluted."""
    detector = AnomalyDetector(
        session_id="test-session-3",
        water_body_id="wb-1",
        water_body_name="Harsul Reservoir",
        latitude=19.9291,
        longitude=75.3365,
        google_maps_url="https://maps.google.com/?q=19.9291,75.3365",
        baseline_target=5,
    )
    # Baseline at clarity 75
    for _ in range(5):
        detector.process_reading(make_sample_reading(clarity=75.0, status="CLEAR"))
    assert detector.baseline_established is True

    # Sudden drop to 40 (-35 points, Status TURBID)
    alerts = detector.process_reading(make_sample_reading(clarity=40.0, status="TURBID"))
    assert len(alerts) == 1
    a = alerts[0]
    assert a.type == IoTAlertType.CLARITY_CHANGE
    assert a.severity == IoTAlertSeverity.HIGH
    assert a.change <= -30.0
    assert "toxic" not in a.message.lower()
    assert "polluted" not in a.message.lower()


def test_temperature_alert_and_validity():
    """Verify temperature alerts trigger on sudden delta and skip when temperature_valid is False."""
    detector = AnomalyDetector(
        session_id="test-session-4",
        water_body_id="wb-1",
        water_body_name="Harsul Reservoir",
        latitude=19.9291,
        longitude=75.3365,
        google_maps_url="https://maps.google.com/?q=19.9291,75.3365",
        baseline_target=5,
    )
    # Baseline at 28.0°C
    for _ in range(5):
        detector.process_reading(make_sample_reading(temp=28.0))

    # Invalid sensor temperature -> skip
    alerts = detector.process_reading(make_sample_reading(temp=45.0, temp_valid=False))
    assert len(alerts) == 0

    # Sudden jump from 28°C to 31.5°C (+3.5°C) -> alert
    alerts = detector.process_reading(make_sample_reading(temp=31.5, temp_valid=True))
    assert len(alerts) == 1
    assert alerts[0].type == IoTAlertType.TEMPERATURE_CHANGE
    assert alerts[0].change >= 3.0


def test_tds_percentage_change_alert():
    """Verify TDS percentage threshold detection."""
    detector = AnomalyDetector(
        session_id="test-session-5",
        water_body_id="wb-1",
        water_body_name="Harsul Reservoir",
        latitude=19.9291,
        longitude=75.3365,
        google_maps_url="https://maps.google.com/?q=19.9291,75.3365",
        baseline_target=5,
    )
    # Baseline at 200 ppm
    for _ in range(5):
        detector.process_reading(make_sample_reading(tds=200.0))

    # Jump to 260 ppm (+30%) -> Alert
    alerts = detector.process_reading(make_sample_reading(tds=260.0))
    assert len(alerts) == 1
    assert alerts[0].type == IoTAlertType.TDS_CHANGE
    assert alerts[0].extra_details["percentage_change"] >= 25.0


def test_temporary_csv_lifecycle_and_deletion(tmp_path):
    """Verify that temporary CSV is created, appended to, and permanently deleted upon stop."""
    storage = TemporaryMonitoringStorage(base_dir=tmp_path)
    session_id = "test-session-csv"

    file_path = storage.start_session(session_id)
    assert file_path.exists()
    assert file_path.name == f"{session_id}.csv"

    # Write readings
    storage.append_reading(make_sample_reading())
    storage.append_reading(make_sample_reading())
    storage.close()

    content = file_path.read_text(encoding="utf-8")
    assert "timestamp,temperature_c,tds_ppm" in content
    assert len(content.strip().splitlines()) == 3  # header + 2 readings

    # Delete session file
    deleted = storage.delete_session(session_id)
    assert deleted is True
    assert not file_path.exists()


@pytest.mark.anyio
async def test_telegram_alert_formatting_and_dispatch():
    """Verify Telegram alert formatting includes coordinates, Maps link, and dispatches safely."""
    alert = IoTAlert(
        id="alert-1",
        session_id="session-1",
        water_body_id="wb-1",
        water_body_name="Harsul Reservoir",
        type=IoTAlertType.WATER_LEVEL_INCREASE,
        severity=IoTAlertSeverity.HIGH,
        title="WATER LEVEL INCREASE",
        message="Water level: 72.0% → 79.1% (+7.1 percentage points)",
        sensor_name="Water Level",
        previous_value=72.0,
        current_value=79.1,
        change=7.1,
        unit="%",
        detected_at="2026-10-16T12:45:32+00:00",
        latitude=19.9291,
        longitude=75.3365,
        google_maps_url="https://www.google.com/maps/search/?api=1&query=19.9291,75.3365",
    )

    msg_text = format_telegram_alert(alert)
    assert "🚨 JALNETRA IoT ALERT" in msg_text
    assert "Harsul Reservoir" in msg_text
    assert "72.0% → 79.1%" in msg_text
    assert "19.9291°N, 75.3365°E" in msg_text
    assert "https://www.google.com/maps/search/?api=1&query=19.9291,75.3365" in msg_text

    # Mock client and verify dispatch
    mock_client = MagicMock()
    mock_client.send_message = AsyncMock(return_value=True)
    register_chat_for_alerts(999999)

    sent = await dispatch_telegram_alert(alert, client=mock_client)
    assert sent >= 1
    mock_client.send_message.assert_called()
    call_args = mock_client.send_message.call_args
    assert "Harsul Reservoir" in call_args.kwargs["text"]
    assert "reply_markup" in call_args.kwargs


def test_monitoring_engine_start_stop_restart_cycle():
    """Verify that stop completely wipes temporary files, baseline, and next start is fresh."""
    engine = IoTMonitoringEngine()

    # 1. Start session
    start_res = engine.start_session(
        water_body_id="wb-harsul",
        water_body_name="Harsul Reservoir",
        latitude=19.9291,
        longitude=75.3365,
        force_start=True,
    )
    assert start_res.success is True
    session_id_1 = start_res.session_id
    assert engine.is_active is True

    # File should exist
    csv_file = engine._storage.get_session_file_path(session_id_1)
    assert csv_file.exists()

    # Add readings
    engine.process_new_reading(make_sample_reading())
    engine.process_new_reading(make_sample_reading())
    assert engine.get_status().sample_count == 2

    # 2. Stop session
    stop_res = engine.stop_session()
    assert stop_res.success is True
    assert stop_res.temporary_data_deleted is True
    assert engine.is_active is False
    assert not csv_file.exists()
    assert engine.get_status().sample_count == 0
    assert len(engine.get_alerts()) == 0

    # 3. Start second session
    start_res_2 = engine.start_session(
        water_body_id="wb-harsul",
        water_body_name="Harsul Reservoir",
        latitude=19.9291,
        longitude=75.3365,
        force_start=True,
    )
    assert start_res_2.success is True
    session_id_2 = start_res_2.session_id
    assert session_id_2 != session_id_1
    assert engine.get_status().sample_count == 0

    # Clean up
    engine.stop_session()


def test_monitoring_api_endpoints():
    """Verify FastAPI endpoints: /monitoring/status, /monitoring/start, /monitoring/stop, /monitoring/alerts."""
    client = TestClient(app)

    # 1. Initially stopped
    res = client.get("/api/v1/iot/monitoring/status")
    assert res.status_code == 200
    data = res.json()
    assert data["active"] is False

    # 2. Start monitoring (force_start=True to allow test without hardware connected)
    res = client.post("/api/v1/iot/monitoring/start", json={"force_start": True})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["session_id"] is not None

    # 3. Check status is now active
    res = client.get("/api/v1/iot/monitoring/status")
    assert res.status_code == 200
    assert res.json()["active"] is True

    # 4. Check alerts endpoint (initially empty)
    res = client.get("/api/v1/iot/monitoring/alerts")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 5. Stop monitoring
    res = client.post("/api/v1/iot/monitoring/stop")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["temporary_data_deleted"] is True

    # 6. Verify status returns to inactive
    res = client.get("/api/v1/iot/monitoring/status")
    assert res.status_code == 200
    assert res.json()["active"] is False
