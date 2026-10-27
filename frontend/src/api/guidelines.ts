import apiClient from './client';
import { GuidelineRule, GuidelineRuleCreatePayload, ContradictionsResponse } from '../types';

export const guidelinesApi = {
  /**
   * List active guidelines for a given brand
   */
  list: async (brandId?: number | string, category?: string, isActive: boolean = true): Promise<GuidelineRule[]> => {
    const params: Record<string, any> = { is_active: isActive };
    if (brandId !== undefined && brandId !== null) {
      params.brand_id = brandId;
    }
    if (category) {
      params.category = category;
    }
    const response = await apiClient.get<GuidelineRule[]>('/api/guidelines', { params });
    return response.data;
  },

  /**
   * Create a new structured brand guideline rule or submit multipart form data
   */
  create: async (
    rulePayload: GuidelineRuleCreatePayload | FormData
  ): Promise<GuidelineRule | GuidelineRule[]> => {
    if (rulePayload instanceof FormData) {
      const response = await apiClient.post<GuidelineRule | GuidelineRule[]>('/api/guidelines', rulePayload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    }

    const response = await apiClient.post<GuidelineRule>('/api/guidelines', rulePayload);
    return response.data;
  },

  /**
   * Upload guideline document (PDF, DOCX, PPTX, or TXT) to auto-extract atomic rules
   */
  uploadDocument: async (
    brandId: number | string,
    file: File,
    category?: string,
    autoCommit: boolean = true,
    previewOnly: boolean = false
  ): Promise<any> => {
    const formData = new FormData();
    formData.append('brand_id', String(brandId));
    formData.append('file', file);
    formData.append('auto_commit', String(autoCommit));
    formData.append('preview_only', String(previewOnly));
    if (category) {
      formData.append('category', category);
    }
    const response = await apiClient.post<any>('/api/guidelines/upload-document', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000, // 3 minutes for heavy document parsing
    });
    return response.data;
  },

  /**
   * Ingest guideline rules from a public documentation URL (Notion, Google Docs, Wiki)
   */
  ingestUrl: async (
    brandId: number | string,
    url: string,
    autoCommit: boolean = true,
    previewOnly: boolean = false
  ): Promise<any> => {
    const response = await apiClient.post<any>('/api/guidelines/ingest-url', {
      brand_id: brandId,
      url,
      auto_commit: autoCommit,
      preview_only: previewOnly,
    });
    return response.data;
  },

  /**
   * Bulk save approved/edited guideline rules from the review drawer
   */
  bulkSave: async (
    brandId: number | string,
    rules: any[],
    sourceName?: string
  ): Promise<any> => {
    const response = await apiClient.post<any>('/api/guidelines/bulk-save', {
      brand_id: brandId,
      rules,
      source_name: sourceName || 'Ingested Content',
    });
    return response.data;
  },


  /**
   * Check for contradictions across brand guidelines
   */
  checkContradictions: async (
    brandId: number | string = 1,
    proposedRules?: any[]
  ): Promise<ContradictionsResponse | any> => {
    const params = { brand_id: brandId };
    const payload: any = { brand_id: brandId };
    if (proposedRules && proposedRules.length > 0) {
      payload.rules = proposedRules;
      payload.new_statements = proposedRules;
    }
    const response = await apiClient.post<ContradictionsResponse | any>(
      '/api/guidelines/check-contradictions',
      payload,
      { params }
    );
    return response.data;
  },

  /**
   * Deactivate a conflicting guideline rule in the catalog
   */
  deactivateRule: async (ruleId: number | string): Promise<any> => {
    const response = await apiClient.post(`/api/guidelines/${ruleId}/deactivate`);
    return response.data;
  },

  /**
   * Record legal sign-off and resolve a policy contradiction
   */
  resolveContradiction: async (payload: {
    conflict_id: string;
    strategy: 'amend' | 'deactivate' | 'merge';
    rule_id?: number | string;
    secondary_rule_id?: number | string;
    amendment_text?: string;
    approver_role?: string;
    approver_name?: string;
    justification?: string;
    brand_id?: number | string;
  }): Promise<any> => {
    const response = await apiClient.post('/api/guidelines/contradictions/resolve', payload);
    return response.data;
  },
};

export default guidelinesApi;
