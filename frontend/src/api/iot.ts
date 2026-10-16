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
