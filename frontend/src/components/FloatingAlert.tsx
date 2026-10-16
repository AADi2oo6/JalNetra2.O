import React from 'react';
import { IoTAlert } from '../api/iot';
import './FloatingAlert.css';

interface FloatingAlertProps {
  alert: IoTAlert | null;
  onDismiss: () => void;
  onViewAlert?: (alert: IoTAlert) => void;
}

export const FloatingAlert: React.FC<FloatingAlertProps> = ({
  alert,
  onDismiss,
  onViewAlert,
}) => {
  if (!alert) return null;

  const handleViewAlert = () => {
    onDismiss();
    if (onViewAlert) {
      onViewAlert(alert);
    } else {
      // Default scrolling behavior
      const target = document.getElementById('live-alerts-panel');
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        target.classList.add('alert-panel-highlight');
        setTimeout(() => {
          target.classList.remove('alert-panel-highlight');
        }, 2500);
      }
    }
  };

  const getSeverityClass = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'severity-critical';
      case 'HIGH':
        return 'severity-high';
      case 'WARNING':
        return 'severity-warning';
      default:
        return 'severity-info';
    }
  };

  const formatDelta = () => {
    const sign = alert.change > 0 ? '+' : '';
    return `${alert.previous_value.toFixed(1)}${alert.unit} → ${alert.current_value.toFixed(1)}${alert.unit} (${sign}${alert.change.toFixed(1)}${alert.unit})`;
  };

  const formatTime = (isoString?: string) => {
    if (!isoString) return 'Just now';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className={`floating-alert-container ${getSeverityClass(alert.severity)}`} role="alert">
      <div className="floating-alert-header">
        <div className="floating-alert-title">
          <span className="floating-alert-icon">🚨</span>
          <span className="floating-alert-heading">NEW WATER MONITORING ALERT</span>
        </div>
        <button
          className="floating-alert-close"
          onClick={onDismiss}
          aria-label="Dismiss alert"
          title="Dismiss toast"
        >
          ×
        </button>
      </div>

      <div className="floating-alert-body">
        <div className="floating-alert-waterbody">
          💧 {alert.water_body_name}
        </div>

        <div className="floating-alert-type">
          {alert.title}
        </div>

        <div className="floating-alert-delta">
          {formatDelta()}
        </div>

        <div className="floating-alert-meta">
          <span className={`floating-severity-badge ${getSeverityClass(alert.severity)}`}>
            ● {alert.severity}
          </span>
          <span className="floating-alert-time">
            Detected: {formatTime(alert.detected_at)}
          </span>
        </div>

        <div className="floating-alert-location">
          📍 {alert.latitude.toFixed(3)}°N, {alert.longitude.toFixed(3)}°E
        </div>
      </div>

      <div className="floating-alert-footer">
        <button
          className="floating-alert-view-btn"
          onClick={handleViewAlert}
        >
          VIEW ALERT →
        </button>
      </div>
    </div>
  );
};
