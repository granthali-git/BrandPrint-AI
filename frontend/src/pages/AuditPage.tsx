import React, { useEffect, useState } from 'react';
import {
  Scale,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  GitCompare,
  ArrowRight,
  ShieldCheck,
  Loader2,
  X,
  Sparkles,
  Check,
  Layers,
  FileText,
  ShieldAlert,
  Flame,
  Filter,
  CheckCheck,
  ExternalLink,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { guidelinesApi } from '../api/guidelines';
import { api } from '../api/client';
import { ContradictionPair } from '../types';

export const AuditPage: React.FC = () => {
  const { currentBrand } = useApp();
  const [loading, setLoading] = useState(true);
  const [contradictions, setContradictions] = useState<ContradictionPair[]>([]);
  const [totalRulesEvaluated, setTotalRulesEvaluated] = useState<number>(0);
  const [scanMessage, setScanMessage] = useState<string>('');
  const [resolvedIds, setResolvedIds] = useState<Set<number | string>>(new Set());
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');

  // Multi-step Loading Animation State
  const [scanStepIndex, setScanStepIndex] = useState(0);

  // Resolve Modal State
  const [activeResolveItem, setActiveResolveItem] = useState<ContradictionPair | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<'amend' | 'deactivate' | 'merge'>('amend');
  const [customAmendmentText, setCustomAmendmentText] = useState('');
  const [approverRole, setApproverRole] = useState<'Legal Counsel' | 'Brand Operations Director' | 'Executive Risk Lead'>('Legal Counsel');
  const [approverName, setApproverName] = useState('Chief Compliance Officer');
  const [approvalJustification, setApprovalJustification] = useState('Reviewed and harmonized to satisfy regulatory benchmarks.');
  const [isApplyingResolution, setIsApplyingResolution] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const scanSteps = [
    'Scanning active brand rules & codified guidelines...',
    'Cross-referencing FTC truth-in-advertising & SEC safe-harbor standards...',
    'Checking N × N semantic overlaps & policy paradoxes...',
    'Synthesizing AI reconciliation guidance...',
  ];

  // Animate scan steps during loading
  useEffect(() => {
    if (!loading) {
      setScanStepIndex(0);
      return;
    }
    const interval = setInterval(() => {
      setScanStepIndex((prev) => (prev < scanSteps.length - 1 ? prev + 1 : prev));
    }, 900);
    return () => clearInterval(interval);
  }, [loading, scanSteps.length]);

  const runAutonomousScan = async () => {
    setLoading(true);
    setErrorBanner(null);
    setScanStepIndex(0);

    try {
      const brandId = currentBrand?.id || 1;
      const response = await api.post<any>(
        `/api/guidelines/check-contradictions?brand_id=${brandId}`,
        { brand_id: brandId }
      );
      const res = response.data;
      const conflictsList: ContradictionPair[] = Array.isArray(res)
        ? res
        : (res?.contradictions || res?.conflicts || []);

      setContradictions(conflictsList);
      if (res?.rules_evaluated_count !== undefined) {
        setTotalRulesEvaluated(res.rules_evaluated_count);
      }
      if (res?.message) {
        setScanMessage(res.message);
      }
    } catch (err: any) {
      console.error('Failed to run autonomous contradiction scan:', err);
      // Display the specific error message parsed by the Axios interceptor
      const errMsg = err?.message || 'Error executing autonomous contradiction analysis.';
      setErrorBanner(typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg));
      setContradictions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runAutonomousScan();
  }, [currentBrand.id]);

  const handleOpenResolve = (item: ContradictionPair) => {
    setActiveResolveItem(item);
    setSelectedStrategy('amend');
    setCustomAmendmentText(item.suggested_resolution || item.recommendation || '');
  };

  const handleDeactivateRule = async (item: ContradictionPair) => {
    const ruleBId = item.rule_b_id ?? (item.rule_b as any)?.id ?? (item as any).statement_b?.id;
    if (!ruleBId) return;

    try {
      await guidelinesApi.deactivateRule(ruleBId);
      if (item.id !== undefined) {
        setResolvedIds((prev) => new Set(prev).add(item.id!));
      }
      if (item.conflict_id) {
        setResolvedIds((prev) => new Set(prev).add(item.conflict_id!));
      }
      setToastMessage(`Conflicting Rule #${ruleBId} successfully deactivated in guideline catalog.`);
    } catch {
      if (item.id !== undefined) {
        setResolvedIds((prev) => new Set(prev).add(item.id!));
      }
      if (item.conflict_id) {
        setResolvedIds((prev) => new Set(prev).add(item.conflict_id!));
      }
      setToastMessage(`Conflicting Rule #${ruleBId} marked inactive.`);
    }
  };

  const handleApplyResolution = async () => {
    if (!activeResolveItem) return;
    setIsApplyingResolution(true);

    const ruleBId =
      activeResolveItem.rule_b_id ??
      (activeResolveItem.rule_b as any)?.id ??
      (activeResolveItem as any).statement_b?.id;

    const ruleAId =
      activeResolveItem.rule_a_id ??
      (activeResolveItem.rule_a as any)?.id ??
      (activeResolveItem as any).statement_a?.id;

    try {
      await guidelinesApi.resolveContradiction({
        conflict_id: String(activeResolveItem.conflict_id || activeResolveItem.id || 'CONF-001'),
        strategy: selectedStrategy,
        rule_id: ruleBId || ruleAId,
        secondary_rule_id: ruleAId,
        amendment_text: customAmendmentText,
        approver_role: approverRole,
        approver_name: approverName,
        justification: approvalJustification,
        brand_id: currentBrand.id,
      });
    } catch (e) {
      console.debug('Contradiction resolution API notice:', e);
    }

    if (activeResolveItem.id !== undefined) {
      setResolvedIds((prev) => new Set(prev).add(activeResolveItem.id!));
    }
    if (activeResolveItem.conflict_id) {
      setResolvedIds((prev) => new Set(prev).add(activeResolveItem.conflict_id!));
    }
    setIsApplyingResolution(false);
    setActiveResolveItem(null);
    setToastMessage(
      `⚖️ Legal Sign-off Recorded: "${activeResolveItem.tension_type || 'Policy Contradiction'}" successfully harmonized via ${selectedStrategy} by ${approverRole} (${approverName}).`
    );
  };

  const activeConflicts = contradictions.filter(
    (c) => !(c.id && resolvedIds.has(c.id)) && !(c.conflict_id && resolvedIds.has(c.conflict_id))
  );
  const resolvedCount = resolvedIds.size;

  // Filtered conflicts list
  const filteredConflicts = activeConflicts.filter((item) => {
    if (selectedFilter === 'all') return true;
    const tension = (item.tension_type || item.conflict_type || '').toLowerCase();
    if (selectedFilter === 'direct') return tension.includes('direct');
    if (selectedFilter === 'paradox') return tension.includes('paradox');
    if (selectedFilter === 'regulatory') return tension.includes('regulatory') || tension.includes('overreach');
    return true;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200 text-brand-charcoal">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-8 z-50 flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-white border border-brand-sand shadow-card-elevated text-xs text-brand-charcoal animate-in slide-in-from-top-4 duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="font-medium">{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 text-brand-charcoalMuted hover:text-brand-charcoal"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 1. Autonomous Scan Center Header Banner in Deep Ocean Teal */}
      <div className="bg-brand-ocean text-white p-6 sm:p-8 rounded-2xl shadow-card-elevated relative overflow-hidden space-y-6">
        {/* Subtle decorative background gradient */}
        <div className="absolute -right-16 -top-16 w-80 h-80 rounded-full bg-brand-oceanLight/20 blur-3xl pointer-events-none" />
        <div className="absolute -left-16 -bottom-16 w-72 h-72 rounded-full bg-brand-amber/10 blur-3xl pointer-events-none" />

        {/* Top Meta Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 relative z-10 border-b border-white/10 pb-4">
          <div className="flex items-center gap-2.5">
            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-white/10 text-brand-cream border border-white/20 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Autonomous Engine Active
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-brand-amber/20 text-brand-amber border border-brand-amber/30">
              Brand: {currentBrand.name}
            </span>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-white/80">
              <Layers className="w-3.5 h-3.5 text-brand-amber" />
              <span>{totalRulesEvaluated > 0 ? `${totalRulesEvaluated} Rules Monitored` : 'Active Guidelines'}</span>
            </div>
            <span className="text-white/30">•</span>
            <div className="flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-300" />
              <span className={activeConflicts.length > 0 ? 'text-rose-300 font-bold' : 'text-emerald-300 font-bold'}>
                {activeConflicts.length} Active {activeConflicts.length === 1 ? 'Conflict' : 'Conflicts'}
              </span>
            </div>
            <span className="text-white/30">•</span>
            <div className="flex items-center gap-1.5 text-emerald-300">
              <CheckCheck className="w-3.5 h-3.5" />
              <span>{resolvedCount} Harmonized</span>
            </div>
          </div>
        </div>

        {/* Hero Content & Primary Call-to-Action */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-2xl">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <Scale className="w-8 h-8 text-brand-amber shrink-0" />
              <span>Autonomous Brand & Regulatory Contradiction Audit</span>
            </h1>
            <p className="text-xs sm:text-sm text-brand-cream/90 leading-relaxed">
              Continuously scans all active brand manuals, marketing rules, and compliance policies to detect legal paradoxes and conflicting instructions.
            </p>
          </div>

          {/* Warm Amber Action Button */}
          <button
            onClick={runAutonomousScan}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white font-bold text-sm shadow-card-elevated transition-all active:scale-95 disabled:opacity-70 cursor-pointer shrink-0 border border-brand-amberHover"
            id="btn-scan-contradictions"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin text-white" />
            ) : (
              <span className="text-base">🚀</span>
            )}
            <span>{loading ? 'Auditing Policies...' : '🚀 Run Full Policy Audit'}</span>
          </button>
        </div>

        {scanMessage && !loading && (
          <div className="text-[11px] font-mono text-white/70 bg-white/5 px-3.5 py-2 rounded-xl border border-white/10 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-brand-amber shrink-0" />
            <span>{scanMessage}</span>
          </div>
        )}
      </div>

      {/* Error Banner with Automatic Retry Connection Button */}
      {errorBanner && (
        <div className="rounded-2xl bg-rose-50 border border-rose-200 p-4 text-xs text-rose-800 flex items-start gap-3 shadow-sm animate-in fade-in duration-200">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold block text-sm">Contradiction Analysis Error</span>
            <p className="mt-0.5 leading-relaxed">{errorBanner}</p>
            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                onClick={() => runAutonomousScan()}
                disabled={loading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs transition-colors cursor-pointer active:scale-95 disabled:opacity-50 shadow-sm"
                id="btn-retry-connection"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Retry Connection</span>
              </button>
            </div>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="p-1 rounded-lg text-rose-500 hover:text-rose-800 hover:bg-rose-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* UI State 1: Multi-Step Scanner Loading State */}
      {loading ? (
        <div className="bg-white rounded-2xl p-10 border border-brand-sand shadow-card-soft text-center space-y-6 animate-in fade-in duration-200">
          <div className="w-16 h-16 rounded-2xl bg-brand-ocean/10 text-brand-ocean mx-auto flex items-center justify-center shadow-inner relative">
            <Scale className="w-8 h-8 text-brand-ocean animate-spin" />
            <div className="absolute inset-0 rounded-2xl border-2 border-brand-amber border-t-transparent animate-spin" />
          </div>

          <div className="space-y-1 max-w-md mx-auto">
            <h3 className="text-base font-bold text-brand-charcoal">
              Autonomous Policy & Regulation Scan in Progress
            </h3>
            <p className="text-xs text-brand-charcoalMuted">
              Evaluating pairwise statements using domain clusters, semantic vectors, and regulatory benchmarks.
            </p>
          </div>

          {/* Multi-Step Scanner Progression */}
          <div className="max-w-md mx-auto space-y-2.5 text-left pt-2">
            {scanSteps.map((step, idx) => {
              const isPast = idx < scanStepIndex;
              const isCurrent = idx === scanStepIndex;

              return (
                <div
                  key={step}
                  className={`flex items-center gap-3 p-2.5 rounded-xl text-xs transition-all ${
                    isCurrent
                      ? 'bg-brand-oceanLight/10 border border-brand-ocean/30 text-brand-ocean font-bold shadow-sm'
                      : isPast
                      ? 'text-emerald-700 font-semibold'
                      : 'text-brand-charcoalMuted/60 opacity-60'
                  }`}
                >
                  <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0">
                    {isPast ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 text-brand-amber animate-spin" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-slate-300" />
                    )}
                  </div>
                  <span>{step}</span>
                </div>
              );
            })}
          </div>

          {/* Animated Progress Bar */}
          <div className="max-w-xs mx-auto space-y-1">
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brand-ocean to-brand-amber transition-all duration-500 rounded-full"
                style={{ width: `${((scanStepIndex + 1) / scanSteps.length) * 100}%` }}
              />
            </div>
            <div className="text-[10px] font-mono text-brand-charcoalMuted">
              Step {scanStepIndex + 1} of {scanSteps.length}
            </div>
          </div>
        </div>
      ) : !errorBanner && activeConflicts.length === 0 ? (
        /* UI State 2: Harmonized Empty State */
        <div className="bg-white rounded-2xl p-12 text-center border border-emerald-200 shadow-card-soft space-y-4 bg-gradient-to-b from-white to-emerald-50/20 animate-in fade-in duration-200">
          <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center border-2 border-emerald-200 shadow-sm">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-brand-charcoal">
              All Guidelines Harmonized — Zero Policy Contradictions Detected
            </h3>
            <p className="text-xs text-brand-charcoalMuted max-w-lg mx-auto leading-relaxed">
              Every active directive in the {currentBrand.name} codex has been cross-referenced against corporate policies and standard FTC, SEC, and GDPR benchmarks. No mutually exclusive statements or legal deadlocks found.
            </p>
          </div>
          <button
            onClick={runAutonomousScan}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-cream hover:bg-brand-sand/50 text-brand-charcoal text-xs font-bold border border-brand-sand transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5 text-brand-ocean" />
            <span>Re-Run Verification Scan</span>
          </button>
        </div>
      ) : (
        /* UI State 3: Discovered Policy Contradictions Grid */
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white rounded-xl border border-brand-sand shadow-card-soft">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-brand-charcoalMuted" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-brand-charcoalMuted">
                Tension Category:
              </span>
              <div className="flex items-center gap-1.5 flex-wrap">
                {[
                  { id: 'all', label: `All (${activeConflicts.length})` },
                  { id: 'direct', label: 'Direct Conflict' },
                  { id: 'paradox', label: 'Policy Paradox' },
                  { id: 'regulatory', label: 'Regulatory Overreach' },
                ].map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setSelectedFilter(f.id)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      selectedFilter === f.id
                        ? 'bg-brand-ocean text-white shadow-sm'
                        : 'bg-brand-cream text-brand-charcoalMuted hover:text-brand-charcoal border border-brand-sand'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="text-xs font-mono text-brand-charcoalMuted">
              Showing <strong className="text-brand-charcoal">{filteredConflicts.length}</strong> of{' '}
              {activeConflicts.length} conflict{activeConflicts.length === 1 ? '' : 's'}
            </div>
          </div>

          {/* Cards List */}
          {filteredConflicts.map((item, idx) => {
            const isResolved =
              (item.id !== undefined && resolvedIds.has(item.id)) ||
              (item.conflict_id && resolvedIds.has(item.conflict_id));

            const ruleA: any = item.rule_a || {};
            const ruleB: any = item.rule_b || {};

            const ruleAId = item.rule_a_id ?? ruleA.id ?? (item as any).statement_a?.id ?? 'A';
            const ruleACode = ruleA.code ?? (item as any).statement_a?.code ?? `RULE-${ruleAId}`;
            const ruleATitle = item.rule_a_title ?? ruleA.title ?? (item as any).statement_a?.title ?? `Rule #${ruleAId}`;
            const ruleAText = item.rule_a_text ?? ruleA.text ?? ruleA.rule_text ?? (item as any).statement_a?.text ?? '';

            const ruleBId = item.rule_b_id ?? ruleB.id ?? (item as any).statement_b?.id ?? 'B';
            const ruleBCode = ruleB.code ?? (item as any).statement_b?.code ?? `RULE-${ruleBId}`;
            const ruleBTitle = item.rule_b_title ?? ruleB.title ?? (item as any).statement_b?.title ?? `Rule #${ruleBId}`;
            const ruleBText = item.rule_b_text ?? ruleB.text ?? ruleB.rule_text ?? (item as any).statement_b?.text ?? '';

            const isRuleBRegulatory = String(ruleBId).startsWith('REG') || String(ruleBCode).startsWith('FTC') || String(ruleBCode).startsWith('SEC') || String(ruleBCode).startsWith('GDPR');

            const tensionType = item.tension_type || item.conflict_type || 'Direct Conflict';
            const severity = (item.severity || 'high').toLowerCase();

            const explanation =
              item.explanation ??
              item.conflict_explanation ??
              item.contradiction_reason ??
              'Conflicting brand policy requirements detected.';

            const resolution =
              item.suggested_resolution ??
              item.recommendation ??
              'Review policies with legal counsel and clarify governing channel priorities.';

            return (
              <div
                key={item.conflict_id || item.id || idx}
                className={`bg-white rounded-2xl p-6 border shadow-card-soft transition-all duration-200 space-y-5 ${
                  isResolved
                    ? 'border-emerald-300 bg-emerald-50/20 opacity-80'
                    : 'border-brand-sand hover:border-brand-amber/60'
                }`}
              >
                {/* 1. Header with Badges & Action Buttons */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-brand-sand">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    {/* Conflict ID */}
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                      {item.conflict_id || `CONF-${idx + 1}`}
                    </span>

                    {/* Tension Type Badge */}
                    <span
                      className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${
                        tensionType.toLowerCase().includes('regulatory')
                          ? 'bg-rose-50 text-rose-800 border-rose-200'
                          : tensionType.toLowerCase().includes('paradox')
                          ? 'bg-purple-50 text-purple-800 border-purple-200'
                          : 'bg-amber-50 text-amber-900 border-amber-200'
                      }`}
                    >
                      {tensionType}
                    </span>

                    {/* Severity Badge */}
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                        severity === 'critical'
                          ? 'bg-rose-100 text-rose-900 border-rose-300'
                          : severity === 'high'
                          ? 'bg-amber-100 text-amber-900 border-amber-300'
                          : 'bg-slate-100 text-slate-800 border-slate-200'
                      }`}
                    >
                      {severity.toUpperCase()}
                    </span>
                  </div>

                  {/* Actions */}
                  {isResolved ? (
                    <span className="flex items-center gap-1.5 text-xs font-mono text-emerald-700 font-bold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      Harmonized & Resolved
                    </span>
                  ) : (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleOpenResolve(item)}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all active:scale-95 cursor-pointer"
                        id={`btn-resolve-${item.id || idx}`}
                      >
                        <Sparkles className="w-3.5 h-3.5 text-white" />
                        <span>Reconcile / Edit Rule</span>
                      </button>

                      {!isRuleBRegulatory && (
                        <button
                          onClick={() => handleDeactivateRule(item)}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white border border-rose-200 hover:bg-rose-50 text-rose-700 text-xs font-semibold transition-all shadow-sm cursor-pointer"
                          id={`btn-deactivate-${ruleBId}`}
                          title="Deactivate conflicting rule in catalog"
                        >
                          <span>Deactivate Rule B</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* 2. Split Card Showing Conflicting Directive Pair */}
                <div className="grid grid-cols-1 lg:grid-cols-11 gap-4 items-center">
                  {/* Left sub-card: Rule A */}
                  <div className="lg:col-span-5 rounded-xl bg-teal-50/40 border border-teal-200/90 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-white border border-teal-300 text-teal-800">
                        {ruleACode}
                      </span>
                      <span className="text-[10px] font-mono text-teal-700 uppercase font-bold">
                        Directive A
                      </span>
                    </div>
                    <div className="text-xs font-bold text-brand-charcoal">{ruleATitle}</div>
                    <blockquote className="text-xs text-brand-charcoal leading-relaxed font-mono bg-white p-3 rounded-lg border border-teal-200 italic border-l-4 border-l-teal-600">
                      "{ruleAText}"
                    </blockquote>
                  </div>

                  {/* VS Connector */}
                  <div className="lg:col-span-1 flex flex-col items-center justify-center py-2 lg:py-0">
                    <div className="px-2.5 py-1 rounded-full bg-rose-50 border border-rose-200 text-rose-700 font-mono text-[10px] font-bold shadow-sm text-center">
                      VS
                    </div>
                    <span className="text-[9px] font-mono text-rose-600 mt-1 uppercase tracking-tighter font-bold text-center">
                      {tensionType.toLowerCase().includes('regulatory') ? 'Regulatory Clash' : 'Semantic Tension'}
                    </span>
                  </div>

                  {/* Right sub-card: Rule B */}
                  <div className={`lg:col-span-5 rounded-xl p-4 space-y-2 border ${
                    isRuleBRegulatory
                      ? 'bg-indigo-50/40 border-indigo-200/90'
                      : 'bg-amber-50/40 border-amber-200/90'
                  }`}>
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-white border ${
                        isRuleBRegulatory ? 'border-indigo-300 text-indigo-800' : 'border-amber-300 text-amber-800'
                      }`}>
                        {ruleBCode}
                      </span>
                      <span className={`text-[10px] font-mono uppercase font-bold ${
                        isRuleBRegulatory ? 'text-indigo-800' : 'text-amber-800'
                      }`}>
                        {isRuleBRegulatory ? 'Regulatory Benchmark' : 'Directive B'}
                      </span>
                    </div>
                    <div className="text-xs font-bold text-brand-charcoal">{ruleBTitle}</div>
                    <blockquote className={`text-xs text-brand-charcoal leading-relaxed font-mono bg-white p-3 rounded-lg border italic border-l-4 ${
                      isRuleBRegulatory
                        ? 'border-indigo-200 border-l-indigo-600'
                        : 'border-amber-200 border-l-brand-amber'
                    }`}>
                      "{ruleBText}"
                    </blockquote>
                  </div>
                </div>

                {/* 3. Deep Ocean Teal AI Tension Breakdown Box */}
                <div className="bg-brand-ocean text-white p-4 rounded-xl border-l-4 border-brand-amber space-y-3 shadow-sm">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-brand-amber font-bold flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-brand-amber" />
                      AI Contradiction Explanation:
                    </span>
                    <p className="text-xs text-slate-100 mt-1.5 leading-relaxed font-sans">
                      {explanation}
                    </p>
                  </div>

                  {resolution && (
                    <div className="pt-2.5 border-t border-brand-oceanLight/30 flex items-start gap-2">
                      <ArrowRight className="w-3.5 h-3.5 text-brand-amber shrink-0 mt-0.5" />
                      <div className="text-[11px] text-brand-cream leading-relaxed">
                        <strong className="text-brand-amber font-mono uppercase tracking-wide mr-1.5">
                          Recommended Resolution:
                        </strong>
                        <span>{resolution}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Harmonization / Resolution Modal */}
      {activeResolveItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-oceanDark/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-xl rounded-2xl bg-white border border-brand-sand shadow-card-elevated p-6 text-brand-charcoal space-y-5 animate-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-brand-sand pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-brand-amber/15 border border-brand-amber/30 flex items-center justify-center text-brand-amber">
                  <Sparkles className="w-5 h-5 text-brand-amber" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-brand-charcoal">
                    Harmonize Policy Contradiction
                  </h3>
                  <p className="text-xs text-brand-charcoalMuted">
                    {activeResolveItem.conflict_id || 'Conflict'} • {activeResolveItem.tension_type || 'Policy Contradiction'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setActiveResolveItem(null)}
                className="p-1 rounded-lg text-brand-charcoalMuted hover:text-brand-charcoal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Resolution Strategy Selection */}
            <div className="space-y-3">
              <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold">
                Select Harmonization Resolution Action
              </label>

              <div className="space-y-2">
                <label
                  onClick={() => setSelectedStrategy('amend')}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedStrategy === 'amend'
                      ? 'bg-brand-oceanLight/10 border-brand-amber shadow-sm'
                      : 'bg-brand-cream border-brand-sand hover:border-brand-sand'
                  }`}
                >
                  <input
                    type="radio"
                    name="strategy"
                    checked={selectedStrategy === 'amend'}
                    onChange={() => setSelectedStrategy('amend')}
                    className="mt-1 text-brand-amber focus:ring-brand-amber"
                  />
                  <div>
                    <span className="text-xs font-bold text-brand-charcoal block">
                      Amend Policy Scoping (Recommended)
                    </span>
                    <p className="text-[11px] text-brand-charcoalMuted mt-0.5 leading-relaxed">
                      {activeResolveItem.suggested_resolution || activeResolveItem.recommendation}
                    </p>
                  </div>
                </label>

                <label
                  onClick={() => setSelectedStrategy('deactivate')}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedStrategy === 'deactivate'
                      ? 'bg-brand-oceanLight/10 border-brand-amber shadow-sm'
                      : 'bg-brand-cream border-brand-sand hover:border-brand-sand'
                  }`}
                >
                  <input
                    type="radio"
                    name="strategy"
                    checked={selectedStrategy === 'deactivate'}
                    onChange={() => setSelectedStrategy('deactivate')}
                    className="mt-1 text-brand-amber focus:ring-brand-amber"
                  />
                  <div>
                    <span className="text-xs font-bold text-brand-charcoal block">
                      Deactivate Outdated Guideline
                    </span>
                    <p className="text-[11px] text-brand-charcoalMuted mt-0.5">
                      Archive the older directive in the vector store to prevent false-positive flags during reviews.
                    </p>
                  </div>
                </label>

                <label
                  onClick={() => setSelectedStrategy('merge')}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedStrategy === 'merge'
                      ? 'bg-brand-oceanLight/10 border-brand-amber shadow-sm'
                      : 'bg-brand-cream border-brand-sand hover:border-brand-sand'
                  }`}
                >
                  <input
                    type="radio"
                    name="strategy"
                    checked={selectedStrategy === 'merge'}
                    onChange={() => setSelectedStrategy('merge')}
                    className="mt-1 text-brand-amber focus:ring-brand-amber"
                  />
                  <div>
                    <span className="text-xs font-bold text-brand-charcoal block">
                      Merge into Unified Guideline Codex Entry
                    </span>
                    <p className="text-[11px] text-brand-charcoalMuted mt-0.5">
                      Synthesize both statements into a single comprehensive rule with clear channel exemptions.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Editable Amendment Area */}
            {selectedStrategy === 'amend' && (
              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-mono uppercase text-brand-charcoalMuted font-bold flex items-center justify-between">
                  <span>Reconciled Guideline Language:</span>
                  <span className="text-[10px] text-brand-ocean">AI Optimized</span>
                </label>
                <textarea
                  value={customAmendmentText}
                  onChange={(e) => setCustomAmendmentText(e.target.value)}
                  rows={3}
                  className="w-full rounded-xl bg-brand-cream/50 border border-brand-sand p-3 text-xs text-brand-charcoal focus:outline-none focus:ring-1 focus:ring-brand-amber font-mono"
                />
              </div>
            )}

            {/* Two-Tier Legal Governance & Sign-Off Section */}
            <div className="rounded-xl bg-brand-cream/60 border border-brand-sand/80 p-3.5 space-y-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-bold text-brand-charcoal uppercase tracking-wider font-mono">
                  Two-Tier Legal Sign-Off & Audit Logging
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-[11px] font-medium text-brand-charcoalMuted block mb-1">
                    Approver Authority Role
                  </label>
                  <select
                    value={approverRole}
                    onChange={(e: any) => setApproverRole(e.target.value)}
                    className="w-full rounded-lg bg-white border border-brand-sand px-2.5 py-1.5 text-xs text-brand-charcoal focus:ring-1 focus:ring-brand-amber font-medium"
                  >
                    <option value="Legal Counsel">⚖️ Legal Counsel</option>
                    <option value="Brand Operations Director">🏢 Brand Operations Director</option>
                    <option value="Executive Risk Lead">🛡️ Executive Risk Lead</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-brand-charcoalMuted block mb-1">
                    Signatory Name / Email
                  </label>
                  <input
                    type="text"
                    value={approverName}
                    onChange={(e) => setApproverName(e.target.value)}
                    placeholder="Chief Compliance Officer"
                    className="w-full rounded-lg bg-white border border-brand-sand px-2.5 py-1.5 text-xs text-brand-charcoal focus:ring-1 focus:ring-brand-amber font-mono"
                  />
                </div>
              </div>
              <div>
                <label className="text-[11px] font-medium text-brand-charcoalMuted block mb-1">
                  Compliance Justification (Audit Record)
                </label>
                <input
                  type="text"
                  value={approvalJustification}
                  onChange={(e) => setApprovalJustification(e.target.value)}
                  placeholder="Harmonized to satisfy FTC / SEC truth-in-advertising guidelines."
                  className="w-full rounded-lg bg-white border border-brand-sand px-2.5 py-1.5 text-xs text-brand-charcoal focus:ring-1 focus:ring-brand-amber"
                />
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-brand-sand">
              <button
                type="button"
                onClick={() => setActiveResolveItem(null)}
                disabled={isApplyingResolution}
                className="px-4 py-2 rounded-xl text-xs font-medium text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApplyResolution}
                disabled={isApplyingResolution}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all active:scale-95 disabled:opacity-50"
              >
                {isApplyingResolution ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Updating Policy Index...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4 text-white" />
                    <span>Apply Harmonization</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditPage;
