"""
Serial Reader Worker for ESP32 IoT Device.
Runs a background daemon thread that connects to COM6 (or configured port), reads JSON lines,
validates sensor ranges, and updates IoTService in-memory state.
"""
from datetime import datetime, timezone
import json
import logging
import threading
import time
from typing import Optional

from pydantic import ValidationError
import serial
from serial import SerialException

from app.core.config import settings
from app.services.iot.models import IoTReading
from app.services.iot.service import iot_service, IoTService

logger = logging.getLogger("jalnetra.iot")


class SerialReaderWorker:
    def __init__(self, service: Optional[IoTService] = None):
        self.service = service or iot_service
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._serial: Optional[serial.Serial] = None

    def start(self) -> None:
        """Start the background serial reader thread if IoT is enabled."""
        if not settings.IOT_ENABLED:
            logger.info("[IoT] IoT is disabled in configuration. Skipping serial reader.")
            return

        if self._thread and self._thread.is_alive():
            logger.warning("[IoT] Serial reader worker is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="JalNetra-IoT-SerialWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "[IoT] Starting ESP32 serial reader | Port: %s | Baud: %s",
            settings.IOT_SERIAL_PORT,
            settings.IOT_SERIAL_BAUDRATE,
        )

    def stop(self) -> None:
        """Signal thread to stop and close serial port."""
        logger.info("[IoT] Stopping ESP32 serial reader worker...")
        self._stop_event.set()
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception as e:
                logger.debug("[IoT] Error closing serial port: %s", e)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.service.set_port_connected(False)
        logger.info("[IoT] ESP32 serial reader worker stopped.")

    def _open_port(self) -> Optional[serial.Serial]:
        """Attempt to open the configured serial port."""
        try:
            ser = serial.Serial(
                port=settings.IOT_SERIAL_PORT,
                baudrate=settings.IOT_SERIAL_BAUDRATE,
                timeout=1.0,
            )
            # DTR/RTS handling for CP210x/ESP32
            try:
                ser.dtr = False
                ser.rts = False
            except Exception:
                pass
            return ser
        except (SerialException, OSError, FileNotFoundError) as e:
            logger.warning("[IoT] %s unavailable: %s", settings.IOT_SERIAL_PORT, e)
            return None

    def _run_loop(self) -> None:
        """Main loop executed in background daemon thread."""
        logger.info(
            "[IoT] Serial reader thread started for port %s @ %d baud",
            settings.IOT_SERIAL_PORT,
            settings.IOT_SERIAL_BAUDRATE,
        )

        while not self._stop_event.is_set():
            # Ensure port is open
            if not self._serial or not self._serial.is_open:
                self.service.set_port_connected(False)
                ser = self._open_port()
                if not ser:
                    # Retry after brief wait
                    self._stop_event.wait(2.0)
                    continue

                self._serial = ser
                self.service.set_port_connected(True)
                logger.info(
                    "[IoT] Connected successfully to %s @ %d baud",
                    settings.IOT_SERIAL_PORT,
                    settings.IOT_SERIAL_BAUDRATE,
                )

            # Read lines
            try:
                raw_bytes = self._serial.readline()
                if not raw_bytes:
                    continue

                line = raw_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # Ignore bootloader / boot noise strings
                if not line.startswith("{"):
                    logger.debug("[IoT] Non-JSON line ignored: %s", line[:60])
                    continue

                # Parse JSON
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as jde:
                    logger.warning("[IoT] Invalid JSON line received — skipped: %s (%s)", line[:60], jde)
                    continue

                # Validate data schema
                try:
                    # Inject backend reception timestamp
                    payload["received_at"] = datetime.now(timezone.utc).isoformat()
                    reading = IoTReading(**payload)
                    self.service.update_reading(reading)
                    logger.debug(
                        "[IoT] Valid reading: temp=%.1f°C clarity=%.1f wlevel=%.1f%%",
                        reading.temperature_c,
                        reading.clarity_index,
                        reading.water_level_percent,
                    )
                except ValidationError as ve:
                    logger.warning("[IoT] Validation error for reading — skipped: %s", ve)
                    continue

            except (SerialException, OSError) as se:
                logger.warning(
                    "[IoT] Serial connection error on %s: %s. Retrying serial connection...",
                    settings.IOT_SERIAL_PORT,
                    se,
                )
                self.service.set_port_connected(False)
                if self._serial:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                    self._serial = None
                self._stop_event.wait(2.0)
            except Exception as ex:
                logger.error("[IoT] Unexpected error in serial loop: %s", ex, exc_info=True)
                self._stop_event.wait(1.0)


serial_reader_worker = SerialReaderWorker()
