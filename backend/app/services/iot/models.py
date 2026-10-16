"""
Pydantic data models and schemas for IoT Live Sensor Integration.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class IoTConnectionState(str, Enum):
    CONNECTED = "CONNECTED"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"


class IoTReading(BaseModel):
    """
    Validated IoT sensor reading received from ESP32 over serial.
    Ranges conform to sensor specifications:
      - Temperature: -20°C to 80°C
      - Clarity Index: 0 to 100
      - Water Level: 0 to 100%
      - TDS: >= 0 ppm
      - Raw ADC values: 0 to 4095
    """
    device: str = "jalnetra_iot"

    temperature_c: float
    temperature_valid: bool = True

    turbidity_raw: int
    clarity_index: float
    turbidity_status: str

    tds_raw: int
    tds_ppm: float

    water_level_raw: int
    water_level_percent: float

    received_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @field_validator("temperature_c")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < -20.0 or v > 80.0:
            raise ValueError(f"Temperature {v}°C out of valid range [-20, 80]")
        return round(v, 2)

    @field_validator("clarity_index")
    @classmethod
    def validate_clarity_index(cls, v: float) -> float:
        if v < 0.0 or v > 100.0:
            raise ValueError(f"Clarity index {v} out of valid range [0, 100]")
        return round(v, 2)

    @field_validator("water_level_percent")
    @classmethod
    def validate_water_level(cls, v: float) -> float:
        if v < 0.0 or v > 100.0:
            raise ValueError(f"Water level {v}% out of valid range [0, 100]")
        return round(v, 2)

    @field_validator("tds_ppm")
    @classmethod
    def validate_tds(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"TDS {v} ppm cannot be negative")
        return round(v, 2)

    @field_validator("turbidity_raw", "tds_raw", "water_level_raw")
    @classmethod
    def validate_raw_adc(cls, v: int) -> int:
        if v < 0 or v > 4095:
            raise ValueError(f"Raw ADC {v} out of valid ESP32 range [0, 4095]")
        return v


class IoTStatusInfo(BaseModel):
    enabled: bool
    connected: bool
    port: str
    baud_rate: int
    device: str
    status: IoTConnectionState
    last_received_at: Optional[str] = None
    seconds_since_last_reading: Optional[float] = None
    target_water_body_name: str


class IoTLatestResponse(BaseModel):
    available: bool
    device: Optional[str] = None
    temperature_c: Optional[float] = None
    temperature_valid: Optional[bool] = None
    turbidity_raw: Optional[int] = None
    clarity_index: Optional[float] = None
    turbidity_status: Optional[str] = None
    tds_raw: Optional[int] = None
    tds_ppm: Optional[float] = None
    water_level_raw: Optional[int] = None
    water_level_percent: Optional[float] = None
    received_at: Optional[str] = None
    status: IoTConnectionState = IoTConnectionState.DISCONNECTED
    seconds_ago: Optional[float] = None
    target_water_body_name: str = "Harsul Reservoir"
    message: Optional[str] = None
