import apiClient from './client';
import {
  ReviewResponse,
  ReviewDecisionRecord,
  ReviewDecisionType,
  WhatIfSimulationResult,
  Finding,
  UserAction,
} from '../types';

export interface SubmitReviewPayload {
  brand_id: number | string;
  content_type: 'text' | 'file' | 'url';
  raw_content?: string;
  url?: string;
  file?: File;
}

export const reviewsApi = {
  /**
   * Submit content (raw text, uploaded document/image, or live URL) for compliance review
   * Supports both FormData and structured plain objects
   */
  submitReview: async (
    payload: FormData | SubmitReviewPayload
  ): Promise<ReviewResponse> => {
    if (payload instanceof FormData) {
      const response = await apiClient.post<ReviewResponse>('/api/reviews', payload, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000, // 3 minutes for complex multi-modal files
      });
      return response.data;
    }

    // If payload contains a file, construct FormData automatically
    if (payload.file || payload.content_type === 'file') {
      const formData = new FormData();
      formData.append('brand_id', String(payload.brand_id));
      formData.append('content_type', payload.content_type || 'file');
      if (payload.file) {
        formData.append('file', payload.file);
      }
      if (payload.raw_content) {
        formData.append('raw_content', payload.raw_content);
      }
      if (payload.url) {
        formData.append('url', payload.url);
      }

      const response = await apiClient.post<ReviewResponse>('/api/reviews', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000, // 3 minutes for complex documents/images
      });
      return response.data;
    }

    // Submit as JSON for text/URL
    const response = await apiClient.post<ReviewResponse>('/api/reviews', payload, {
      timeout: 120000, // 2 minutes for AI pipeline execution
    });
    return response.data;
  },

  /**
   * What-If Simulator: test revised copy or draft guidelines without altering production data
   */
  simulateRevision: async (
    submissionId: number | string,
    revisedContent: string,
    draftRules?: any[]
  ): Promise<WhatIfSimulationResult> => {
    const response = await apiClient.post<WhatIfSimulationResult>(
      `/api/reviews/${submissionId}/simulate`,
      {
        revised_content: revisedContent,
        draft_rules: draftRules,
      }
    );
    return response.data;
  },

  /**
   * Submit reviewer or brand manager compliance decision (approved, changes_required, rejected)
   */
  submitDecision: async (
    submissionId: number | string,
    decision: ReviewDecisionType,
    notes?: string
  ): Promise<ReviewDecisionRecord> => {
    const response = await apiClient.post<ReviewDecisionRecord>(
      `/api/reviews/${submissionId}/decision`,
      {
        decision,
        comment: notes || '',
        notes: notes || '',
      }
    );
    return response.data;
  },

  /**
   * List recent content submissions
   */
  list: async (brandId?: number | string, limit: number = 10): Promise<any[]> => {
    const params: Record<string, any> = { limit };
    if (brandId !== undefined && brandId !== null) {
      params.brand_id = brandId;
    }
    const response = await apiClient.get<any[]>('/api/reviews', { params });
    return response.data;
  },

  /**
   * Retrieve full details of a submission and its active findings
   */
  getById: async (submissionId: number | string): Promise<ReviewResponse> => {
    const response = await apiClient.get<ReviewResponse>(`/api/reviews/${submissionId}`);
    return response.data;
  },

  /**
   * Update reviewer/creator action on an individual finding
   */
  updateFindingAction: async (
    findingId: number | string,
    action: UserAction,
    suggestedFix?: string
  ): Promise<Finding> => {
    const response = await apiClient.patch<Finding>(`/api/reviews/findings/${findingId}`, {
      action,
      suggested_fix: suggestedFix,
    });
    return response.data;
  },

  /**
   * Generate official brand compliance clearance certificate
   */
  getCertificate: async (submissionId: number | string): Promise<any> => {
    const response = await apiClient.get<any>(`/api/reviews/${submissionId}/certificate`);
    return response.data;
  },

  /**
   * Poll review job status
   */
  getJobStatus: async (submissionId: number | string): Promise<any> => {
    const response = await apiClient.get<any>(`/api/reviews/${submissionId}/status`);
    return response.data;
  },
};

export default reviewsApi;
