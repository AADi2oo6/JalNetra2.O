export interface HealthStatus {
  status: string;
  service: string;
  version: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export interface WaterBody {
  id: string;
  name: string;
  normalized_name: string;
  country?: string | null;
  state_province?: string | null;
  district?: string | null;
  city?: string | null;
  source: string;
  source_id?: string | null;
  water_body_type?: string | null;
  description?: string | null;
  area_sq_km?: number | null;
  centroid_lat?: number | null;
  centroid_lon?: number | null;
  min_lat?: number | null;
  min_lon?: number | null;
  max_lat?: number | null;
  max_lon?: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WaterBodyListResponse {
  items: WaterBody[];
  total: number;
  limit: number;
  offset: number;
}

export interface StorageStatus {
  database: {
    status: string;
    engine: string;
    url_type: string;
  };
  directories: Record<string, string>;
  details: Record<
    string,
    {
      path: string;
      exists: boolean;
      is_directory: boolean;
      file_count: number;
    }
  >;
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMsg = `Server responded with status ${response.status}`;
    try {
      const errData: ApiError = await response.json();
      if (errData?.error?.message) {
        errorMsg = errData.error.message;
      }
    } catch {
      // Fallback
    }
    throw new Error(errorMsg);
  }
  return response.json();
}

export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${BASE_URL}/api/v1/health`, {
    headers: { 'Accept': 'application/json' },
  });
  return handleResponse<HealthStatus>(response);
}

export async function getStorageStatus(): Promise<StorageStatus> {
  const response = await fetch(`${BASE_URL}/api/v1/storage/status`, {
    headers: { 'Accept': 'application/json' },
  });
  return handleResponse<StorageStatus>(response);
}

export async function listWaterBodies(limit = 20, offset = 0): Promise<WaterBodyListResponse> {
  const response = await fetch(`${BASE_URL}/api/v1/water-bodies?limit=${limit}&offset=${offset}`, {
    headers: { 'Accept': 'application/json' },
  });
  return handleResponse<WaterBodyListResponse>(response);
}

export async function createWaterBody(data: {
  name: string;
  country?: string;
  state_province?: string;
  source?: string;
  source_id?: string;
  area_sq_km?: number;
}): Promise<WaterBody> {
  const response = await fetch(`${BASE_URL}/api/v1/water-bodies`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(data),
  });
  return handleResponse<WaterBody>(response);
}
