import { useEffect, useState, useRef, useCallback } from 'react';
import { IoTAlert, getAlertsStreamUrl } from '../api/iot';

interface UseIoTAlertsOptions {
  enabled?: boolean;
  onNewAlert?: (alert: IoTAlert) => void;
}

export function useIoTAlerts({ enabled = true, onNewAlert }: UseIoTAlertsOptions = {}) {
  const [alerts, setAlerts] = useState<IoTAlert[]>([]);
  const [floatingAlert, setFloatingAlert] = useState<IoTAlert | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const seenIdsRef = useRef<Set<string>>(new Set());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(2000);
  const eventSourceRef = useRef<EventSource | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const dismissFloatingAlert = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setFloatingAlert(null);
  }, []);

  const triggerFloatingAlert = useCallback((alert: IoTAlert) => {
    setFloatingAlert(alert);

    // Auto-dismiss after 9 seconds
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = setTimeout(() => {
      if (isMountedRef.current) {
        setFloatingAlert(null);
      }
    }, 9000);
  }, []);

  const clearAlerts = useCallback(() => {
    dismissFloatingAlert();
    setAlerts([]);
    seenIdsRef.current.clear();
  }, [dismissFloatingAlert]);

  useEffect(() => {
    isMountedRef.current = true;

    if (!enabled) {
      return;
    }

    const connect = () => {
      const url = getAlertsStreamUrl();
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        if (!isMountedRef.current) return;
        setIsConnected(true);
        reconnectDelayRef.current = 2000; // Reset backoff
      };

      es.addEventListener('connected', () => {
        if (!isMountedRef.current) return;
        setIsConnected(true);
      });

      es.addEventListener('iot_alert', (evt: MessageEvent) => {
        if (!isMountedRef.current) return;
        try {
          const raw = JSON.parse(evt.data);
          const alert: IoTAlert = raw;

          // Deduplicate
          if (seenIdsRef.current.has(alert.id)) {
            return;
          }
          seenIdsRef.current.add(alert.id);

          setAlerts((prev) => [alert, ...prev]);
          triggerFloatingAlert(alert);

          if (onNewAlert) {
            onNewAlert(alert);
          }
        } catch (err) {
          console.error('[useIoTAlerts] Failed to parse iot_alert event:', err);
        }
      });

      es.addEventListener('session_stopped', () => {
        if (!isMountedRef.current) return;
        // Session stopped: clear website session alerts and close floating alert
        clearAlerts();
      });

      es.onerror = () => {
        if (!isMountedRef.current) return;
        setIsConnected(false);
        es.close();

        // Reconnect with backoff
        const delay = reconnectDelayRef.current;
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 1.5, 30000);
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current && enabled) {
            connect();
          }
        }, delay);
      };
    };

    connect();

    return () => {
      isMountedRef.current = false;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [enabled, triggerFloatingAlert, clearAlerts, onNewAlert]);

  return {
    alerts,
    setAlerts,
    floatingAlert,
    dismissFloatingAlert,
    clearAlerts,
    isConnected,
  };
}
