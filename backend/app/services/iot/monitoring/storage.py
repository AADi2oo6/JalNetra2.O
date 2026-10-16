"""
Temporary storage manager for active IoT monitoring sessions.
Stores readings in data/iot_monitoring/{session_id}.csv during an active session,
and securely deletes the file when monitoring stops.
"""
import csv
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.iot.models import IoTReading

logger = logging.getLogger("jalnetra.iot.storage")


class TemporaryMonitoringStorage:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (settings.resolved_data_dir / "iot_monitoring")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._current_file: Optional[Path] = None
        self._file_handle = None
        self._writer = None

    def get_session_file_path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.csv"

    def start_session(self, session_id: str) -> Path:
        """Create new CSV file and write header."""
        self.close()
        file_path = self.get_session_file_path(session_id)
        self._current_file = file_path
        self._file_handle = open(file_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file_handle)
        self._writer.writerow([
            "timestamp",
            "temperature_c",
            "tds_ppm",
            "turbidity_raw",
            "clarity_index",
            "water_level_percent",
        ])
        self._file_handle.flush()
        logger.info("[IoT Storage] Created temporary monitoring file: %s", file_path)
        return file_path

    def append_reading(self, reading: IoTReading) -> None:
        """Append one sensor sample to temporary CSV file."""
        if not self._writer or not self._file_handle or self._file_handle.closed:
            return
        try:
            self._writer.writerow([
                reading.received_at,
                reading.temperature_c,
                reading.tds_ppm,
                reading.turbidity_raw,
                reading.clarity_index,
                reading.water_level_percent,
            ])
            self._file_handle.flush()
        except Exception as e:
            logger.warning("[IoT Storage] Error writing reading to CSV: %s", e)

    def close(self) -> None:
        """Close open file handle."""
        if self._file_handle and not self._file_handle.closed:
            try:
                self._file_handle.flush()
                self._file_handle.close()
            except Exception as e:
                logger.debug("[IoT Storage] Error closing file: %s", e)
        self._file_handle = None
        self._writer = None

    def delete_session(self, session_id: str) -> bool:
        """Close and completely delete the session CSV file."""
        self.close()
        file_path = self.get_session_file_path(session_id)
        deleted = False
        if file_path.exists():
            try:
                file_path.unlink()
                deleted = True
                logger.info("[IoT Storage] Deleted temporary monitoring file: %s", file_path)
            except Exception as e:
                logger.error("[IoT Storage] Failed to delete temporary file %s: %s", file_path, e)
        self._current_file = None
        return deleted
