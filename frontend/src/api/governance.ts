import apiClient from './client';
import { AITransparencyLog } from '../types';

export const governanceApi = {
  getAITransparencyLogs: async (limit: number = 25): Promise<AITransparencyLog[]> => {
    const response = await apiClient.get<AITransparencyLog[]>('/api/governance/ai-transparency-logs', {
      params: { limit },
    });
    return response.data;
  },
};

export default governanceApi;

