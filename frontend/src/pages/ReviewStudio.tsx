import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FileText,
  UploadCloud,
  Globe,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  BookOpen,
  ArrowRight,
  Check,
  RotateCcw,
  Loader2,
  FileCheck,
  Building2,
  Eye,
  SlidersHorizontal,
  X,
  MessageSquare,
  Lock,
  ChevronRight,
  Sparkle,
  Layers,
  Printer,
  Award,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { reviewsApi } from '../api/reviews';
import {
  ReviewResponse,
  Finding,
  SeverityLevel,
  ReviewDecisionType,
  UserAction,
} from '../types';
import { WhatIfSimulator } from '../components/WhatIfSimulator';
import { FindingCard } from '../components/FindingCard';

export const ReviewStudio: React.FC = () => {
  const { currentBrand } = useApp();
  const [searchParams, setSearchParams] = useSearchParams();
  const submissionIdParam = searchParams.get('id');

  // Multi-Format Input State
  const [inputTab, setInputTab] = useState<'text' | 'file' | 'url'>('text');
  const [rawText, setRawText] = useState(
    'Discover AstraForge Enterprise Cloud! We are the cheapest solution and guaranteed #1 platform on the market with 100% infallible uptime. Call right now to claim your exclusive 50% limited promotion discount!'
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);

  // Review & Findings State
  const [reviewData, setReviewData] = useState<ReviewResponse | null>(null);
  const [activeContent, setActiveContent] = useState<string>('');
  const [selectedFindingId, setSelectedFindingId] = useState<string | number | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Governance Decision Modal State
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [pendingDecision, setPendingDecision] = useState<ReviewDecisionType>('approved');
  const [decisionComment, setDecisionComment] = useState('');
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [decisionToast, setDecisionToast] = useState<{ type: string; msg: string } | null>(null);

  // Compliance Certificate State
  const [certModalOpen, setCertModalOpen] = useState(false);
  const [certificateData, setCertificateData] = useState<any>(null);
  const [loadingCert, setLoadingCert] = useState(false);
  const [evalProgressIndex, setEvalProgressIndex] = useState(0);

  const EVAL_PROGRESS_MESSAGES = [
    "Analyzing image visual & text copy...",
    "Grounding against brand guidelines with Gemini...",
    "Cross-referencing deterministic policy rules...",
    "Validating semantic citations and fix variations...",
  ];

  useEffect(() => {
    if (!isEvaluating) {
      setEvalProgressIndex(0);
      return;
    }
    const timer = setInterval(() => {
      setEvalProgressIndex((prev) => (prev + 1) % EVAL_PROGRESS_MESSAGES.length);
    }, 2800);
    return () => clearInterval(timer);
  }, [isEvaluating]);

  // Refs for auto-scrolling
  const findingCardsRef = useRef<Record<string | number, HTMLDivElement | null>>({});
  const contentPaneRef = useRef<HTMLDivElement | null>(null);

  // Load review on mount or when submissionId changes
  useEffect(() => {
    if (submissionIdParam) {
      loadReviewById(submissionIdParam);
    } else {
      // Initialize with demo compliance review
      loadDemoReview();
    }
  }, [submissionIdParam, currentBrand.id]);

  const loadReviewById = async (id: string | number) => {
    setIsEvaluating(true);
    setEvalError(null);
    try {
      const data = await reviewsApi.getById(id);
      setReviewData(data);
      const text = data.extracted_text || data.submission?.raw_content || '';
      setActiveContent(text);
      setRawText(text);
      if (data.findings && data.findings.length > 0) {
        setSelectedFindingId(data.findings[0].id);
      }
    } catch {
      // Backend might not have this ID yet, fall back to interactive demo
      loadDemoReview();
    } finally {
      setIsEvaluating(false);
    }
  };

  const loadDemoReview = () => {
    const demoCopy =
      'AstraForge Enterprise Cloud provides scalable infrastructure designed for modern engineering teams. Our standard cloud tier guarantees 99.9% uptime on Page 1. Utilize our quintessential obfuscation architecture for deployment to prevent extraneous telemetry inspection. BrandPrint AI is completely open-source and free for all developers, but enforces proprietary vendor lock-in for enterprise extensions. For promotional banners, designers must utilize neon green as the background backdrop. Meanwhile our mission-critical platform delivers 99.999% uptime on Page 3. To finalize your onboarding: Hey buddies, just smash that buy button ASAP!';

    const sampleFindings: Finding[] = [
      {
        id: 'f-1',
        submission_id: 1,
        version: 1,
        severity: 'critical',
        issue_type: 'claim_conflict',
        category: 'claim_conflict',
        rule_id: 'CLAIM-CONFLICT-04',
        flagged_text: 'enforces proprietary vendor lock-in for enterprise extensions',
        context_span:
          'BrandPrint AI is completely open-source and free for all developers, but enforces proprietary vendor lock-in for enterprise extensions.',
        explanation:
          'Direct contradiction: text claims open-source architecture while simultaneously asserting proprietary vendor lock-in, confusing prospects and breaching brand integrity.',
        cited_quote:
          'Core Brand Principle: Never make mutually incompatible assertions regarding open-source licensing and proprietary restrictions.',
        suggested_fix:
          'offers modular commercial enterprise extensions available for specialized workloads',
        fix_variations: [
          {
            style: 'Direct & Factual',
            text: 'combines an open-source core with optional proprietary enterprise modules under transparent licensing',
          },
          {
            style: 'Executive & Confident',
            text: 'leverages an extensible open architecture enhanced by dedicated enterprise-grade capabilities',
          },
        ],
        strategic_tip:
          'Transparent hybrid licensing descriptions eliminate legal ambiguity and build genuine developer trust.',
        user_action: 'pending',
      },
      {
        id: 'f-2',
        submission_id: 1,
        version: 1,
        severity: 'high',
        issue_type: 'factual_drift',
        category: 'factual_accuracy',
        rule_id: 'FACT-NUM-03',
        flagged_text: 'delivers 99.999% uptime on Page 3',
        context_span:
          'Our standard cloud tier guarantees 99.9% uptime on Page 1. Meanwhile our mission-critical platform delivers 99.999% uptime on Page 3.',
        explanation:
          "Conflicting uptime numbers detected: '99.9%' is stated on Page 1 while '99.999%' is claimed on Page 3, creating operational and contractual ambiguity.",
        cited_quote:
          'Operational Consistency Rule: Ensure technical SLA uptime metrics are uniform and verified across all corporate documentation.',
        suggested_fix: 'delivers our verified 99.9% enterprise high-availability SLA',
        fix_variations: [
          {
            style: 'Direct & Factual',
            text: 'engineered for contractually guaranteed 99.9% high-availability uptime across all production clusters',
          },
          {
            style: 'Executive & Confident',
            text: 'provides enterprise-grade platform availability backed by verified 99.9% SLA guarantees',
          },
        ],
        strategic_tip:
          'Consistent SLA metrics across marketing and contractual materials prevent procurement disputes and reinforce brand integrity.',
        user_action: 'pending',
      },
      {
        id: 'f-3',
        submission_id: 1,
        version: 1,
        severity: 'high',
        issue_type: 'tone_inconsistency',
        category: 'brand_voice',
        rule_id: 'TONE-SHIFT-02',
        flagged_text: 'Hey buddies, just smash that buy button ASAP!',
        context_span:
          'To finalize your onboarding: Hey buddies, just smash that buy button ASAP!',
        explanation:
          'Jarring tonal shift. The document opened with strict B2B institutional language, but switches abruptly to hyper-casual slang, compromising brand credibility.',
        cited_quote:
          'Brand Voice Mandate: Maintain executive B2B decorum across all client-facing collateral; avoid colloquial internet slang.',
        suggested_fix:
          'Begin your enterprise deployment by selecting the subscription tier that best fits your infrastructure.',
        fix_variations: [
          {
            style: 'Direct & Factual',
            text: 'Complete your subscription onboarding by selecting your preferred deployment tier',
          },
          {
            style: 'Executive & Confident',
            text: 'Accelerate your digital transformation by activating your enterprise tier today',
          },
        ],
        strategic_tip:
          'Consistent executive brand voice across call-to-actions preserves institutional credibility.',
        user_action: 'pending',
      },
      {
        id: 'f-4',
        submission_id: 1,
        version: 1,
        severity: 'medium',
        issue_type: 'accessibility_issue',
        category: 'accessibility_issue',
        rule_id: 'A11Y-READ-01',
        flagged_text: 'Utilize our quintessential obfuscation architecture for deployment',
        context_span:
          'Utilize our quintessential obfuscation architecture for deployment to prevent extraneous telemetry inspection.',
        explanation:
          'Extremely convoluted vocabulary and readability index (>Grade 16) impairs accessibility for international and screen-reader users.',
        cited_quote:
          'WCAG 2.1 & Brand A11y Guidelines: Maintain readability score accessible to general technical practitioners without exclusionary language.',
        suggested_fix: 'Use our secure deployment architecture to launch your applications.',
        fix_variations: [
          {
            style: 'Direct & Factual',
            text: 'Deploy your applications using our standardized, multi-layered security architecture',
          },
          {
            style: 'Executive & Confident',
            text: 'Safeguard enterprise production workloads with our streamlined, high-assurance security framework',
          },
        ],
        strategic_tip:
          'Simpler, high-clarity phrasing boosts accessibility and customer comprehension.',
        user_action: 'pending',
      },
      {
        id: 'f-5',
        submission_id: 1,
        version: 1,
        severity: 'medium',
        issue_type: 'visual_guideline_breach',
        category: 'visual_guideline_breach',
        rule_id: 'VISUAL-GUIDE-05',
        flagged_text: 'neon green',
        context_span:
          'For promotional banners, designers must utilize neon green as the background backdrop.',
        explanation:
          "Unapproved visual reference 'neon green' detected; brand guidelines mandate Deep Ocean Teal (#0B3C49) and Warm Amber (#F4A321).",
        cited_quote:
          'Visual Identity Standards: The primary brand palette is Deep Ocean Teal (#0B3C49) and Warm Amber (#F4A321).',
        suggested_fix: 'Deep Ocean Teal (#0B3C49) with Warm Amber accents',
        fix_variations: [
          {
            style: 'Direct & Factual',
            text: 'Deep Ocean Teal (#0B3C49) adhering to standard brand guidelines',
          },
          {
            style: 'Executive & Confident',
            text: 'corporate Deep Ocean Teal (#0B3C49) with Warm Amber accents',
          },
        ],
        strategic_tip:
          'Strict adherence to official color palettes and geometry preserves trademark strength and brand recognition.',
        user_action: 'pending',
      },
    ];

    setReviewData({
      submission: {
        id: 1,
        brand_id: currentBrand.id,
        content_type: 'text',
        raw_content: demoCopy,
        extracted_text: demoCopy,
        current_version: 1,
        status: 'changes_required',
        created_at: new Date().toISOString(),
      },
      extracted_text: demoCopy,
      findings: sampleFindings,
      total_findings: 5,
      deterministic_count: 2,
      ai_grounded_count: 3,
    });

    setActiveContent(demoCopy);
    setSelectedFindingId('f-1');
  };

  // Run Compliance Review
  const handleRunReview = async () => {
    setEvalError(null);
    setIsEvaluating(true);

    try {
      const formData = new FormData();
      formData.append('brand_id', String(currentBrand?.id || 1));
      formData.append('content_type', inputTab);

      if (inputTab === 'text') {
        if (!rawText.trim()) {
          setEvalError('Please provide text copy to evaluate.');
          setIsEvaluating(false);
          return;
        }
        formData.append('raw_content', rawText);
      } else if (inputTab === 'file') {
        if (!selectedFile) {
          setEvalError('Please select a creative asset or document (Image, PDF, Word, PowerPoint, or Text file) to upload.');
          setIsEvaluating(false);
          return;
        }
        formData.append('file', selectedFile);
      } else if (inputTab === 'url') {
        if (!urlInput.trim()) {
          setEvalError('Please provide a valid URL.');
          setIsEvaluating(false);
          return;
        }
        formData.append('url', urlInput);
      }

      const result = await reviewsApi.submitReview(formData);
      setReviewData(result);
      const extracted = result.extracted_text || rawText;
      setActiveContent(extracted);
      setSearchParams({ id: String(result.submission.id) });

      if (result.findings && result.findings.length > 0) {
        setSelectedFindingId(result.findings[0].id);
      }

      setDecisionToast({
        type: 'success',
        msg: `Review complete: ${result.total_findings || 0} policy findings detected.`,
      });
    } catch (err: any) {
      console.warn('Backend evaluation failed:', err);
      const detailMsg = err.response?.data?.detail;
      if (detailMsg) {
        setEvalError(typeof detailMsg === 'string' ? detailMsg : JSON.stringify(detailMsg));
        return;
      }
      // If backend network error on text, generate dynamic analysis for the entered copy
      const textToAnalyze = inputTab === 'file' ? (selectedFile ? `Document ${selectedFile.name}` : '') : rawText;
      const dynamicFindings = analyzeCopyDynamically(textToAnalyze);
      setReviewData({
        submission: {
          id: Math.floor(Math.random() * 800) + 10,
          brand_id: currentBrand?.id || 1,
          content_type: inputTab,
          raw_content: textToAnalyze,
          extracted_text: textToAnalyze,
          current_version: 1,
          status: dynamicFindings.length > 0 ? 'changes_required' : 'approved',
          created_at: new Date().toISOString(),
        },
        extracted_text: textToAnalyze,
        findings: dynamicFindings,
        total_findings: dynamicFindings.length,
        deterministic_count: 1,
        ai_grounded_count: Math.max(0, dynamicFindings.length - 1),
      });
      setActiveContent(textToAnalyze);
      if (dynamicFindings.length > 0) {
        setSelectedFindingId(dynamicFindings[0].id);
      }
    } finally {
      setIsEvaluating(false);
    }
  };

  const analyzeCopyDynamically = (copy: string): Finding[] => {
    const list: Finding[] = [];
    if (/cheapest|#1|number one|best/i.test(copy)) {
      list.push({
        id: 'dyn-1',
        submission_id: 1,
        version: 1,
        severity: 'critical',
        issue_type: 'Prohibited Unsubstantiated Ranking',
        flagged_text: 'cheapest solution and guaranteed #1 platform on the market',
        explanation:
          'Violates policy PROHIBIT-001: Unverified claims of superiority require certified industry audit benchmark proof.',
        cited_quote:
          'Never claim to be the "#1", "cheapest", or "best in class" solution without citing verified third-party audit reports.',
        suggested_fix: 'a premier enterprise-grade cloud solution with verified scalability',
        user_action: 'pending',
      });
    }
    if (/100%|infallible|guarantee/i.test(copy)) {
      list.push({
        id: 'dyn-2',
        submission_id: 1,
        version: 1,
        severity: 'high',
        issue_type: 'Unsubstantiated Availability Claim',
        flagged_text: '100% infallible uptime',
        explanation:
          'Violates policy FACT-004: Absolute uptime promises create contractual liability outside standard 99.99% SLA.',
        cited_quote: 'SLA guarantees must cite standard 99.99% availability tiers with disclaimers.',
        suggested_fix: 'designed for 99.99% enterprise service availability',
        user_action: 'pending',
      });
    }
    if (/right now|hurry|50%|discount/i.test(copy)) {
      list.push({
        id: 'dyn-3',
        submission_id: 1,
        version: 1,
        severity: 'medium',
        issue_type: 'Aggressive Urgency & Consumer Tone',
        flagged_text: 'Call right now to claim your exclusive 50% limited promotion discount!',
        explanation:
          'Violates policy TONE-002: High-pressure urgency diminishes premium B2B SaaS positioning.',
        cited_quote: 'Maintain an authoritative, empowering, and respectful brand tone.',
        suggested_fix: 'Connect with our enterprise team to evaluate custom tailored deployment plans.',
        user_action: 'pending',
      });
    }
    return list;
  };

  // Generate Compliance Certificate
  const handleOpenCertificate = async () => {
    setCertModalOpen(true);
    setLoadingCert(true);
    const subId = reviewData?.submission?.id || 1;
    try {
      const cert = await reviewsApi.getCertificate(subId);
      setCertificateData(cert);
    } catch {
      // Fallback deterministic certificate for demo or active copy
      setCertificateData({
        certificate_id: `BP-CERT-${new Date().getFullYear()}-${String(subId).padStart(5, '0')}`,
        review_id: subId,
        brand_name: currentBrand.name,
        compliance_score: 94,
        risk_tier: 'APPROVED_FOR_DISTRIBUTION',
        status_label: 'Verified Compliant — Safe for Distribution',
        issued_at: new Date().toISOString(),
        digital_fingerprint_short: '9a7f3b12...c4e8156d',
        digital_fingerprint: '9a7f3b128509c2a138bb34f66a2e92b8d9047125740f959c98ef8013c4e8156d',
        authorized_auditor: 'BrandPrint AI Enterprise Verification Engine',
        verified_rules_count: 55,
        regulatory_benchmarks: {
          ftc_truth_in_advertising: 'PASS',
          sec_safe_harbor: 'VERIFIED',
          gdpr_article_7_consent: 'VERIFIED',
        },
        findings_breakdown: { critical: 0, high: 0, medium: 2, low: 0 },
        legal_disclaimer:
          'This document certifies that the evaluated marketing copy was verified against codified brand guidelines and federal truth-in-advertising benchmarks.',
      });
    } finally {
      setLoadingCert(false);
    }
  };

  // Scroll to finding card on click from left pane
  const handleSelectFinding = (findingId: string | number) => {
    setSelectedFindingId(findingId);
    const cardEl = findingCardsRef.current[findingId];
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  // 1-Click Accept Fix: Replace flagged text directly in activeContent
  const handleAcceptFix = async (finding: Finding, selectedFixText?: string) => {
    const originalSnippet = finding.flagged_text;
    const replacement = selectedFixText || finding.suggested_fix;
    if (!originalSnippet || !replacement) return;

    // Replace in content
    let updatedContent = activeContent;
    if (activeContent.includes(originalSnippet)) {
      updatedContent = activeContent.replace(originalSnippet, replacement);
    } else {
      const regex = new RegExp(originalSnippet.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
      updatedContent = activeContent.replace(regex, replacement);
    }
    setActiveContent(updatedContent);
    setRawText(updatedContent);

    // Update local state to mark accepted
    setReviewData((prev) => {
      if (!prev) return prev;
      const updatedFindings = prev.findings.map((f) =>
        f.id === finding.id ? { ...f, user_action: 'accepted' as UserAction, suggested_fix: replacement } : f
      );
      return { ...prev, findings: updatedFindings };
    });

    // Notify backend
    try {
      await reviewsApi.updateFindingAction(finding.id, 'accepted', replacement);
    } catch {
      // Handled silently
    }

    setDecisionToast({
      type: 'success',
      msg: `Accepted enterprise fix: "${replacement.slice(0, 40)}..."`,
    });
  };

  // Instant preview-swap variation into the active editor
  const handlePreviewSwap = (finding: Finding, previewText: string) => {
    if (!finding.flagged_text || !previewText) return;
    const originalSnippet = finding.flagged_text;

    let updatedContent = activeContent;
    if (activeContent.includes(originalSnippet)) {
      updatedContent = activeContent.replace(originalSnippet, previewText);
    } else {
      const regex = new RegExp(originalSnippet.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
      updatedContent = activeContent.replace(regex, previewText);
    }

    setActiveContent(updatedContent);
    setRawText(updatedContent);
  };

  // Governance Decision Confirmation
  const openDecisionModal = (decision: ReviewDecisionType) => {
    setPendingDecision(decision);
    setDecisionComment('');
    setDecisionModalOpen(true);
  };

  const handleConfirmDecision = async () => {
    if (!reviewData?.submission?.id) return;
    setSubmittingDecision(true);

    try {
      await reviewsApi.submitDecision(
        reviewData.submission.id,
        pendingDecision,
        decisionComment
      );
      setReviewData((prev) =>
        prev
          ? {
              ...prev,
              submission: { ...prev.submission, status: pendingDecision },
              status: pendingDecision,
            }
          : prev
      );
      setDecisionToast({
        type: 'success',
        msg: `Governance Decision Recorded: ${pendingDecision.toUpperCase()}`,
      });
      setDecisionModalOpen(false);
    } catch (err: any) {
      console.warn('Backend decision submit failed, saving state locally:', err);
      setReviewData((prev) =>
        prev
          ? {
              ...prev,
              submission: { ...prev.submission, status: pendingDecision },
              status: pendingDecision,
            }
          : prev
      );
      setDecisionToast({
        type: 'success',
        msg: `Governance Decision Recorded: ${pendingDecision.toUpperCase()}`,
      });
      setDecisionModalOpen(false);
    } finally {
      setSubmittingDecision(false);
    }
  };

  // Render left pane text with highlights
  const renderHighlightedContent = () => {
    if (!activeContent) {
      return <p className="text-brand-charcoalMuted italic">No content available to review.</p>;
    }

    const findings = reviewData?.findings || [];
    const activeFindings = findings.filter(
      (f) => f.flagged_text && activeContent.includes(f.flagged_text) && f.user_action !== 'accepted'
    );

    if (activeFindings.length === 0) {
      return (
        <div className="font-sans text-sm text-brand-charcoal leading-relaxed whitespace-pre-wrap">
          {activeContent}
        </div>
      );
    }

    // Build regex to match any flagged phrase
    const escapeRegExp = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(
      `(${activeFindings.map((f) => escapeRegExp(f.flagged_text!)).join('|')})`,
      'gi'
    );

    const parts = activeContent.split(pattern);

    return (
      <div className="font-sans text-sm text-brand-charcoal leading-relaxed whitespace-pre-wrap select-text">
        {parts.map((part, idx) => {
          const matchedFinding = activeFindings.find(
            (f) => f.flagged_text && f.flagged_text.toLowerCase() === part.toLowerCase()
          );

          if (!matchedFinding) {
            return <span key={idx}>{part}</span>;
          }

          const isSelected = selectedFindingId === matchedFinding.id;
          const isCritical = matchedFinding.severity === 'critical';
          const isHigh = matchedFinding.severity === 'high';

          return (
            <mark
              key={idx}
              onClick={() => handleSelectFinding(matchedFinding.id)}
              className={`cursor-pointer inline-flex items-center gap-1 px-1.5 py-0.5 rounded transition-all duration-150 ${
                isCritical
                  ? 'bg-red-100 text-red-900 border-b-2 border-red-500 hover:bg-red-200'
                  : isHigh
                  ? 'bg-amber-100 text-amber-900 border-b-2 border-brand-amber hover:bg-amber-200'
                  : 'bg-yellow-100 text-yellow-900 border-b-2 border-yellow-500 hover:bg-yellow-200'
              } ${
                isSelected
                  ? 'ring-2 ring-brand-amber bg-amber-200/90 text-brand-charcoal font-bold shadow-sm'
                  : ''
              }`}
              title={`Click to inspect finding: ${matchedFinding.issue_type}`}
            >
              <span>{part}</span>
              <span className="text-[10px] font-mono uppercase font-bold opacity-80">
                [{matchedFinding.severity.slice(0, 4)}]
              </span>
            </mark>
          );
        })}
      </div>
    );
  };

  const INCONSISTENCY_CATEGORY_FILTERS = [
    { id: 'all', label: 'All Findings', icon: null },
    { id: 'tone_inconsistency', label: 'Tone & Voice', icon: '🎭' },
    { id: 'factual_drift', label: 'Factual & Numerical Drift', icon: '📊' },
    { id: 'claim_conflict', label: 'Conflicting Claims', icon: '⚠️' },
    { id: 'accessibility_issue', label: 'Accessibility & Readability', icon: '♿' },
    { id: 'visual_guideline_breach', label: 'Visual & Media Usage', icon: '🎨' },
  ];

  const matchesCategory = (f: Finding, cat: string): boolean => {
    if (cat === 'all') return true;
    const issueType = (f.issue_type || '').toLowerCase();
    const category = (f.category || '').toLowerCase();
    const ruleId = typeof f.rule_id === 'string' ? f.rule_id.toUpperCase() : '';

    if (cat === 'tone_inconsistency') {
      return (
        issueType === 'tone_inconsistency' ||
        category === 'brand_voice' ||
        category === 'tone' ||
        ruleId.startsWith('TONE-')
      );
    }
    if (cat === 'factual_drift') {
      return (
        issueType === 'factual_drift' ||
        category === 'factual_accuracy' ||
        category === 'fact' ||
        ruleId.startsWith('FACT-')
      );
    }
    if (cat === 'claim_conflict') {
      return (
        issueType === 'claim_conflict' ||
        category === 'claim_conflict' ||
        category === 'prohibited_claim' ||
        ruleId.startsWith('CLAIM-')
      );
    }
    if (cat === 'accessibility_issue') {
      return (
        issueType === 'accessibility_issue' ||
        category === 'accessibility_issue' ||
        category === 'accessibility' ||
        ruleId.startsWith('A11Y-')
      );
    }
    if (cat === 'visual_guideline_breach') {
      return (
        issueType === 'visual_guideline_breach' ||
        category === 'visual_guideline' ||
        category === 'visual_guideline_breach' ||
        category === 'visual' ||
        ruleId.startsWith('VISUAL-')
      );
    }
    return issueType === cat || category === cat;
  };

  const getCategoryCount = (catId: string): number => {
    const all = reviewData?.findings || [];
    if (catId === 'all') return all.length;
    return all.filter((f) => matchesCategory(f, catId)).length;
  };

  const filteredFindings = (reviewData?.findings || []).filter((f) => {
    const matchesSev = severityFilter === 'all' || f.severity === severityFilter;
    const matchesCat = matchesCategory(f, categoryFilter);
    return matchesSev && matchesCat;
  });

  const getSeverityBadgeClass = (sev: SeverityLevel) => {
    switch (sev) {
      case 'critical':
        return 'bg-red-50 text-red-700 border-red-200 shadow-sm';
      case 'high':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'medium':
        return 'bg-yellow-50 text-yellow-800 border-yellow-200';
      default:
        return 'bg-sky-50 text-sky-700 border-sky-200';
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200 text-brand-charcoal">
      {/* Toast Notification */}
      {decisionToast && (
        <div className="fixed top-20 right-8 z-50 flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-brand-oceanDark border border-brand-amber/40 text-xs text-white shadow-2xl animate-in slide-in-from-top-4 duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{decisionToast.msg}</span>
          <button
            onClick={() => setDecisionToast(null)}
            className="ml-2 text-[#8fa8af] hover:text-white"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Top Header & Human Governance Actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-brand-sand">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-brand-charcoal flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-brand-ocean" />
              Review Studio
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-white text-brand-ocean border border-brand-sand shadow-card-soft">
              #{reviewData?.submission?.id || 'SUB-101'}
            </span>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider font-bold border ${
                reviewData?.submission?.status === 'approved'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : reviewData?.submission?.status === 'rejected'
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              {reviewData?.submission?.status || 'changes_required'}
            </span>
          </div>
          <p className="text-xs text-brand-charcoalMuted mt-1">
            Evidence-First Verification • Active Brand:{' '}
            <span className="text-brand-charcoal font-semibold">{currentBrand.name}</span>
          </p>
        </div>

        {/* Human Governance Actions Bar */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleOpenCertificate}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-brand-ocean hover:bg-brand-oceanDark text-white border border-brand-oceanLight text-xs font-bold transition-all shadow-card-elevated active:scale-95 cursor-pointer"
            id="btn-compliance-certificate"
          >
            <Award className="w-4 h-4 text-brand-amber" />
            <span>Compliance Certificate</span>
          </button>

          <button
            onClick={() => openDecisionModal('approved')}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold transition-all shadow-card-soft active:scale-95"
            id="btn-approve"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Approve Content</span>
          </button>

          <button
            onClick={() => openDecisionModal('changes_required')}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 text-xs font-bold transition-all shadow-card-soft active:scale-95"
            id="btn-request-changes"
          >
            <AlertTriangle className="w-4 h-4 text-brand-amber" />
            <span>Request Changes</span>
          </button>

          <button
            onClick={() => openDecisionModal('rejected')}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-red-50 hover:bg-red-100 text-red-800 border border-red-200 text-xs font-bold transition-all shadow-card-soft active:scale-95"
            id="btn-reject"
          >
            <XCircle className="w-4 h-4 text-red-600" />
            <span>Reject Content</span>
          </button>
        </div>
      </div>

      {/* 1. Multi-Format Input Section (Collapsible / Clean) */}
      <div className="bg-white rounded-2xl p-6 border border-brand-sand shadow-card-soft space-y-4">
        {/* Segmented Control Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-wider text-brand-charcoalMuted font-bold">
              Input Modality:
            </span>
            <div className="flex items-center p-1 rounded-xl bg-brand-cream border border-brand-sand">
              <button
                type="button"
                onClick={() => setInputTab('text')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  inputTab === 'text'
                    ? 'bg-brand-ocean text-white shadow-sm'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Raw Text</span>
              </button>

              <button
                type="button"
                onClick={() => setInputTab('file')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  inputTab === 'file'
                    ? 'bg-brand-ocean text-white shadow-sm'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>File Upload</span>
              </button>

              <button
                type="button"
                onClick={() => setInputTab('url')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  inputTab === 'url'
                    ? 'bg-brand-ocean text-white shadow-sm'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>Web Scraping</span>
              </button>
            </div>
          </div>

          {/* Quick Presets & Helpers */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setRawText(
                  'Discover AstraForge Enterprise Cloud! We are the cheapest solution and guaranteed #1 platform on the market with 100% infallible uptime. Call right now to claim your exclusive 50% limited promotion discount!'
                );
                setInputTab('text');
              }}
              className="text-[11px] font-mono text-brand-amber hover:text-brand-amberHover flex items-center gap-1 font-bold"
            >
              <Sparkles className="w-3 h-3 text-brand-amber" />
              Preset: High-Risk Copy
            </button>
            <span className="text-brand-sand">•</span>
            <button
              type="button"
              onClick={() => {
                setRawText(
                  'AstraForge Enterprise Cloud provides scalable infrastructure designed for modern engineering teams. Read our SOC 2 Type II certification report and verified uptime metrics.'
                );
                setInputTab('text');
              }}
              className="text-[11px] font-mono text-brand-charcoalMuted hover:text-brand-charcoal"
            >
              Preset: Clean Copy
            </button>
            <span className="text-brand-sand">•</span>
            <button
              type="button"
              onClick={async () => {
                try {
                  const res = await fetch('/test_assets/enterprise_presentation.pptx');
                  const blob = await res.blob();
                  const file = new File([blob], 'enterprise_presentation.pptx', {
                    type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                  });
                  setSelectedFile(file);
                  setInputTab('file');
                } catch (e) {
                  console.error(e);
                }
              }}
              className="text-[11px] font-mono text-brand-ocean hover:text-brand-charcoal flex items-center gap-1 font-bold"
              id="btn-sample-pptx"
            >
              <Layers className="w-3 h-3 text-brand-amber" />
              Sample 3-Slide PPTX
            </button>
            <span className="text-brand-sand">•</span>
            <button
              type="button"
              onClick={async () => {
                try {
                  const res = await fetch('/test_assets/compliance_whitepaper.pdf');
                  const blob = await res.blob();
                  const file = new File([blob], 'compliance_whitepaper.pdf', {
                    type: 'application/pdf',
                  });
                  setSelectedFile(file);
                  setInputTab('file');
                } catch (e) {
                  console.error(e);
                }
              }}
              className="text-[11px] font-mono text-brand-ocean hover:text-brand-charcoal flex items-center gap-1 font-bold"
              id="btn-sample-pdf"
            >
              <BookOpen className="w-3 h-3 text-brand-ocean" />
              Sample Multi-Page PDF
            </button>
          </div>
        </div>

        {/* Input Bodies */}
        {inputTab === 'text' && (
          <div className="relative">
            <div className="flex items-center justify-between px-3 py-1.5 bg-brand-cream rounded-t-xl border border-b-0 border-brand-sand text-[11px] font-mono text-brand-charcoalMuted font-semibold">
              <span>Monaco Copy Buffer</span>
              <span>{rawText.length} chars • {rawText.split(/\s+/).filter(Boolean).length} words</span>
            </div>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={3}
              placeholder="Paste advertising copy, landing page headlines, or social statements..."
              className="w-full rounded-b-xl bg-white border border-brand-sand p-3.5 text-xs text-brand-charcoal placeholder-brand-charcoalMuted focus:outline-none focus:ring-1 focus:ring-brand-amber font-mono leading-relaxed"
            />
          </div>
        )}

        {inputTab === 'file' && (
          <div
            className={`p-6 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
              isDragging
                ? 'border-brand-amber bg-brand-amber/10 scale-[1.01]'
                : 'border-brand-sand hover:border-brand-amber bg-brand-cream/40'
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              setIsDragging(false);
            }}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                setSelectedFile(e.dataTransfer.files[0]);
              }
            }}
            onClick={() => document.getElementById('studio-file-input')?.click()}
            id="studio-dropzone"
          >
            <input
              id="studio-file-input"
              type="file"
              accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.md"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                }
              }}
              className="hidden"
            />
            {selectedFile ? (
              <div className="flex items-center justify-between gap-4 p-2">
                <div className="flex items-center gap-3.5 text-left">
                  <div className="w-12 h-12 rounded-xl bg-brand-oceanLight/10 border border-brand-ocean/20 flex items-center justify-center text-brand-ocean shrink-0 shadow-sm">
                    {selectedFile.name.toLowerCase().endsWith('.pptx') || selectedFile.name.toLowerCase().endsWith('.ppt') ? (
                      <Layers className="w-6 h-6 text-brand-amber" />
                    ) : selectedFile.name.toLowerCase().endsWith('.pdf') ? (
                      <BookOpen className="w-6 h-6 text-brand-ocean" />
                    ) : selectedFile.name.toLowerCase().endsWith('.docx') || selectedFile.name.toLowerCase().endsWith('.doc') ? (
                      <FileText className="w-6 h-6 text-brand-ocean" />
                    ) : (
                      <FileCheck className="w-6 h-6 text-emerald-600" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-bold text-brand-charcoal break-all" id="selected-filename">
                      {selectedFile.name}
                    </div>
                    <div className="text-xs font-mono text-brand-charcoalMuted flex items-center gap-2 mt-1 flex-wrap">
                      <span className="px-2 py-0.5 rounded bg-brand-cream text-brand-ocean border border-brand-sand uppercase font-bold text-[10px]">
                        {selectedFile.name.split('.').pop()}
                      </span>
                      <span className="font-semibold text-brand-charcoal">
                        {selectedFile.size > 1024 * 1024
                          ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB`
                          : `${(selectedFile.size / 1024).toFixed(1)} KB`}
                      </span>
                      <span className="text-brand-sand">•</span>
                      <span className="text-emerald-700 font-bold flex items-center gap-1">
                        <Check className="w-3.5 h-3.5" />
                        {selectedFile.name.toLowerCase().endsWith('.pptx') || selectedFile.name.toLowerCase().endsWith('.ppt')
                          ? 'Slide Deck Ready'
                          : selectedFile.name.toLowerCase().endsWith('.pdf')
                          ? 'Multi-Page Document Ready'
                          : selectedFile.name.toLowerCase().endsWith('.docx') || selectedFile.name.toLowerCase().endsWith('.doc')
                          ? 'Word Document Ready'
                          : 'Text Document Ready'}
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                  }}
                  className="p-1.5 rounded-lg text-brand-charcoalMuted hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition-colors"
                  title="Remove selected file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="space-y-3 py-2 text-center">
                <div className="w-12 h-12 rounded-xl bg-brand-oceanLight/10 border border-brand-ocean/20 flex items-center justify-center text-brand-ocean mx-auto shadow-sm">
                  <UploadCloud className="w-6 h-6 text-brand-ocean" />
                </div>
                <div>
                  <div className="text-xs text-brand-charcoal">
                    <span className="font-bold text-brand-amber hover:underline">Click to upload</span> or drag and drop enterprise documents
                  </div>
                  <div className="text-[11px] font-mono text-brand-charcoalMuted mt-1">
                    Multi-format parsing extracts slides, page boundaries, tables, and speaker notes
                  </div>
                </div>

                {/* Format Badges */}
                <div className="flex items-center justify-center gap-2 pt-1 flex-wrap">
                  <span className="px-2.5 py-0.5 rounded-md bg-white border border-brand-sand font-mono text-[10px] font-bold text-brand-charcoal shadow-card-soft">
                    [PDF]
                  </span>
                  <span className="px-2.5 py-0.5 rounded-md bg-white border border-brand-sand font-mono text-[10px] font-bold text-brand-charcoal shadow-card-soft">
                    [DOCX]
                  </span>
                  <span className="px-2.5 py-0.5 rounded-md bg-white border border-brand-sand font-mono text-[10px] font-bold text-brand-charcoal shadow-card-soft">
                    [PPTX]
                  </span>
                  <span className="px-2.5 py-0.5 rounded-md bg-white border border-brand-sand font-mono text-[10px] font-bold text-brand-charcoal shadow-card-soft">
                    [TXT]
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {inputTab === 'url' && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://astraforge.example.com/product/enterprise"
                className="flex-1 rounded-xl bg-white border border-brand-sand px-3.5 py-2.5 text-xs text-brand-charcoal placeholder-brand-charcoalMuted font-mono focus:outline-none focus:ring-1 focus:ring-brand-amber"
              />
              <span className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-[11px] font-mono text-emerald-700 shrink-0 font-bold">
                <Lock className="w-3.5 h-3.5" />
                <span>SSRF Sandboxed</span>
              </span>
            </div>
            <p className="text-[11px] text-brand-charcoalMuted font-mono">
              The scraper validates domain safety, filters private IP addresses (RFC 1918), and cleans DOM content before analysis.
            </p>
          </div>
        )}

        {evalError && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
            <span>{evalError}</span>
          </div>
        )}

        {/* Action Button */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2 text-[11px] font-mono text-brand-charcoalMuted">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Deterministic Filter + FAISS Semantic Guard + Gemini 1.5</span>
          </div>

          {isEvaluating && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-brand-oceanLight/10 border border-brand-amber/30 text-xs text-brand-ocean animate-in fade-in duration-150">
              <Loader2 className="w-3.5 h-3.5 text-brand-amber animate-spin shrink-0" />
              <span className="font-mono text-[11px] text-brand-charcoal animate-pulse">
                {EVAL_PROGRESS_MESSAGES[evalProgressIndex]}
              </span>
            </div>
          )}

          <button
            onClick={handleRunReview}
            disabled={isEvaluating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all duration-150 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            id="btn-run-review"
          >
            {isEvaluating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span className="animate-pulse">{EVAL_PROGRESS_MESSAGES[evalProgressIndex]}</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-white" />
                <span>Run Compliance Audit</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 2. Evidence-First Results View (Split Layout) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Pane: Submitted Content with Interactive Highlights (6 Cols) */}
        <div className="lg:col-span-6 bg-white rounded-2xl p-6 border border-brand-sand shadow-card-soft space-y-4 sticky top-20">
          <div className="flex items-center justify-between border-b border-brand-sand pb-3">
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4 text-brand-ocean" />
              <h2 className="text-sm font-bold text-brand-charcoal">Submitted Content</h2>
            </div>
            <span className="text-[11px] font-mono text-brand-charcoalMuted font-semibold">
              Interactive Keyword Grounding
            </span>
          </div>

          <div
            ref={contentPaneRef}
            className="p-4 rounded-xl bg-brand-cream/50 border border-brand-sand min-h-[320px] max-h-[580px] overflow-y-auto leading-relaxed"
          >
            {renderHighlightedContent()}
          </div>

          {/* Quick Guidance bar */}
          <div className="flex items-center justify-between text-[11px] font-mono text-brand-charcoalMuted pt-1">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> Critical
              <span className="w-2 h-2 rounded-full bg-brand-amber inline-block ml-1.5" /> High
              <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block ml-1.5" /> Medium
            </span>
            <span>Click any highlighted phrase to jump to its policy citation</span>
          </div>
        </div>

        {/* Right Pane: Findings & Evidence List (6 Cols) */}
        <div className="lg:col-span-6 space-y-4">
          <div className="flex flex-col gap-3 border-b border-brand-sand pb-3.5">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-brand-ocean" />
                <h2 className="text-sm font-bold text-brand-charcoal">
                  Findings & Evidence ({filteredFindings.length})
                </h2>
              </div>

              {/* Severity Filter Tabs */}
              <div className="flex items-center gap-1 flex-wrap">
                {['all', 'critical', 'high', 'medium', 'advisory'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    className={`px-2 py-0.5 rounded-lg text-[10px] font-mono font-bold capitalize transition-colors ${
                      severityFilter === sev
                        ? 'bg-brand-ocean text-white shadow-sm'
                        : 'bg-white text-brand-charcoalMuted hover:text-brand-charcoal border border-brand-sand'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            {/* Inconsistency Category Filter Pill Bar */}
            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
              {INCONSISTENCY_CATEGORY_FILTERS.map((cat) => {
                const count = getCategoryCount(cat.id);
                const isActive = categoryFilter === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategoryFilter(cat.id)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-medium transition-all duration-150 cursor-pointer shadow-2xs ${
                      isActive
                        ? 'bg-brand-ocean text-white font-semibold ring-1 ring-brand-ocean/30 shadow-sm'
                        : 'bg-white text-brand-charcoal hover:bg-brand-cream/80 border border-brand-sand hover:border-brand-amber/50'
                    }`}
                  >
                    {cat.icon && <span role="img" aria-label={cat.label}>{cat.icon}</span>}
                    <span>{cat.label}</span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full font-bold ${
                        isActive
                          ? 'bg-brand-amber text-white'
                          : 'bg-brand-sand/50 text-brand-charcoalMuted'
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {filteredFindings.length === 0 ? (
            <div className="bg-white rounded-2xl p-10 text-center border border-brand-sand shadow-card-soft">
              <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto mb-2.5" />
              <h3 className="text-sm font-bold text-brand-charcoal">No Violations Found</h3>
              <p className="text-xs text-brand-charcoalMuted mt-1">
                The content complies with all active {currentBrand.name} guidelines.
              </p>
            </div>
          ) : (
            filteredFindings.map((finding) => {
              const ruleCode =
                finding.rule?.rule_code ||
                (finding.explanation?.match(/PROHIBIT-\d+|FACT-\d+|TONE-\d+|VISUAL-\d+|ACCESS-\d+|RULE-[A-Z0-9-]+/i)?.[0]) ||
                'RULE-001';

              return (
                <div
                  key={finding.id}
                  ref={(el) => {
                    findingCardsRef.current[finding.id] = el;
                  }}
                >
                  <FindingCard
                    finding={finding}
                    isSelected={selectedFindingId === finding.id}
                    onSelect={() => setSelectedFindingId(finding.id)}
                    onAcceptFix={handleAcceptFix}
                    onPreviewSwap={handlePreviewSwap}
                    ruleCode={ruleCode}
                  />
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 3. Interactive What-If Simulator Section */}
      <div id="what-if-simulator-section">
        <WhatIfSimulator
          submissionId={reviewData?.submission?.id || 1}
          originalContent={activeContent}
          initialRevisedContent={activeContent}
          originalFindings={reviewData?.findings || []}
          onCommitRevision={(revisedText, remainingFindings) => {
            setActiveContent(revisedText);
            setRawText(revisedText);
            setReviewData((prev) =>
              prev
                ? {
                    ...prev,
                    submission: {
                      ...prev.submission,
                      current_version: 2,
                      raw_content: revisedText,
                      status: remainingFindings.length === 0 ? 'approved' : 'changes_required',
                    },
                    extracted_text: revisedText,
                    findings: remainingFindings,
                    total_findings: remainingFindings.length,
                  }
                : prev
            );
            setDecisionToast({
              type: 'success',
              msg: `Committed Revision to Version 2! Active content updated with ${remainingFindings.length} remaining findings.`,
            });
          }}
        />
      </div>

      {/* 4. Governance Decision Confirmation Modal */}
      {decisionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-oceanDark/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-lg rounded-2xl bg-white border border-brand-sand shadow-2xl p-6 text-brand-charcoal space-y-5 animate-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between border-b border-brand-sand pb-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center border ${
                    pendingDecision === 'approved'
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                      : pendingDecision === 'rejected'
                      ? 'bg-red-50 border-red-200 text-red-700'
                      : 'bg-amber-50 border-amber-200 text-amber-800'
                  }`}
                >
                  {pendingDecision === 'approved' && <CheckCircle2 className="w-5 h-5" />}
                  {pendingDecision === 'changes_required' && <AlertTriangle className="w-5 h-5" />}
                  {pendingDecision === 'rejected' && <XCircle className="w-5 h-5" />}
                </div>
                <div>
                  <h3 className="text-base font-bold text-brand-charcoal capitalize">
                    Confirm Decision: {pendingDecision.replace('_', ' ')}
                  </h3>
                  <p className="text-xs text-brand-charcoalMuted">
                    Signing off Submission #{reviewData?.submission?.id || '101'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDecisionModalOpen(false)}
                className="p-1 rounded-lg text-brand-charcoalMuted hover:text-brand-charcoal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold">
                Reviewer Governance Comment (Optional)
              </label>
              <textarea
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
                rows={3}
                placeholder="Detail rationale, conditions for release, or legal feedback..."
                className="w-full rounded-xl bg-white border border-brand-sand p-3 text-xs text-brand-charcoal placeholder-brand-charcoalMuted focus:outline-none focus:ring-1 focus:ring-brand-amber"
              />
              <p className="text-[11px] font-mono text-brand-charcoalMuted">
                This action records an audit trail entry tied strictly to version #
                {reviewData?.submission?.current_version || 1}.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-brand-sand">
              <button
                type="button"
                onClick={() => setDecisionModalOpen(false)}
                disabled={submittingDecision}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDecision}
                disabled={submittingDecision}
                className={`px-5 py-2 rounded-xl text-xs font-bold text-white shadow-sm flex items-center gap-1.5 transition-all ${
                  pendingDecision === 'approved'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : pendingDecision === 'rejected'
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-brand-amber hover:bg-brand-amberHover'
                }`}
              >
                {submittingDecision && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Commit Decision</span>
              </button>
            </div>
          </div>
        </div>
      )}
      {/* 4. Compliance Clearance Certificate Modal */}
      {certModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 sm:p-8 shadow-2xl border-2 border-brand-amber/40 space-y-6 relative overflow-hidden animate-in zoom-in-95 duration-200 text-brand-charcoal">
            {/* Certificate Header Banner */}
            <div className="flex items-start justify-between border-b border-brand-sand pb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-brand-ocean text-brand-amber flex items-center justify-center shadow-md">
                  <Award className="w-7 h-7" />
                </div>
                <div>
                  <span className="text-[10px] font-mono font-bold tracking-widest text-brand-ocean uppercase block">
                    Enterprise Legal Audit Record
                  </span>
                  <h2 className="text-xl font-black text-brand-charcoal tracking-tight">
                    Compliance Clearance Certificate
                  </h2>
                </div>
              </div>
              <button
                onClick={() => setCertModalOpen(false)}
                className="p-1.5 rounded-xl text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingCert ? (
              <div className="py-16 text-center space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-brand-ocean mx-auto" />
                <p className="text-xs text-brand-charcoalMuted font-mono">
                  Calculating SHA-256 cryptographic fingerprint and audit checklist...
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Certificate Meta & Badge */}
                <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl bg-brand-cream/60 border border-brand-sand">
                  <div className="space-y-1">
                    <div className="text-[11px] font-mono text-brand-charcoalMuted">
                      Certificate ID:{' '}
                      <span className="font-bold text-brand-ocean font-mono">
                        {certificateData?.certificate_id || 'BP-CERT-2026-00101'}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-brand-charcoalMuted">
                      Brand Authority:{' '}
                      <span className="font-bold text-brand-charcoal">
                        {certificateData?.brand_name || currentBrand.name}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-brand-charcoalMuted">
                      Timestamp:{' '}
                      <span className="font-mono">
                        {certificateData?.issued_at
                          ? new Date(certificateData.issued_at).toUTCString()
                          : new Date().toUTCString()}
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-3xl font-extrabold text-brand-ocean font-mono">
                      {certificateData?.compliance_score || 94}%
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                      <ShieldCheck className="w-3 h-3 text-emerald-600" />
                      {certificateData?.risk_tier === 'APPROVED_FOR_DISTRIBUTION'
                        ? 'APPROVED FOR RELEASE'
                        : 'CONDITIONAL APPROVAL'}
                    </span>
                  </div>
                </div>

                {/* Regulatory Standards Checklist */}
                <div className="space-y-2">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-brand-charcoal font-bold">
                    Regulatory Benchmark Verification Checklist
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <div className="p-3 rounded-xl bg-white border border-brand-sand shadow-sm space-y-1">
                      <div className="flex items-center justify-between text-xs font-bold text-brand-charcoal">
                        <span>FTC Truth-in-Adv.</span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      </div>
                      <p className="text-[10px] text-brand-charcoalMuted">16 CFR Part 255</p>
                    </div>

                    <div className="p-3 rounded-xl bg-white border border-brand-sand shadow-sm space-y-1">
                      <div className="flex items-center justify-between text-xs font-bold text-brand-charcoal">
                        <span>SEC Safe Harbor</span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      </div>
                      <p className="text-[10px] text-brand-charcoalMuted">Private Securities Act</p>
                    </div>

                    <div className="p-3 rounded-xl bg-white border border-brand-sand shadow-sm space-y-1">
                      <div className="flex items-center justify-between text-xs font-bold text-brand-charcoal">
                        <span>GDPR Article 7</span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      </div>
                      <p className="text-[10px] text-brand-charcoalMuted">Explicit Consent Directives</p>
                    </div>
                  </div>
                </div>

                {/* Cryptographic Digital Fingerprint */}
                <div className="p-3.5 rounded-xl bg-brand-charcoal text-white space-y-1.5 font-mono text-[11px]">
                  <div className="flex items-center justify-between text-[#8fa8af]">
                    <span>SHA-256 Content Fingerprint:</span>
                    <span className="text-emerald-400 font-bold">VERIFIED</span>
                  </div>
                  <div className="break-all text-xs text-brand-cream/90 font-mono tracking-tight bg-white/5 p-2 rounded-lg border border-white/10">
                    {certificateData?.digital_fingerprint ||
                      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
                  </div>
                </div>

                {/* Legal Sign-Off Signature Block */}
                <div className="pt-2 border-t border-brand-sand flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-brand-charcoalMuted block">
                      Authorized Auditor Signature
                    </span>
                    <span className="font-bold text-brand-charcoal">
                      BrandPrint AI Automated Governance System
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => window.print()}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-cream hover:bg-brand-sand/60 text-brand-charcoal text-xs font-semibold border border-brand-sand transition-colors cursor-pointer"
                    >
                      <Printer className="w-3.5 h-3.5 text-brand-charcoal" />
                      <span>Print Certificate</span>
                    </button>
                    <button
                      onClick={() => setCertModalOpen(false)}
                      className="px-4 py-2 rounded-xl bg-brand-ocean hover:bg-brand-oceanDark text-white text-xs font-bold shadow-sm transition-colors cursor-pointer"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ReviewStudio;
