"""
IoT Live Monitoring and Alerting package.
"""
from app.services.iot.monitoring.models import (
    IoTAlert,
    IoTAlertSeverity,
    IoTAlertType,
    MonitoringSessionStatus,
    StartMonitoringResponse,
    StopMonitoringResponse,
)
from app.services.iot.monitoring.engine import (
    IoTMonitoringEngine,
    iot_monitoring_engine,
)
from app.services.iot.monitoring.alerts import (
    register_chat_for_alerts,
    get_target_chat_ids,
    dispatch_telegram_alert,
    format_telegram_alert,
)
from app.services.iot.service import iot_service

# Auto-subscribe monitoring engine to live incoming readings
iot_service.register_reading_subscriber(iot_monitoring_engine.process_new_reading)

__all__ = [
    "IoTAlert",
    "IoTAlertSeverity",
    "IoTAlertType",
    "MonitoringSessionStatus",
    "StartMonitoringResponse",
    "StopMonitoringResponse",
    "IoTMonitoringEngine",
    "iot_monitoring_engine",
    "register_chat_for_alerts",
    "get_target_chat_ids",
    "dispatch_telegram_alert",
    "format_telegram_alert",
]
