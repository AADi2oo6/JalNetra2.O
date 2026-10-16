import React, { useEffect, useState, useRef } from 'react';
import {
  getLatestIoTReading,
  getIoTStatus,
  IoTLatestResponse,
  IoTStatusResponse,
  IoTConnectionState,
} from '../api/iot';
import './LiveIoTMonitorSection.css';

interface LiveIoTMonitorSectionProps {
  waterBodyId?: string;
  waterBodyName?: string;
}

export const LiveIoTMonitorSection: React.FC<LiveIoTMonitorSectionProps> = ({
  waterBodyName,
}) => {
  // Only activate for Harsul Reservoir
  const isTargetWaterBody =
    waterBodyName &&
    waterBodyName.trim().toLowerCase().includes('harsul');

  const [reading, setReading] = useState<IoTLatestResponse | null>(null);
  const [deviceStatus, setDeviceStatus] = useState<IoTStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    if (!isTargetWaterBody) {
      return;
    }

    const pollData = async () => {
      try {
        const [latestRes, statusRes] = await Promise.all([
          getLatestIoTReading().catch(() => null),
          getIoTStatus().catch(() => null),
        ]);

        if (!isMountedRef.current) return;

        if (latestRes) {
          setReading(latestRes);
          setError(null);
        }
        if (statusRes) {
          setDeviceStatus(statusRes);
        }
      } catch (err: any) {
        if (!isMountedRef.current) return;
        setError(err.message || 'Error connecting to IoT backend');
      }
    };

    // Immediate initial fetch
    pollData();

    // 1-second polling interval
    const intervalId = setInterval(pollData, 1000);

    return () => {
      isMountedRef.current = false;
      clearInterval(intervalId);
    };
  }, [isTargetWaterBody, waterBodyName]);

  // If not Harsul Reservoir, render nothing
  if (!isTargetWaterBody) {
    return null;
  }

  // Determine current effective state
  const state: IoTConnectionState = reading?.status || deviceStatus?.status || 'DISCONNECTED';
  const isConnected = state === 'CONNECTED';
  const isStale = state === 'STALE';
  const isDisconnected = state === 'DISCONNECTED';

  // Format elapsed time string
  const getElapsedText = () => {
    if (reading?.seconds_ago !== undefined && reading.seconds_ago !== null) {
      if (reading.seconds_ago < 2) return 'just now';
      if (reading.seconds_ago < 60) return `${Math.round(reading.seconds_ago)} sec ago`;
      const mins = Math.floor(reading.seconds_ago / 60);
      return `${mins} min ago`;
    }
    return 'Waiting for packet...';
  };

  const getStatusBadgeClass = () => {
    if (isConnected) return 'iot-status-badge iot-status-connected';
    if (isStale) return 'iot-status-badge iot-status-stale';
    return 'iot-status-badge iot-status-disconnected';
  };

  const getStatusBadgeLabel = () => {
    if (isConnected) return '● CONNECTED';
    if (isStale) return '⚠ STALE';
    return '○ DISCONNECTED';
  };

  const getTurbidityBadgeClass = (status?: string) => {
    const s = (status || '').toUpperCase();
    if (s.includes('CLEAR')) return 'iot-badge-small iot-badge-clear';
    if (s.includes('TURBID')) return 'iot-badge-small iot-badge-turbid';
    return 'iot-badge-small iot-badge-normal';
  };

  return (
    <div className="iot-monitor-container">
      {/* ── Top Header ────────────────────────────────────────── */}
      <div className="iot-monitor-header">
        <div className="iot-title-group">
          <div className="iot-kicker">
            <span className="iot-live-pulse-dot" />
            TELEMETRY · REAL-TIME SENSING
          </div>
          <h2 className="iot-main-title">LIVE IoT WATER MONITOR</h2>
          <div className="iot-subtitle">
            <span><strong>{waterBodyName}</strong></span>
            <span>·</span>
            <span>ESP32 Hardware</span>
            <span>·</span>
            <span>Port: {deviceStatus?.port || 'COM6'} @ {deviceStatus?.baud_rate || 115200} baud</span>
            {reading?.available && (
              <>
                <span>·</span>
                <span>Last reading: {getElapsedText()}</span>
              </>
            )}
          </div>
        </div>

        <div className={getStatusBadgeClass()}>
          <span className="status-dot" />
          <span>{getStatusBadgeLabel()}</span>
        </div>
      </div>

      {/* ── Connection Alert Banner (if disconnected or stale) ──── */}
      {isDisconnected && (
        <div className="iot-banner iot-banner-disconnected">
          <span style={{ fontSize: '1.25rem' }}>🔌</span>
          <div>
            <strong>ESP32 Disconnected / Waiting:</strong> Hardware is not currently streaming data to {deviceStatus?.port || 'COM6'}.
            Make sure the ESP32 is plugged in and the Arduino IDE Serial Monitor is closed.
            {error && <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', opacity: 0.85 }}>{error}</div>}
          </div>
        </div>
      )}

      {isStale && (
        <div className="iot-banner iot-banner-stale">
          <span style={{ fontSize: '1.25rem' }}>⏳</span>
          <div>
            <strong>Data Stale:</strong> Last reading was received {getElapsedText()}. Waiting for subsequent sensor packets...
          </div>
        </div>
      )}

      {/* ── Live Sensor Cards Grid ────────────────────────────── */}
      <div className="iot-cards-grid">
        {/* 1. Water Temperature */}
        <div className="iot-card">
          <div className="iot-card-header">
            <div className="iot-card-label">
              <span>🌡️</span>
              <span>Temperature</span>
            </div>
            {reading?.temperature_valid !== false ? (
              <span className="iot-badge-small iot-badge-clear">Valid</span>
            ) : (
              <span className="iot-badge-small iot-badge-turbid">Uncalibrated</span>
            )}
          </div>

          <div className="iot-metric-value-row">
            <span className="iot-metric-value">
              {reading?.available && reading.temperature_valid !== false
                ? reading.temperature_c?.toFixed(1)
                : '—'}
            </span>
            <span className="iot-metric-unit">°C</span>
          </div>

          <div className="iot-metric-subtext">
            {reading?.available
              ? `Water sensor temperature (${((reading.temperature_c || 0) * 1.8 + 32).toFixed(1)} °F)`
              : 'Sensor telemetry offline'}
          </div>
          <div className="iot-raw-tag">ESP32 DS18B20 / Analog</div>
        </div>

        {/* 2. Estimated TDS */}
        <div className="iot-card">
          <div className="iot-card-header">
            <div className="iot-card-label">
              <span>💧</span>
              <span>Estimated TDS</span>
            </div>
            <span className="iot-badge-small iot-badge-normal">Conductivity</span>
          </div>

          <div className="iot-metric-value-row">
            <span className="iot-metric-value">
              {reading?.available ? reading.tds_ppm?.toFixed(1) : '—'}
            </span>
            <span className="iot-metric-unit">ppm</span>
          </div>

          <div className="iot-metric-subtext">
            Calibrated estimate · not laboratory-grade
          </div>
          <div className="iot-raw-tag">
            Raw ADC: {reading?.available ? reading.tds_raw : '—'}
          </div>
        </div>

        {/* 3. Turbidity & Clarity Index */}
        <div className="iot-card">
          <div className="iot-card-header">
            <div className="iot-card-label">
              <span>🔬</span>
              <span>Turbidity & Clarity</span>
            </div>
            <span className={getTurbidityBadgeClass(reading?.turbidity_status)}>
              {reading?.turbidity_status || 'UNKNOWN'}
            </span>
          </div>

          <div className="iot-metric-value-row">
            <span className="iot-metric-value">
              {reading?.available ? reading.clarity_index?.toFixed(1) : '—'}
            </span>
            <span className="iot-metric-unit">/ 100</span>
          </div>

          <div className="iot-clarity-meter-wrap">
            <div className="iot-clarity-track">
              <div
                className="iot-clarity-fill"
                style={{
                  width: `${Math.min(100, Math.max(0, reading?.clarity_index || 0))}%`,
                }}
              />
            </div>
            <div className="iot-meter-labels">
              <span>0 (Turbid)</span>
              <span>50</span>
              <span>100 (Clear)</span>
            </div>
          </div>

          <div className="iot-metric-subtext" style={{ marginTop: '0.4rem' }}>
            Relative clarity index · Not NTU
          </div>
          <div className="iot-raw-tag">
            Raw ADC: {reading?.available ? reading.turbidity_raw : '—'}
          </div>
        </div>

        {/* 4. Water Level */}
        <div className="iot-card iot-water-level-card">
          <div className="iot-card-header">
            <div className="iot-card-label">
              <span>🌊</span>
              <span>Water Level</span>
            </div>
            <span className="iot-badge-small iot-badge-normal">Gauge</span>
          </div>

          <div className="iot-metric-value-row">
            <span className="iot-metric-value">
              {reading?.available ? reading.water_level_percent?.toFixed(1) : '—'}
            </span>
            <span className="iot-metric-unit">%</span>
          </div>

          <div className="iot-water-gauge-container">
            <div className="iot-water-track">
              <div
                className="iot-water-fill"
                style={{
                  width: `${Math.min(100, Math.max(0, reading?.water_level_percent || 0))}%`,
                }}
              />
            </div>
            <div className="iot-meter-labels">
              <span>0%</span>
              <span>25%</span>
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>

          <div className="iot-metric-subtext" style={{ marginTop: '0.4rem' }}>
            Calibrated range: 0 ADC = 0% · 2300 ADC = 100%
          </div>
          <div className="iot-raw-tag">
            Raw ADC: {reading?.available ? reading.water_level_raw : '—'}
          </div>
        </div>
      </div>

      {/* ── Technical Specs Footer ────────────────────────────── */}
      <div className="iot-tech-footer">
        <div className="iot-specs-row">
          <div className="iot-spec-item">
            <span className="iot-spec-key">DEVICE:</span>
            <span className="iot-spec-val">{reading?.device || deviceStatus?.device || 'jalnetra_iot'}</span>
          </div>
          <div className="iot-spec-item">
            <span className="iot-spec-key">CONNECTION:</span>
            <span className="iot-spec-val">USB Serial</span>
          </div>
          <div className="iot-spec-item">
            <span className="iot-spec-key">PORT:</span>
            <span className="iot-spec-val">{deviceStatus?.port || 'COM6'}</span>
          </div>
          <div className="iot-spec-item">
            <span className="iot-spec-key">BAUD:</span>
            <span className="iot-spec-val">{deviceStatus?.baud_rate || 115200}</span>
          </div>
          <div className="iot-spec-item">
            <span className="iot-spec-key">LAST READING:</span>
            <span className="iot-spec-val">{getElapsedText()}</span>
          </div>
        </div>
      </div>

      {/* ── Disclaimer ────────────────────────────────────────── */}
      <div className="iot-disclaimer">
        ⚠️ IoT readings are live sensor measurements and derived values from the connected JalNetra device.
        Sensor calibration determines measurement accuracy. Optical clarity is a relative index and does not represent laboratory NTU turbidity.
      </div>
    </div>
  );
};
