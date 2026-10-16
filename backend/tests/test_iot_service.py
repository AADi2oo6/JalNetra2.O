"""
Unit and integration tests for IoT Live Sensor Integration.
Tests JSON validation, ranges, memory store, status transitions, serial worker resilience, and REST API.
"""
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.main import app
from app.services.iot.models import (
    IoTConnectionState,
    IoTReading,
    IoTLatestResponse,
)
from app.services.iot.service import IoTService, iot_service
from app.services.iot.serial_reader import SerialReaderWorker


def test_iot_reading_valid():
    """Verify that valid ESP32 sensor JSON passes validation and rounds values properly."""
    data = {
        "device": "jalnetra_iot",
        "temperature_c": 28.456,
        "temperature_valid": True,
        "turbidity_raw": 1850,
        "clarity_index": 16.74,
        "turbidity_status": "TURBID",
        "tds_raw": 1200,
        "tds_ppm": 245.62,
        "water_level_raw": 1750,
        "water_level_percent": 76.12,
    }
    reading = IoTReading(**data)
    assert reading.device == "jalnetra_iot"
    assert reading.temperature_c == 28.46
    assert reading.temperature_valid is True
    assert reading.turbidity_raw == 1850
    assert reading.clarity_index == 16.74
    assert reading.turbidity_status == "TURBID"
    assert reading.tds_raw == 1200
    assert reading.tds_ppm == 245.62
    assert reading.water_level_raw == 1750
    assert reading.water_level_percent == 76.12
    assert reading.received_at is not None


@pytest.mark.parametrize(
    "field,invalid_val",
    [
        ("temperature_c", -25.0),
        ("temperature_c", 85.0),
        ("clarity_index", -1.0),
        ("clarity_index", 105.0),
        ("water_level_percent", -5.0),
        ("water_level_percent", 101.0),
        ("tds_ppm", -0.1),
        ("turbidity_raw", -1),
        ("turbidity_raw", 4096),
        ("tds_raw", 5000),
        ("water_level_raw", 4100),
    ],
)
def test_iot_reading_range_validation(field, invalid_val):
    """Verify out-of-range sensor values are strictly rejected."""
    base_data = {
        "device": "jalnetra_iot",
        "temperature_c": 25.0,
        "temperature_valid": True,
        "turbidity_raw": 1800,
        "clarity_index": 50.0,
        "turbidity_status": "NORMAL",
        "tds_raw": 1000,
        "tds_ppm": 200.0,
        "water_level_raw": 1500,
        "water_level_percent": 50.0,
    }
    base_data[field] = invalid_val
    with pytest.raises(ValidationError):
        IoTReading(**base_data)


def test_iot_service_lifecycle_and_status():
    """Verify in-memory service state, freshness, and status calculations."""
    service = IoTService()
    # 1. Initial state
    status = service.get_status()
    assert status.status == IoTConnectionState.DISCONNECTED
    assert status.last_received_at is None
    latest = service.get_latest_response()
    assert latest.available is False
    assert latest.status == IoTConnectionState.DISCONNECTED

    # 2. Add fresh reading (<= 5s)
    now = datetime.now(timezone.utc)
    reading = IoTReading(
        device="jalnetra_iot",
        temperature_c=26.5,
        temperature_valid=True,
        turbidity_raw=1900,
        clarity_index=20.0,
        turbidity_status="TURBID",
        tds_raw=1100,
        tds_ppm=210.0,
        water_level_raw=1600,
        water_level_percent=60.0,
        received_at=now.isoformat(),
    )
    service.update_reading(reading)

    status = service.get_status()
    assert status.status == IoTConnectionState.CONNECTED
    assert status.connected is True
    assert status.last_received_at == now.isoformat()

    latest = service.get_latest_response()
    assert latest.available is True
    assert latest.temperature_c == 26.5
    assert latest.clarity_index == 20.0
    assert latest.water_level_percent == 60.0
    assert latest.status == IoTConnectionState.CONNECTED

    # 3. Simulate Stale reading (6 to 15s)
    service._last_received_datetime = now - timedelta(seconds=8)
    state, elapsed = service.compute_connection_state()
    assert state == IoTConnectionState.STALE
    assert elapsed >= 8.0

    # 4. Simulate Disconnected reading (> 15s)
    service._last_received_datetime = now - timedelta(seconds=20)
    state, elapsed = service.compute_connection_state()
    assert state == IoTConnectionState.DISCONNECTED
    assert elapsed >= 20.0


def test_serial_reader_worker_parses_valid_and_skips_malformed():
    """Verify background worker parses valid JSON and gracefully skips malformed/noisy lines."""
    service = IoTService()
    worker = SerialReaderWorker(service=service)

    valid_json = json.dumps({
        "device": "jalnetra_iot",
        "temperature_c": 27.2,
        "temperature_valid": True,
        "turbidity_raw": 1820,
        "clarity_index": 15.5,
        "turbidity_status": "TURBID",
        "tds_raw": 1150,
        "tds_ppm": 230.4,
        "water_level_raw": 1650,
        "water_level_percent": 70.0,
    })

    # Prepare mocked serial stream: noise, malformed JSON, out of range, valid JSON
    mock_serial = MagicMock()
    mock_serial.is_open = True
    mock_serial.readline.side_effect = [
        b"rst:0x1 (POWERON_RESET),boot:0x17\r\n",   # boot noise
        b"{incomplete json\r\n",                    # JSONDecodeError
        b'{"device":"jalnetra_iot","temperature_c":999.0}\r\n',  # ValidationError
        valid_json.encode("utf-8") + b"\r\n",       # Valid reading
        b"",                                        # Empty timeout
    ]

    with patch.object(worker, "_open_port", return_value=mock_serial):
        # Run one iteration of the loop logic directly
        with patch.object(worker._stop_event, "is_set", side_effect=[False, False, False, False, False, True]):
            worker._run_loop()

    # The valid reading should be successfully parsed and stored
    latest = service.get_latest_reading()
    assert latest is not None
    assert latest.temperature_c == 27.2
    assert latest.water_level_percent == 70.0
    assert latest.clarity_index == 15.5
    assert service.get_status().status == IoTConnectionState.CONNECTED


def test_iot_api_status_and_latest():
    """Verify FastAPI GET /api/v1/iot/status and GET /api/v1/iot/latest."""
    client = TestClient(app)

    # 1. Reset state
    iot_service.reset()

    # 2. Check status when no reading
    res = client.get("/api/v1/iot/status")
    assert res.status_code == 200
    data = res.json()
    assert data["enabled"] is True
    assert data["port"] == "COM6"
    assert data["baud_rate"] == 115200
    assert data["status"] == "DISCONNECTED"
    assert data["target_water_body_name"] == "Harsul Reservoir"

    # 3. Check latest when no reading
    res = client.get("/api/v1/iot/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False
    assert data["status"] == "DISCONNECTED"
    assert "No IoT reading received yet" in data["message"]

    # 4. Inject a live reading into the singleton service
    test_reading = IoTReading(
        device="jalnetra_iot",
        temperature_c=28.45,
        temperature_valid=True,
        turbidity_raw=1850,
        clarity_index=16.7,
        turbidity_status="TURBID",
        tds_raw=1200,
        tds_ppm=245.6,
        water_level_raw=1750,
        water_level_percent=76.1,
    )
    iot_service.update_reading(test_reading)

    # 5. Check status again
    res = client.get("/api/v1/iot/status")
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is True
    assert data["status"] == "CONNECTED"
    assert data["last_received_at"] is not None

    # 6. Check latest with reading
    res = client.get("/api/v1/iot/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True
    assert data["device"] == "jalnetra_iot"
    assert data["temperature_c"] == 28.45
    assert data["temperature_valid"] is True
    assert data["turbidity_raw"] == 1850
    assert data["clarity_index"] == 16.7
    assert data["turbidity_status"] == "TURBID"
    assert data["tds_raw"] == 1200
    assert data["tds_ppm"] == 245.6
    assert data["water_level_raw"] == 1750
    assert data["water_level_percent"] == 76.1
    assert data["status"] == "CONNECTED"
    assert data["seconds_ago"] is not None
    assert data["target_water_body_name"] == "Harsul Reservoir"
