import apiClient from './client';
import { AuthResponse, User } from '../types';

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
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('access_token', response.data.access_token);
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
    }
    return response.data;
  },

  /**
   * Register a new user account
   */
  register: async (email: string, password: string, role: string = 'Creator'): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/auth/register', {
      email,
      password,
      role,
    });
    if (response.data?.access_token) {
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('access_token', response.data.access_token);
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
    }
    return response.data;
  },

  /**
   * Get cached user or null
   */
  getCurrentUser: (): User | null => {
    const stored = localStorage.getItem('user');
    if (!stored) return null;
    try {
      return JSON.parse(stored) as User;
    } catch {
      return null;
    }
  },

  /**
   * Sign out and clear cached credentials
   */
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },
};

export default authApi;
