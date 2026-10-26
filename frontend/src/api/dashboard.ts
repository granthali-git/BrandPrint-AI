import apiClient from './client';
import { DashboardSummary } from '../types';

export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  database_configured: boolean;
}

export const dashboardApi = {
  /**
   * Retrieve aggregate governance metrics and compliance summary
   */
  getSummary: async (brandId?: number | string): Promise<DashboardSummary> => {
    const params: Record<string, any> = {};
    if (brandId !== undefined && brandId !== null) {
      params.brand_id = brandId;
    }
    const response = await apiClient.get<DashboardSummary>('/api/dashboard/summary', { params });
    return response.data;
  },

  /**
   * System operational and Supabase connection health check
   */
  getHealth: async (): Promise<HealthCheckResponse> => {
    const response = await apiClient.get<HealthCheckResponse>('/health');
    return response.data;
  },
};

export default dashboardApi;
