"""
Data models and schemas for IoT Live Monitoring and Alert System.
"""
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class IoTAlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IoTAlertType(str, Enum):
    WATER_LEVEL_INCREASE = "WATER_LEVEL_INCREASE"
    WATER_LEVEL_DECREASE = "WATER_LEVEL_DECREASE"
    CLARITY_CHANGE = "CLARITY_CHANGE"
    TEMPERATURE_CHANGE = "TEMPERATURE_CHANGE"
    TDS_CHANGE = "TDS_CHANGE"


class IoTAlert(BaseModel):
    id: str
    session_id: str
    water_body_id: str
    water_body_name: str
    type: IoTAlertType
    severity: IoTAlertSeverity
    title: str
    message: str
    sensor_name: str
    previous_value: float
    current_value: float
    change: float
    unit: str
    detected_at: str  # ISO-8601 string
    latitude: float
    longitude: float
    google_maps_url: str
    extra_details: Optional[Dict[str, Any]] = None


class MonitoringSessionStatus(BaseModel):
    active: bool
    session_id: Optional[str] = None
    water_body_id: Optional[str] = None
    water_body_name: str = "Harsul Reservoir"
    started_at: Optional[str] = None
    duration_seconds: int = 0
    sample_count: int = 0
    alert_count: int = 0
    baseline_established: bool = False
    baseline_progress: int = 0
    baseline_target: int = 10
    baseline_values: Optional[Dict[str, float]] = None


class StartMonitoringResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    message: str
    water_body_id: Optional[str] = None
    water_body_name: str = "Harsul Reservoir"


class StopMonitoringResponse(BaseModel):
    success: bool
    samples_recorded: int = 0
    alerts_generated: int = 0
    temporary_data_deleted: bool = True
    message: str
