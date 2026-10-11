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
  geometry_geojson?: string | null;
  geometry_hash?: string | null;
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

export interface WaterBodyDiscoveryResult {
  provider: string;
  source_id: string;
  name: string;
  water_body_type?: string | null;
  country?: string | null;
  state_province?: string | null;
  district?: string | null;
  city?: string | null;
  description?: string | null;
  geometry_geojson?: string | null;
  geometry_hash?: string | null;
  min_lat?: number | null;
  min_lon?: number | null;
  max_lat?: number | null;
  max_lon?: number | null;
  centroid_lat?: number | null;
  centroid_lon?: number | null;
  area_sq_km?: number | null;
  source_metadata?: Record<string, any> | null;
}

export interface DiscoverySearchResponse {
  query: string;
  provider: string;
  results: WaterBodyDiscoveryResult[];
}

export interface ProviderStatus {
  name: string;
  enabled: boolean;
  status: string;
  description?: string | null;
}

export interface ProviderListResponse {
  providers: ProviderStatus[];
}

// Phase 3: Satellite STAC Models
export interface NormalizedAsset {
  asset_key: string;
  asset_type?: string | null;
  remote_url: string;
  mime_type?: string | null;
  file_size_bytes?: number | null;
}

export interface NormalizedScene {
  provider: string;
  collection: string;
  external_scene_id: string;
  product_id?: string | null;
  sensing_start: string;
  sensing_end?: string | null;
  cloud_cover_percent?: number | null;
  processing_level?: string | null;
  bbox?: number[] | null;
  footprint_geojson?: Record<string, any> | null;
  assets: Record<string, NormalizedAsset>;
  score?: number | null;
}

export interface SceneSearchResponse {
  water_body_id: string;
  provider: string;
  collection: string;
  results: NormalizedScene[];
}

export interface AssetAcquisitionStatus {
  asset_key: string;
  status: string;
  size_bytes?: number | null;
  sha256?: string | null;
  local_path?: string | null;
  error_message?: string | null;
}

export interface SceneAcquisitionResponse {
  scene_id: string;
  external_scene_id: string;
  status: string;
  downloaded_assets: number;
  failed_assets: number;
  already_present_assets: number;
  assets: AssetAcquisitionStatus[];
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

export async function listWaterBodies(limit = 50, offset = 0): Promise<WaterBodyListResponse> {
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

export async function searchDiscoveredWaterBodies(
  query: string,
  limit = 10,
  provider?: string
): Promise<DiscoverySearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (provider) {
    params.append('provider', provider);
  }
  const response = await fetch(`${BASE_URL}/api/v1/discovery/water-bodies/search?${params.toString()}`, {
    headers: { 'Accept': 'application/json' },
  });
  return handleResponse<DiscoverySearchResponse>(response);
}

export async function importDiscoveredWaterBody(
  result: WaterBodyDiscoveryResult
): Promise<WaterBody> {
  const response = await fetch(`${BASE_URL}/api/v1/discovery/water-bodies/import`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(result),
  });
  return handleResponse<WaterBody>(response);
}

export async function getDiscoveryProviders(): Promise<ProviderListResponse> {
  const response = await fetch(`${BASE_URL}/api/v1/discovery/providers`, {
    headers: { 'Accept': 'application/json' },
  });
  return handleResponse<ProviderListResponse>(response);
}

// Satellite API
export async function searchSatelliteScenes(
  waterBodyId: string,
  startDate?: string,
  endDate?: string,
  maxCloudCover = 30,
  limit = 10
): Promise<SceneSearchResponse> {
  const params = new URLSearchParams({
    water_body_id: waterBodyId,
    max_cloud_cover: String(maxCloudCover),
    limit: String(limit),
  });
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const response = await fetch(`${BASE_URL}/api/v1/satellite/scenes/search?${params.toString()}`, {
    headers: { 'Accept': 'application/json' },
  });
  return handleResponse<SceneSearchResponse>(response);
}

export async function acquireSceneAssets(
  externalSceneId: string,
  assets: string[]
): Promise<SceneAcquisitionResponse> {
  const response = await fetch(`${BASE_URL}/api/v1/satellite/scenes/${encodeURIComponent(externalSceneId)}/acquire`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ assets }),
  });
  return handleResponse<SceneAcquisitionResponse>(response);
}
