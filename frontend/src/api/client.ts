import axios from 'axios';

export const apiClient = axios.create({
  // Dev: empty baseURL => requests go to same origin (/api) and are proxied by
  // Vite to :8000 (avoids CORS). Prod: VITE_API_URL points at the backend.
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 15000,
  headers: {
    'Accept': 'application/json',
  },
});

// Response interceptor for normalized error handling (FastAPI returns {"detail": ...})
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error?.response?.data?.detail ??
      error?.message ??
      'Unknown API error';
    console.error('[api]', detail);
    return Promise.reject(error);
  },
);
