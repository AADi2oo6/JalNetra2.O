import { resolveApiUrl } from './client';

export type IoTConnectionState = 'CONNECTED' | 'STALE' | 'DISCONNECTED';

export interface IoTReading {
  device: string;
  temperature_c: number;
  temperature_valid: boolean;
  turbidity_raw: number;
  clarity_index: number;
  turbidity_status: string;
  tds_raw: number;
  tds_ppm: number;
  water_level_raw: number;
  water_level_percent: number;
  received_at: string;
}

export interface IoTStatusResponse {
  enabled: boolean;
  connected: boolean;
  port: string;
  baud_rate: number;
  device: string;
  status: IoTConnectionState;
  last_received_at?: string | null;
  seconds_since_last_reading?: number | null;
  target_water_body_name: string;
}

export interface IoTLatestResponse {
  available: boolean;
  device?: string;
  temperature_c?: number;
  temperature_valid?: boolean;
  turbidity_raw?: number;
  clarity_index?: number;
  turbidity_status?: string;
  tds_raw?: number;
  tds_ppm?: number;
  water_level_raw?: number;
  water_level_percent?: number;
  received_at?: string;
  status: IoTConnectionState;
  seconds_ago?: number | null;
  target_water_body_name: string;
  message?: string | null;
}

export type IoTAlertSeverity = 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL';

export type IoTAlertType =
  | 'WATER_LEVEL_INCREASE'
  | 'WATER_LEVEL_DECREASE'
  | 'CLARITY_CHANGE'
  | 'TEMPERATURE_CHANGE'
  | 'TDS_CHANGE';

export interface IoTAlert {
  id: string;
  session_id: string;
  water_body_id: string;
  water_body_name: string;
  type: IoTAlertType;
  severity: IoTAlertSeverity;
  title: string;
  message: string;
  sensor_name: string;
  previous_value: number;
  current_value: number;
  change: number;
  unit: string;
  detected_at: string;
  latitude: number;
  longitude: number;
  google_maps_url: string;
  extra_details?: Record<string, any> | null;
}

export interface MonitoringSessionStatus {
  active: boolean;
  session_id?: string | null;
  water_body_id?: string | null;
  water_body_name: string;
  started_at?: string | null;
  duration_seconds: number;
  sample_count: number;
  alert_count: number;
  baseline_established: boolean;
  baseline_progress: number;
  baseline_target: number;
  baseline_values?: Record<string, number> | null;
}

export interface StartMonitoringResponse {
  success: boolean;
  session_id?: string | null;
  message: string;
  water_body_id?: string | null;
  water_body_name: string;
}

export interface StopMonitoringResponse {
  success: boolean;
  samples_recorded: number;
  alerts_generated: number;
  temporary_data_deleted: boolean;
  message: string;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Server returned ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) {
        msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data?.error?.message) {
        msg = data.error.message;
      }
    } catch {
      // fallback
    }
    throw new Error(msg);
  }
  return res.json();
}

export async function getIoTStatus(): Promise<IoTStatusResponse> {
  const url = resolveApiUrl('/api/v1/iot/status');
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return handleResponse<IoTStatusResponse>(res);
}

export async function getLatestIoTReading(): Promise<IoTLatestResponse> {
  const url = resolveApiUrl('/api/v1/iot/latest');
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return handleResponse<IoTLatestResponse>(res);
}

export async function getMonitoringStatus(): Promise<MonitoringSessionStatus> {
  const url = resolveApiUrl('/api/v1/iot/monitoring/status');
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return handleResponse<MonitoringSessionStatus>(res);
}

export async function startMonitoring(
  waterBodyId?: string,
  forceStart: boolean = false
): Promise<StartMonitoringResponse> {
  const url = resolveApiUrl('/api/v1/iot/monitoring/start');
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      water_body_id: waterBodyId,
      force_start: forceStart,
    }),
  });
  return handleResponse<StartMonitoringResponse>(res);
}

export async function stopMonitoring(): Promise<StopMonitoringResponse> {
  const url = resolveApiUrl('/api/v1/iot/monitoring/stop');
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
    },
  });
  return handleResponse<StopMonitoringResponse>(res);
}

export async function getMonitoringAlerts(): Promise<IoTAlert[]> {
  const url = resolveApiUrl('/api/v1/iot/monitoring/alerts');
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return handleResponse<IoTAlert[]>(res);
}
