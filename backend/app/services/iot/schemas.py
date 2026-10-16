"""
IoT API Schemas.
"""
from app.services.iot.models import (
    IoTConnectionState,
    IoTReading,
    IoTStatusInfo,
    IoTLatestResponse,
)

__all__ = [
    "IoTConnectionState",
    "IoTReading",
    "IoTStatusInfo",
    "IoTLatestResponse",
]
