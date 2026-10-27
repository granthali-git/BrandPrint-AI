export type UserRole = 'Admin' | 'BrandManager' | 'Reviewer' | 'Creator';

export interface User {
  id: number | string;
  email: string;
  name?: string;
  full_name?: string;
  company?: string;
  role: UserRole;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type RuleCategory = 'tone' | 'visual' | 'prohibited_claim' | 'fact' | 'accessibility';

export interface GuidelineRule {
  id: number | string;
  brand_id: number | string;
  category: RuleCategory;
  title: string;
  rule_text: string;
  rule_code: string;
  source_file?: string | null;
  is_active: boolean;
  version: number;
  created_at?: string;
  updated_at?: string;
}

export interface GuidelineRuleCreatePayload {
  brand_id: number | string;
  category: RuleCategory;
  title: string;
  rule_text: string;
  rule_code?: string;
}

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'advisory';
export type UserAction = 'pending' | 'accepted' | 'rejected' | 'edited';
export type SubmissionStatus = 'draft' | 'pending_review' | 'approved' | 'changes_required' | 'rejected';
export type ContentType = 'text' | 'file' | 'url';
export type ReviewDecisionType = 'approved' | 'changes_required' | 'rejected';

export interface FixVariation {
  style: string;
  text: string;
}

export interface Finding {
  id: number | string;
  submission_id: number | string;
  version: number;
  rule_id?: number | string | null;
  category?: string | null;
  severity: SeverityLevel;
  issue_type: string;
  flagged_text?: string | null;
  context_span?: string | null;
  explanation: string;
  cited_quote?: string | null;
  suggested_fix?: string | null;
  fix_variations?: FixVariation[] | null;
  strategic_tip?: string | null;
  user_action: UserAction;
  is_visual?: boolean;
  visual_element?: string | null;
  observed_evidence?: string | null;
  created_at?: string;
  rule?: GuidelineRule | null;
}

export interface ContentSubmission {
  id: number | string;
  brand_id: number | string;
  title?: string | null;
  content_type: ContentType;
  raw_content?: string | null;
  extracted_text?: string | null;
  current_version: number;
  status: SubmissionStatus;
  image_preview_url?: string | null;
  visual_analysis_status?: 'complete' | 'incomplete' | 'failed' | null;
  visual_analysis_message?: string | null;
  is_image_asset?: boolean;
  created_at: string;
  updated_at?: string;
  findings?: Finding[];
}

export interface ReviewResponse {
  submission: ContentSubmission;
  extracted_text?: string;
  findings: Finding[];
  total_findings: number;
  deterministic_count?: number;
  ai_grounded_count?: number;
  visual_findings_count?: number;
  image_preview_url?: string | null;
  visual_analysis_status?: 'complete' | 'incomplete' | 'failed' | null;
  visual_analysis_message?: string | null;
  is_image_asset?: boolean;
  brand_id?: number | string;
  status?: SubmissionStatus;
}

export interface ReviewDecisionRecord {
  id: number | string;
  submission_id: number | string;
  version: number;
  reviewer_id: number | string;
  decision: ReviewDecisionType;
  notes?: string | null;
  created_at: string;
}

export interface ContradictionPair {
  id?: string | number;
  conflict_id?: string;
  rule_a: Partial<GuidelineRule> | string | any;
  rule_b: Partial<GuidelineRule> | string | any;
  rule_a_id?: number | string;
  rule_b_id?: number | string;
  rule_a_title?: string;
  rule_b_title?: string;
  rule_a_text?: string;
  rule_b_text?: string;
  conflict_title?: string;
  contradiction_reason?: string;
  conflict_type?: string;
  tension_type?: 'Direct Conflict' | 'Policy Paradox' | 'Regulatory Overreach' | string;
  severity?: 'critical' | 'high' | 'medium' | 'low';
  explanation?: string;
  conflict_explanation?: string;
  suggested_resolution?: string;
  recommendation?: string;
  status?: string;
}


export interface ContradictionsResponse {
  brand_id?: number | string;
  total_contradictions: number;
  contradictions: ContradictionPair[];
}

export interface TopViolatedRule {
  rule_id: number | string;
  rule_code: string;
  title: string;
  category: string;
  violation_count: number;
}

export interface DashboardSummary {
  total_submissions: number;
  total_checks: number;
  status_counts: {
    approved: number;
    changes_required: number;
    rejected: number;
    draft: number;
    [key: string]: number;
  };
  pass_rate: number;
  top_violated_rules: TopViolatedRule[];
  total_contradictions?: number;
  total_contradictions_detected?: number;
  total_violations_detected?: number;
  category_breakdown?: Record<string, number>;
  common_issues?: Array<{ issue_type: string; count: number }>;
}

export interface PositiveImpact {
  category: string;
  metric: string;
  explanation: string;
}

export interface WhatIfSimulationResult {
  submission_id?: number | string;
  original_findings_count?: number;
  simulated_findings_count?: number;
  resolved_findings?: Finding[];
  remaining_findings?: Finding[];
  new_findings?: Finding[];
  resolved_issues?: any[];
  remaining_issues?: any[];
  introduced_issues?: any[];
  resolved_violations?: any[];
  remaining_violations?: any[];
  introduced_violations?: any[];
  summary?: any;
  safety_score?: number;
  baseline_score?: number;
  excellence_score?: number;
  excellence_status?: 'exceeds_standard' | 'meets_standard' | 'needs_work' | string;
  positive_impacts?: PositiveImpact[];
  strategic_highlights?: string[];
}
