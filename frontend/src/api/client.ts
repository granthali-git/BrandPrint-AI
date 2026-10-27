import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

let rawBaseUrl =
  (typeof window !== 'undefined' ? localStorage.getItem('brandprint_api_base_url') : null) ||
  import.meta.env.VITE_API_BASE_URL ||
  'https://brandprint-ai-backend.onrender.com';
export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

let resolvedBaseUrl = API_BASE_URL;
if (typeof window !== 'undefined' && window.location.protocol === 'https:' && resolvedBaseUrl.startsWith('http://') && !resolvedBaseUrl.includes('localhost')) {
  resolvedBaseUrl = resolvedBaseUrl.replace('http://', 'https://');
}
export const BASE_URL = resolvedBaseUrl;

// Set default timeout to 120 seconds for AI pipeline execution
export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for multi-modal and LLM evaluation
});

export const api = apiClient;

// Request interceptor: automatically attach Authorization: Bearer <token> & configure upload timeouts
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // For file upload requests (FormData), ensure timeout is at least 180 seconds (3 minutes)
    if (config.data instanceof FormData) {
      config.timeout = Math.max(config.timeout || 0, 180000);
    }

    // Check BrandPrint AI auth token key and fallbacks
    const token =
      localStorage.getItem('brandprint_auth_token') ||
      localStorage.getItem('token') ||
      localStorage.getItem('access_token');
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
    const status = error?.response?.status;
    if (status === 401) {
      console.warn('[BrandPrint AI Client] Unauthorized 401: Token may have expired.');
    }

    const rawDetail = error?.response?.data?.detail;
    const parsedDetail = Array.isArray(rawDetail)
      ? rawDetail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
      : (typeof rawDetail === 'object' && rawDetail !== null)
        ? JSON.stringify(rawDetail)
        : rawDetail;

    let message: string;

    if (error?.code === 'ECONNABORTED' || (error?.message && error.message.toLowerCase().includes('timeout'))) {
      message = 'Request timed out while analyzing the asset. Multi-modal extraction or AI grounding took longer than expected. Please retry or test with a smaller image.';
    } else if (status === 502) {
      message = 'Cloud service temporarily unavailable (HTTP 502 Bad Gateway). The Render backend may be waking up from sleep or restarting. Please wait 15-30 seconds and retry.';
    } else if (status === 504) {
      message = 'Gateway timeout (HTTP 504). The compliance audit exceeded the cloud proxy timeout. Please retry.';
    } else if (status === 413) {
      message = 'File too large (HTTP 413). Please upload an asset under 10MB.';
    } else if (status === 401) {
      message = parsedDetail || 'Authentication required or session expired. Please sign in again.';
    } else if (error?.message === 'Network Error' && !error?.response) {
      message = `Unable to connect to backend at ${BASE_URL}. The cloud service may be spinning up from sleep (Render free tier takes ~20s to wake up). Please wait a moment and retry.`;
    } else {
      message = parsedDetail || error?.response?.data?.message || error?.message || 'An unexpected error occurred.';
    }

    const err = new Error(message);
    (err as any).response = error?.response;
    return Promise.reject(err);
  }
);

export default apiClient;
