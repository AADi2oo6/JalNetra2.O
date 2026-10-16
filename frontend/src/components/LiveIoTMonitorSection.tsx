import React, { useEffect, useState, useRef } from 'react';
import {
  getLatestIoTReading,
  getIoTStatus,
  getMonitoringStatus,
  startMonitoring,
  stopMonitoring,
  getMonitoringAlerts,
  getTelegramAlertsStatus,
  TelegramAlertsStatusResponse,
  IoTLatestResponse,
  IoTStatusResponse,
  IoTConnectionState,
  MonitoringSessionStatus,
} from '../api/iot';
import { useIoTAlerts } from '../hooks/useIoTAlerts';
import { FloatingAlert } from './FloatingAlert';
import './LiveIoTMonitorSection.css';

interface LiveIoTMonitorSectionProps {
  waterBodyId?: string;
  waterBodyName?: string;
}

export const LiveIoTMonitorSection: React.FC<LiveIoTMonitorSectionProps> = ({
  waterBodyId,
  waterBodyName,
}) => {
  // Only activate for Harsul Reservoir
  const isTargetWaterBody =
    waterBodyName &&
    waterBodyName.trim().toLowerCase().includes('harsul');

  const {
    alerts,
    setAlerts,
    floatingAlert,
    dismissFloatingAlert,
    clearAlerts,
  } = useIoTAlerts({ enabled: Boolean(isTargetWaterBody) });

  const [reading, setReading] = useState<IoTLatestResponse | null>(null);
  const [deviceStatus, setDeviceStatus] = useState<IoTStatusResponse | null>(null);
  const [monitoringStatus, setMonitoringStatus] = useState<MonitoringSessionStatus | null>(null);
  const [telegramStatus, setTelegramStatus] = useState<TelegramAlertsStatusResponse | null>(null);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [showStopModal, setShowStopModal] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isMountedRef = useRef(true);

  const formatDuration = (totalSec: number) => {
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatTimeOnly = (isoString?: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  useEffect(() => {
    isMountedRef.current = true;

    if (!isTargetWaterBody) {
      return;
    }

    const pollData = async () => {
      try {
        const [latestRes, statusRes, monRes, tgRes] = await Promise.all([
          getLatestIoTReading().catch(() => null),
          getIoTStatus().catch(() => null),
          getMonitoringStatus().catch(() => null),
          getTelegramAlertsStatus().catch(() => null),
        ]);

        if (!isMountedRef.current) return;

        if (latestRes) {
          setReading(latestRes);
          setError(null);
        }
        if (statusRes) {
          setDeviceStatus(statusRes);
        }
        if (tgRes) {
          setTelegramStatus(tgRes);
        }
        if (monRes) {
          setMonitoringStatus(monRes);
          if (monRes.active) {
            // Fetch any existing alerts from current active session
            getMonitoringAlerts()
              .then(alertList => {
                if (isMountedRef.current && alertList && alertList.length > 0) {
                  setAlerts(prev => {
                    const existingIds = new Set(prev.map(a => a.id));
                    const newOnes = alertList.filter(a => !existingIds.has(a.id));
                    return newOnes.length > 0 ? [...newOnes, ...prev] : prev;
                  });
                }
              })
              .catch(() => {});
          } else {
            clearAlerts();
          }
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
  }, [isTargetWaterBody, waterBodyName, clearAlerts, setAlerts]);

  // Actions
  const handleStartMonitoring = async () => {
    setIsActionLoading(true);
    setActionError(null);
    try {
      const res = await startMonitoring(waterBodyId);
      if (!res.success) {
        setActionError(res.message);
      } else {
        const mon = await getMonitoringStatus();
        setMonitoringStatus(mon);
      }
    } catch (err: any) {
      setActionError(err.message || 'Failed to start monitoring session');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleConfirmStop = async () => {
    setIsActionLoading(true);
    setActionError(null);
    try {
      await stopMonitoring();
      setMonitoringStatus(null);
      clearAlerts();
      setShowStopModal(false);
    } catch (err: any) {
      setActionError(err.message || 'Failed to stop monitoring session');
    } finally {
      setIsActionLoading(false);
    }
  };

  // If not Harsul Reservoir, render nothing
  if (!isTargetWaterBody) {
    return null;
  }

  // Determine current effective state
  const state: IoTConnectionState = reading?.status || deviceStatus?.status || 'DISCONNECTED';
  const isConnected = state === 'CONNECTED';
  const isStale = state === 'STALE';
  const isDisconnected = state === 'DISCONNECTED';

  const isMonitoringActive = monitoringStatus?.active || false;

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
      {/* ── Floating Alert Toast (Top-Right Viewport) ──────────── */}
      <FloatingAlert
        alert={floatingAlert}
        onDismiss={dismissFloatingAlert}
      />

      {/* ── Top Header ────────────────────────────────────────── */}
      <div className="iot-monitor-header">
        <div className="iot-title-group">
          <div className="iot-kicker">
            <span className="iot-live-pulse-dot" />
            TELEMETRY · REAL-TIME SENSING & ALERTING
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

        <div className="iot-header-actions">
          {/* Telegram Status Badge */}
          <div className="iot-status-badge iot-status-telegram" title="Telegram alert broadcast connection and active subscriber count">
            <span
              className="status-dot"
              style={{
                backgroundColor: telegramStatus?.bot_connected ? '#38bdf8' : '#94a3b8',
                boxShadow: telegramStatus?.bot_connected ? '0 0 8px #38bdf8' : 'none',
              }}
            />
            <span>TG: {telegramStatus?.bot_connected ? 'ONLINE' : 'OFFLINE'}</span>
            <span className="iot-tg-sub-pill" title="Active Telegram subscribers who receive broadcast alerts">
              👥 {telegramStatus?.active_subscribers ?? 0}
            </span>
          </div>

          {/* Hardware Connection Badge */}
          <div className={getStatusBadgeClass()}>
            <span className="status-dot" />
            <span>{getStatusBadgeLabel()}</span>
          </div>

          {/* Start / Stop Monitoring Button */}
          {!isMonitoringActive ? (
            <button
              className="iot-btn iot-btn-start"
              onClick={handleStartMonitoring}
              disabled={isActionLoading || isDisconnected}
              title={isDisconnected ? "Connect ESP32 hardware to start monitoring" : "Begin live monitoring & change detection"}
            >
              <span>▶</span>
              <span>{isActionLoading ? 'STARTING...' : 'START MONITORING'}</span>
            </button>
          ) : (
            <button
              className="iot-btn iot-btn-stop"
              onClick={() => setShowStopModal(true)}
              disabled={isActionLoading}
              title="Stop monitoring and clear temporary session data"
            >
              <span>⏹</span>
              <span>STOP MONITORING</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Telegram Subscriber Notice Banner ───────────────────── */}
      {telegramStatus && telegramStatus.active_subscribers === 0 && (
        <div className="iot-banner iot-banner-stale" style={{ marginTop: '0.75rem' }}>
          <span>✈️</span>
          <span>
            No Telegram subscribers connected. Send <code>/start</code> to the JalNetra bot (<code>@jalNetra_Helperbot</code>) to receive live monitoring alerts on your device.
          </span>
        </div>
      )}

      {/* ── Action Error Banner ────────────────────────────────── */}
      {actionError && (
        <div className="iot-banner iot-banner-disconnected" style={{ marginTop: '1rem' }}>
          <span>⚠️</span>
          <div>{actionError}</div>
        </div>
      )}

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

      {/* ── Phase 2: Active Session Statistics Bar ─────────────── */}
      {isMonitoringActive && (
        <div className="iot-session-bar">
          <div className="iot-session-status-badge">
            <span className="active-dot" />
            <span>MONITORING ACTIVE</span>
          </div>

          <div className="iot-session-metrics">
            <div className="iot-session-metric-item">
              <span className="iot-session-metric-key">Started:</span>
              <span className="iot-session-metric-val">{formatTimeOnly(monitoringStatus?.started_at)}</span>
            </div>
            <div className="iot-session-metric-item">
              <span className="iot-session-metric-key">Duration:</span>
              <span className="iot-session-metric-val">{formatDuration(monitoringStatus?.duration_seconds || 0)}</span>
            </div>
            <div className="iot-session-metric-item">
              <span className="iot-session-metric-key">Samples:</span>
              <span className="iot-session-metric-val">{monitoringStatus?.sample_count || 0}</span>
            </div>
            <div className="iot-session-metric-item">
              <span className="iot-session-metric-key">Alerts:</span>
              <span className="iot-session-metric-val" style={{ color: (monitoringStatus?.alert_count || 0) > 0 ? '#f87171' : '#34d399' }}>
                {monitoringStatus?.alert_count || 0}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Phase 2: Baseline Progress Banner ──────────────────── */}
      {isMonitoringActive && (
        <div className="iot-baseline-bar">
          {!monitoringStatus?.baseline_established ? (
            <div className="iot-baseline-establishing">
              ⏳ Establishing baseline... {monitoringStatus?.baseline_progress || 0} / {monitoringStatus?.baseline_target || 10} samples
            </div>
          ) : (
            <div className="iot-baseline-ready">
              <div>
                ✓ Baseline established · Monitoring for sudden changes
              </div>
              {monitoringStatus.baseline_values && (
                <div className="iot-baseline-chips">
                  <span className="iot-baseline-chip">Level: {monitoringStatus.baseline_values.water_level_percent?.toFixed(1)}%</span>
                  <span className="iot-baseline-chip">Temp: {monitoringStatus.baseline_values.temperature_c?.toFixed(1)}°C</span>
                  <span className="iot-baseline-chip">Clarity: {monitoringStatus.baseline_values.clarity_index?.toFixed(1)}</span>
                  <span className="iot-baseline-chip">TDS: {monitoringStatus.baseline_values.tds_ppm?.toFixed(1)} ppm</span>
                </div>
              )}
            </div>
          )}
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

      {/* ── Phase 2: Live Alerts Panel ─────────────────────────── */}
      {isMonitoringActive && (
        <div id="live-alerts-panel" className="iot-alerts-container">
          <div className="iot-alerts-header">
            <div className="iot-alerts-title">
              <span>🚨</span>
              <span>LIVE ALERTS</span>
            </div>
            <span className="iot-alert-count-pill">
              {alerts.length} {alerts.length === 1 ? 'ALERT DETECTED' : 'ALERTS DETECTED'}
            </span>
          </div>

          {alerts.length === 0 ? (
            <div className="iot-alerts-empty">
              <span>✓</span>
              <span>No anomalous sensor shifts detected. Signal is within normal thresholds.</span>
            </div>
          ) : (
            <div className="iot-alerts-list">
              {alerts.map(a => (
                <div
                  key={a.id}
                  className={`iot-alert-item ${a.severity === 'HIGH' ? 'iot-alert-item-high' : ''}`}
                >
                  <div className="iot-alert-top-row">
                    <div className="iot-alert-type-group">
                      <span className={`iot-alert-badge ${a.severity === 'HIGH' ? 'iot-alert-badge-high' : 'iot-alert-badge-warning'}`}>
                        {a.severity}
                      </span>
                      <span className="iot-alert-title">{a.title}</span>
                    </div>
                    <span className="iot-alert-time">{formatTimeOnly(a.detected_at)}</span>
                  </div>

                  <div className="iot-alert-value-row">
                    <span>{a.message}</span>
                  </div>

                  <div className="iot-alert-footer-row">
                    <span>📍 {a.water_body_name} · {a.latitude?.toFixed(4)}°N, {a.longitude?.toFixed(4)}°E</span>
                    <a
                      href={a.google_maps_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="iot-alert-map-link"
                    >
                      <span>🗺</span>
                      <span>Open in Google Maps</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
        ⚠️ IoT readings and alerts are real-time sensor anomaly signals from the connected JalNetra device.
        Sensor calibration determines measurement accuracy. Optical clarity is a relative index and does not represent laboratory NTU turbidity or biological potability.
      </div>

      {/* ── Stop Monitoring Confirmation Modal ─────────────────── */}
      {showStopModal && (
        <div className="iot-modal-backdrop">
          <div className="iot-modal">
            <div className="iot-modal-title">
              <span>⏹</span>
              <span>Stop monitoring?</span>
            </div>
            <div className="iot-modal-body">
              This will:
              <ul className="iot-modal-bullets">
                <li>Stop recording sensor readings</li>
                <li>Permanently delete temporary monitoring data</li>
                <li>Reset anomaly detection and baseline</li>
                <li>Clear the current monitoring session</li>
              </ul>
              Are you sure you want to proceed?
            </div>
            <div className="iot-modal-actions">
              <button
                className="iot-modal-btn-cancel"
                onClick={() => setShowStopModal(false)}
                disabled={isActionLoading}
              >
                CANCEL
              </button>
              <button
                className="iot-modal-btn-confirm"
                onClick={handleConfirmStop}
                disabled={isActionLoading}
              >
                {isActionLoading ? 'STOPPING...' : 'STOP MONITORING'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
