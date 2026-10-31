import { apiClient } from './client';
import {
  HistorySessionItem,
  HistorySessionDetail,
  HistorySessionCreate,
} from '../types';

export const historyApi = {
  /**
   * Save completed audit, comparison, or contradiction session.
   */
  async saveHistory(payload: HistorySessionCreate): Promise<{ id: string; status: string }> {
    const res = await apiClient.post('/api/history', payload);
    return res.data;
  },

  /**
   * List past sessions with optional query parameters.
   */
  async getHistoryList(params?: {
    search?: string;
    type?: string;
    limit?: number;
  }): Promise<HistorySessionItem[]> {
    const res = await apiClient.get('/api/history', { params });
    return res.data;
  },

  /**
   * Retrieve full details of a session for state re-hydration.
   */
  async getHistoryDetail(id: string): Promise<HistorySessionDetail> {
    const res = await apiClient.get(`/api/history/${id}`);
    return res.data;
  },

  /**
   * Delete a single session record by ID.
   */
  async deleteHistory(id: string): Promise<{ id: string; status: string }> {
    const res = await apiClient.delete(`/api/history/${id}`);
    return res.data;
  },

  /**
   * Clear all session history.
   */
  async clearAllHistory(): Promise<{ status: string; deleted_count: number }> {
    const res = await apiClient.delete('/api/history/clear-all');
    return res.data;
  },
};
