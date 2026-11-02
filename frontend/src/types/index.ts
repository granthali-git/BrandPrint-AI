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
  rule_code?: string | null;
  rule_title?: string | null;
  source_file?: string | null;
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
  compliance_score?: number;
  status?: SubmissionStatus;
  ai_transparency?: AITransparencyMeta | null;
}

export interface AITransparencyLog {
  id: number;
  timestamp: string;
  service_provider: string;
  model_name: string;
  redaction_applied: boolean;
  redactions_count: number;
  redacted_fields: string[];
  tokens_or_bytes_sent: number;
  prompt_hash: string;
  user_id?: number | null;
  submission_id?: number | null;
}

export interface AITransparencyMeta {
  id?: number | null;
  service_provider: string;
  model_name: string;
  redaction_applied: boolean;
  redactions_count: number;
  redacted_fields: string[];
  tokens_or_bytes_sent: number;
  prompt_hash: string;
  is_local: boolean;
  badge_text: string;
}

export interface GuidelineGap {
  id: number;
  brand_id: number;
  submission_id?: number | null;
  claim: string;
  gap_type: 'UNCOVERED_TOPIC' | 'AMBIGUOUS_RULE';
  severity: 'MEDIUM' | 'HIGH' | 'CRITICAL';
  suggested_rule_proposal: string;
  status: 'PENDING_DECISION' | 'ADOPTED' | 'DISMISSED' | 'REVISED';
  resolution_notes?: string | null;
  created_at: string;
}

export interface ComparisonMatrixRow {
  metric: string;
  slot_a: any;
  slot_b: any;
  slot_c?: any;
  best?: string | null;
}

export interface ComparisonResultItem {
  slot_id: string;
  title: string;
  content: string;
  score: number;
  compliance_level: 'Clean' | 'Warning' | 'Critical' | string;
  word_count: number;
  violations_count: number;
  pii_redactions_count: number;
  tone_alignment: string;
  findings: Finding[];
}

export interface SlotEvaluationSummary {
  score: number;
  status: 'FULLY_COMPLIANT' | 'NEEDS_REVISION' | 'NON_COMPLIANT' | string;
  violations_count: number;
  critical_issues: string[];
}

export interface DualComparisonResponse {
  results?: ComparisonResultItem[];
  matrix?: ComparisonMatrixRow[];
  best_variant?: string;
  best_variant_title?: string;
  winner_title?: string;
  executive_verdict?: string;
  slot_evaluations?: Record<string, SlotEvaluationSummary>;
  key_improvements_noted?: string[];
  title_a: string;
  title_b: string;
  title_c?: string | null;
  content_a: string;
  content_b: string;
  content_c?: string | null;
  diff_summary: string;
  score_delta: number;
  resolved_violations: Finding[];
  new_risks: Finding[];
  persistent_violations?: Finding[];
  metrics: {
    score_a: number;
    score_b: number;
    score_c?: number | null;
    score_delta: number;
    violations_count_a: number;
    violations_count_b: number;
    violations_count_c?: number | null;
    resolved_count: number;
    new_risks_count: number;
    tone_alignment_a: string;
    tone_alignment_b: string;
    tone_alignment_c?: string | null;
    contrast_ratio_a?: string;
    contrast_ratio_b?: string;
    contrast_ratio_c?: string;
  };
  item_a: {
    title: string;
    score: number;
    violations_count: number;
    findings: Finding[];
    char_count?: number;
  };
  item_b: {
    title: string;
    score: number;
    violations_count: number;
    findings: Finding[];
    char_count?: number;
  };
  item_c?: {
    title: string;
    score: number;
    violations_count: number;
    findings: Finding[];
    char_count?: number;
  } | null;
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
  category?: string;
  severity?: 'critical' | 'high' | 'medium' | 'low';
  explanation?: string;
  conflict_explanation?: string;
  suggested_resolution?: string;
  suggested_harmonization?: string;
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
  guideline_delta?: string;
  simulated_score?: number;
  excellence_score?: number;
  excellence_status?: 'exceeds_standard' | 'meets_standard' | 'needs_work' | string;
  positive_impacts?: PositiveImpact[];
  strategic_highlights?: string[];
}

export type HistorySessionType =
  | 'SINGLE_AUDIT'
  | 'DUAL_COMPARISON'
  | 'THREE_WAY_COMPARISON'
  | 'CONTRADICTION_CHECK';

export interface HistorySessionItem {
  id: string;
  created_at: string;
  session_type: HistorySessionType;
  title: string;
  summary?: string | null;
  brand_id?: number | string | null;
  user_id?: number | string | null;
}

export interface HistorySessionDetail extends HistorySessionItem {
  inputs_payload: Record<string, any>;
  results_payload: Record<string, any>;
}

export interface HistorySessionCreate {
  session_type: HistorySessionType;
  title: string;
  summary?: string | null;
  inputs_payload: Record<string, any>;
  results_payload: Record<string, any>;
  brand_id?: number | string | null;
  user_id?: number | string | null;
}
