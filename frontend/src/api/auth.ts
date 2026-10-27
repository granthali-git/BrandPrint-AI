import apiClient from './client';
import { AuthResponse, User } from '../types';

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
  company?: string;
  role?: string;
}

export interface ForgotPasswordResponse {
  message: string;
  status: string;
}

export const authApi = {
  /**
   * Authenticate user with email & password and persist JWT token
   */
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/auth/login', {
      email,
      password,
    });
    if (response.data?.access_token) {
      localStorage.setItem('brandprint_auth_token', response.data.access_token);
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('access_token', response.data.access_token);
      if (response.data.user) {
        localStorage.setItem('brandprint_user', JSON.stringify(response.data.user));
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
    }
    return response.data;
  },

  /**
   * Register a new user account with enterprise profile fields
   */
  register: async (payload: RegisterPayload): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/auth/register', payload);
    if (response.data?.access_token) {
      localStorage.setItem('brandprint_auth_token', response.data.access_token);
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('access_token', response.data.access_token);
      if (response.data.user) {
        localStorage.setItem('brandprint_user', JSON.stringify(response.data.user));
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
    }
    return response.data;
  },

  /**
   * Request password reset instructions
   */
  forgotPassword: async (email: string): Promise<ForgotPasswordResponse> => {
    const response = await apiClient.post<ForgotPasswordResponse>('/api/auth/forgot-password', {
      email,
    });
    return response.data;
  },

  /**
   * Retrieve current authenticated user profile via Bearer token
   */
  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/auth/me');
    if (response.data) {
      localStorage.setItem('brandprint_user', JSON.stringify(response.data));
      localStorage.setItem('user', JSON.stringify(response.data));
    }
    return response.data;
  },

  /**
   * Get cached user from localStorage or null
   */
  getCurrentUser: (): User | null => {
    const stored = localStorage.getItem('brandprint_user') || localStorage.getItem('user');
    if (!stored) return null;
    try {
      return JSON.parse(stored) as User;
    } catch {
      return null;
    }
  },

  /**
   * Get active token or null
   */
  getToken: (): string | null => {
    return (
      localStorage.getItem('brandprint_auth_token') ||
      localStorage.getItem('token') ||
      localStorage.getItem('access_token')
    );
  },

  /**
   * Sign out and purge stored credentials
   */
  logout: () => {
    localStorage.removeItem('brandprint_auth_token');
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('brandprint_user');
    localStorage.removeItem('user');
  },
};

export default authApi;
