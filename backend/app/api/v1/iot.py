"""
IoT REST API endpoints for live ESP32 sensor state and temporary monitoring sessions.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models.water_body import WaterBody
from app.services.iot import (
    iot_service,
    IoTStatusInfo,
    IoTLatestResponse,
)
from app.services.iot.monitoring import (
    IoTAlert,
    MonitoringSessionStatus,
    StartMonitoringResponse,
    StopMonitoringResponse,
    iot_monitoring_engine,
)

router = APIRouter(prefix="/iot", tags=["IoT"])


class StartMonitoringRequest(BaseModel):
    water_body_id: Optional[str] = None
    force_start: Optional[bool] = False


@router.get("/status", response_model=IoTStatusInfo)
def get_iot_status() -> IoTStatusInfo:
    """Return current hardware connection status, serial port, and freshness."""
    return iot_service.get_status()


@router.get("/latest", response_model=IoTLatestResponse)
def get_latest_iot_reading() -> IoTLatestResponse:
    """Return latest in-memory sensor reading from ESP32."""
    return iot_service.get_latest_response()


@router.get("/monitoring/status", response_model=MonitoringSessionStatus)
def get_monitoring_status() -> MonitoringSessionStatus:
    """Return status, sample counts, and baseline state of active monitoring session."""
    return iot_monitoring_engine.get_status()


@router.post("/monitoring/start", response_model=StartMonitoringResponse)
def start_monitoring(
    payload: Optional[StartMonitoringRequest] = None,
    db: Session = Depends(get_db),
) -> StartMonitoringResponse:
    """
    Start a temporary monitoring session.
    Verifies hardware is connected, establishes baseline, and records readings.
    """
    target_name = settings.IOT_TARGET_WATER_BODY_NAME

    # Resolve Harsul Reservoir entity from database
    wb: Optional[WaterBody] = None
    if payload and payload.water_body_id:
        wb = db.query(WaterBody).filter(WaterBody.id == payload.water_body_id).first()

    if not wb:
        wb = db.query(WaterBody).filter(
            (WaterBody.name.ilike(f"%{target_name}%")) | (WaterBody.name.ilike("%harsul%"))
        ).first()

    if not wb:
        # Default fallback coordinates for Harsul Reservoir if DB record is somehow missing
        wb_id = payload.water_body_id if payload else "harsul-default"
        wb_name = target_name
        lat, lon = 19.9291418, 75.3364885
    else:
        wb_id = wb.id
        wb_name = wb.name
        lat = wb.centroid_lat if wb.centroid_lat is not None else 19.9291418
        lon = wb.centroid_lon if wb.centroid_lon is not None else 75.3364885

    force_start = bool(payload and payload.force_start)
    res = iot_monitoring_engine.start_session(
        water_body_id=wb_id,
        water_body_name=wb_name,
        latitude=lat,
        longitude=lon,
        force_start=force_start,
    )
    return res


@router.post("/monitoring/stop", response_model=StopMonitoringResponse)
def stop_monitoring() -> StopMonitoringResponse:
    """
    Stop active monitoring session.
    Deletes temporary CSV file and clears all session detection state.
    """
    return iot_monitoring_engine.stop_session()


@router.get("/monitoring/alerts", response_model=List[IoTAlert])
def get_monitoring_alerts() -> List[IoTAlert]:
    """Return all alerts generated during the current active monitoring session."""
    return iot_monitoring_engine.get_alerts()
