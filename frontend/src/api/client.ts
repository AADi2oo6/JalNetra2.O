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

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${BASE_URL}/api/v1/health`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    let errorMsg = `Server responded with status ${response.status}`;
    try {
      const errData: ApiError = await response.json();
      if (errData?.error?.message) {
        errorMsg = errData.error.message;
      }
    } catch {
      // Fallback to HTTP error
    }
    throw new Error(errorMsg);
  }

  return response.json();
}
