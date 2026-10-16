"""
IoT REST API endpoints for live ESP32 sensor state.
"""
from fastapi import APIRouter
from app.services.iot import (
    iot_service,
    IoTStatusInfo,
    IoTLatestResponse,
)

router = APIRouter(prefix="/iot", tags=["IoT"])


@router.get("/status", response_model=IoTStatusInfo)
def get_iot_status() -> IoTStatusInfo:
    """Return current hardware connection status, serial port, and freshness."""
    return iot_service.get_status()


@router.get("/latest", response_model=IoTLatestResponse)
def get_latest_iot_reading() -> IoTLatestResponse:
    """Return latest in-memory sensor reading from ESP32."""
    return iot_service.get_latest_response()
