import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const api = apiClient;

// Request interceptor: automatically attach Authorization: Bearer <token>
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Check both standard token keys
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor: intercept unauthenticated requests and parse real backend feedback
apiClient.interceptors.response.use(
  (response) => response,
  (error: any) => {
    if (error?.response?.status === 401) {
      console.warn('[BrandPrint AI Client] Unauthorized 401: Token may have expired.');
    }
    const rawDetail = error?.response?.data?.detail;
    const parsedDetail = Array.isArray(rawDetail)
      ? rawDetail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
      : (typeof rawDetail === 'object' && rawDetail !== null)
        ? JSON.stringify(rawDetail)
        : rawDetail;

    const message =
      parsedDetail ||
      error?.response?.data?.message ||
      (error?.message === 'Network Error'
        ? 'Backend unreachable at port 8001. Please verify Uvicorn is active.'
        : error?.message || 'An unexpected error occurred');

    const err = new Error(message);
    (err as any).response = error?.response;
    return Promise.reject(err);
  }
);

export default apiClient;
