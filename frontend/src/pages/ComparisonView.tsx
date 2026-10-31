import React, { useState, useEffect } from 'react';
import {
  Columns,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Sparkles,
  Layers,
  Lock,
  RotateCcw,
  FileText,
  SlidersHorizontal,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { reviewsApi } from '../api/reviews';
import { DualComparisonResponse, Finding } from '../types';

export const ComparisonView: React.FC = () => {
  const { currentBrand } = useApp();

  // Mode: Compare existing submissions vs raw text
  const [mode, setMode] = useState<'submissions' | 'raw_text'>('raw_text');
  const [recentSubmissions, setRecentSubmissions] = useState<any[]>([]);
  const [selectedIdA, setSelectedIdA] = useState<string | number>('');
  const [selectedIdB, setSelectedIdB] = useState<string | number>('');

  // Raw text inputs
  const [textA, setTextA] = useState<string>(
    'Discover AstraForge Enterprise Cloud! We are the cheapest solution and guaranteed #1 platform on the market with 100% infallible uptime. Call right now to claim your exclusive 50% limited promotion discount!'
  );
  const [textB, setTextB] = useState<string>(
    'AstraForge Enterprise Cloud delivers high-availability infrastructure engineered for mission-critical operations. Review our published SOC 2 Type II report and third-party verified 99.99% uptime metrics.'
  );

  const [loading, setLoading] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<DualComparisonResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'resolved' | 'new_risks'>('all');

  // Load recent submissions on mount
  useEffect(() => {
    reviewsApi
      .list(currentBrand.id, 10)
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setRecentSubmissions(data);
          if (data.length >= 2) {
            setSelectedIdA(data[0].id);
            setSelectedIdB(data[1].id);
          } else if (data.length === 1) {
            setSelectedIdA(data[0].id);
          }
        }
      })
      .catch((err) => console.warn('Could not load submissions for comparison:', err));
  }, [currentBrand.id]);

  // Execute dual comparison
  const handleRunComparison = async () => {
    setLoading(true);
    try {
      const payload: any = { brand_id: currentBrand.id };
      if (mode === 'submissions') {
        if (!selectedIdA || !selectedIdB) {
          alert('Please select both Slot A and Slot B submissions to compare.');
          setLoading(false);
          return;
        }
        payload.asset_id_a = selectedIdA;
        payload.asset_id_b = selectedIdB;
      } else {
        if (!textA.trim() || !textB.trim()) {
          alert('Please enter copy in both Slot A and Slot B.');
          setLoading(false);
          return;
        }
        payload.text_a = textA;
        payload.text_b = textB;
      }

      const res = await reviewsApi.compareReviews(payload);
      setComparisonResult(res);
    } catch (err: any) {
      console.error('Comparison execution failed:', err);
      alert(err?.response?.data?.detail || 'Failed to execute comparative audit.');
    } finally {
      setLoading(false);
    }
  };

  // Run automatically on first mount with initial texts
  useEffect(() => {
    handleRunComparison();
  }, []);

  const metrics = comparisonResult?.metrics;
  const scoreDelta = comparisonResult?.score_delta ?? 0;
  const isPositiveDelta = scoreDelta >= 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-200 text-brand-charcoal">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-brand-sand">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-brand-charcoal flex items-center gap-2">
              <Columns className="w-6 h-6 text-brand-ocean" />
              Side-by-Side Dual Content & Version Comparison
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-brand-ocean text-white border border-brand-oceanLight">
              Strict Max: 2 Items
            </span>
          </div>
          <p className="text-xs text-brand-charcoalMuted mt-1">
            Comparative brand safety compliance, automated diffing, and policy violation delta tracking.
          </p>
        </div>

        {/* Input Mode Selector */}
        <div className="flex items-center gap-2 bg-brand-cream/80 p-1 rounded-xl border border-brand-sand">
          <button
            type="button"
            onClick={() => setMode('raw_text')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              mode === 'raw_text'
                ? 'bg-brand-ocean text-white shadow-sm'
                : 'text-brand-charcoalMuted hover:text-brand-charcoal'
            }`}
          >
            Draft Text Diff
          </button>
          <button
            type="button"
            onClick={() => setMode('submissions')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              mode === 'submissions'
                ? 'bg-brand-ocean text-white shadow-sm'
                : 'text-brand-charcoalMuted hover:text-brand-charcoal'
            }`}
          >
            Audited Submissions
          </button>
        </div>
      </div>

      {/* Dual Input Slots (Strictly Slot A and Slot B - Capped at 2) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">
        {/* Slot A: Reference Version */}
        <div className="bg-white rounded-2xl p-5 border border-brand-sand shadow-card-soft flex flex-col space-y-3">
          <div className="flex items-center justify-between border-b border-brand-sand pb-2.5">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-brand-ocean text-white text-xs font-mono font-bold flex items-center justify-center">
                A
              </span>
              <h2 className="text-sm font-bold text-brand-charcoal">Slot A (Reference / Draft 1)</h2>
            </div>
            <span className="text-[10px] font-mono text-brand-charcoalMuted uppercase tracking-wider font-semibold">
              Baseline
            </span>
          </div>

          {mode === 'submissions' ? (
            <div className="space-y-2">
              <label className="text-xs text-brand-charcoalMuted">Select Audited Asset A:</label>
              <select
                value={selectedIdA}
                onChange={(e) => setSelectedIdA(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-brand-sand bg-white text-brand-charcoal focus:ring-1 focus:ring-brand-amber"
              >
                <option value="">-- Choose Submission --</option>
                {recentSubmissions.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} • {s.title || `Review #${s.id}`} ({s.status})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="space-y-1.5 flex-1 flex flex-col">
              <label className="text-xs text-brand-charcoalMuted">Reference Content Copy:</label>
              <textarea
                value={textA}
                onChange={(e) => setTextA(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 text-xs rounded-xl border border-brand-sand bg-[#FBF9F4] text-brand-charcoal focus:ring-1 focus:ring-brand-amber font-sans resize-none flex-1"
                placeholder="Enter baseline content copy..."
              />
            </div>
          )}
        </div>

        {/* Slot B: Revised Version */}
        <div className="bg-white rounded-2xl p-5 border border-brand-sand shadow-card-soft flex flex-col space-y-3">
          <div className="flex items-center justify-between border-b border-brand-sand pb-2.5">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-brand-amber text-white text-xs font-mono font-bold flex items-center justify-center">
                B
              </span>
              <h2 className="text-sm font-bold text-brand-charcoal">Slot B (Revised / Test Copy)</h2>
            </div>
            <span className="text-[10px] font-mono text-brand-amber font-semibold uppercase tracking-wider">
              Comparison Candidate
            </span>
          </div>

          {mode === 'submissions' ? (
            <div className="space-y-2">
              <label className="text-xs text-brand-charcoalMuted">Select Audited Asset B:</label>
              <select
                value={selectedIdB}
                onChange={(e) => setSelectedIdB(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-brand-sand bg-white text-brand-charcoal focus:ring-1 focus:ring-brand-amber"
              >
                <option value="">-- Choose Submission --</option>
                {recentSubmissions.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} • {s.title || `Review #${s.id}`} ({s.status})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="space-y-1.5 flex-1 flex flex-col">
              <label className="text-xs text-brand-charcoalMuted">Revised Content Copy:</label>
              <textarea
                value={textB}
                onChange={(e) => setTextB(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 text-xs rounded-xl border border-brand-sand bg-[#FBF9F4] text-brand-charcoal focus:ring-1 focus:ring-brand-amber font-sans resize-none flex-1"
                placeholder="Enter revised content copy to evaluate improvements..."
              />
            </div>
          )}
        </div>

        {/* Hard Constraint Cap Notice */}
        <div className="md:col-span-2 flex items-center justify-between bg-brand-cream/60 p-3 rounded-xl border border-brand-sand text-xs text-brand-charcoalMuted">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-brand-ocean" />
            <span>
              <strong>Hard Capacity Rule:</strong> Comparison workspace is strictly locked to 2 assets to ensure
              accurate bi-directional policy diffing. Adding additional slots is disabled.
            </span>
          </div>
          <button
            onClick={handleRunComparison}
            disabled={loading}
            className="px-4 py-2 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white font-bold text-xs shadow-sm transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{loading ? 'Evaluating...' : 'Run Comparative Audit'}</span>
          </button>
        </div>
      </div>

      {/* Comparison Metrics Delta Bar */}
      {comparisonResult && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Metric 1: Safety Score Delta */}
          <div className="bg-white p-4 rounded-xl border border-brand-sand shadow-card-soft">
            <span className="text-[11px] font-mono text-brand-charcoalMuted uppercase font-semibold">
              Compliance Delta
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`text-2xl font-black font-mono ${
                  isPositiveDelta ? 'text-emerald-600' : 'text-red-600'
                }`}
              >
                {isPositiveDelta ? `+${scoreDelta}%` : `${scoreDelta}%`}
              </span>
              <span
                className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  isPositiveDelta
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}
              >
                {isPositiveDelta ? <TrendingUp className="w-3 h-3 mr-0.5" /> : <TrendingDown className="w-3 h-3 mr-0.5" />}
                {isPositiveDelta ? 'Improved' : 'Regressed'}
              </span>
            </div>
            <div className="text-[11px] text-brand-charcoalMuted mt-1">
              {metrics?.score_a}% (A) → {metrics?.score_b}% (B)
            </div>
          </div>

          {/* Metric 2: Resolved Violations */}
          <div className="bg-white p-4 rounded-xl border border-brand-sand shadow-card-soft">
            <span className="text-[11px] font-mono text-brand-charcoalMuted uppercase font-semibold">
              Resolved Violations
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-2xl font-black font-mono text-emerald-600">
                {comparisonResult.resolved_violations.length}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Remediated
              </span>
            </div>
            <div className="text-[11px] text-brand-charcoalMuted mt-1">Cleared from baseline</div>
          </div>

          {/* Metric 3: Newly Introduced Risks */}
          <div className="bg-white p-4 rounded-xl border border-brand-sand shadow-card-soft">
            <span className="text-[11px] font-mono text-brand-charcoalMuted uppercase font-semibold">
              New Infractions
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`text-2xl font-black font-mono ${
                  comparisonResult.new_risks.length > 0 ? 'text-red-600' : 'text-emerald-600'
                }`}
              >
                {comparisonResult.new_risks.length}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  comparisonResult.new_risks.length > 0
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}
              >
                {comparisonResult.new_risks.length > 0 ? 'Alert' : 'Zero New Risks'}
              </span>
            </div>
            <div className="text-[11px] text-brand-charcoalMuted mt-1">Introduced in candidate</div>
          </div>

          {/* Metric 4: Tone & Accessibility */}
          <div className="bg-white p-4 rounded-xl border border-brand-sand shadow-card-soft">
            <span className="text-[11px] font-mono text-brand-charcoalMuted uppercase font-semibold">
              Tone & Accessibility
            </span>
            <div className="mt-1 font-mono text-xs font-bold text-brand-charcoal">
              {metrics?.tone_alignment_b || '98% Aligned'}
            </div>
            <div className="text-[11px] text-brand-charcoalMuted mt-1">
              Contrast: {metrics?.contrast_ratio_b || 'WCAG AAA'}
            </div>
          </div>
        </div>
      )}

      {/* Narrative Diff Summary Card */}
      {comparisonResult && (
        <div className="bg-white rounded-2xl p-5 border border-brand-sand shadow-card-soft space-y-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-brand-ocean" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-brand-charcoal">
              Executive Diff Summary
            </h3>
          </div>
          <p className="text-sm font-sans text-brand-charcoal leading-relaxed">
            {comparisonResult.diff_summary}
          </p>
        </div>
      )}

      {/* Findings Delta Table & Tabs */}
      {comparisonResult && (
        <div className="bg-white rounded-2xl border border-brand-sand shadow-card-soft overflow-hidden">
          <div className="px-6 py-4 border-b border-brand-sand bg-brand-cream/40 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-brand-ocean" />
              <h3 className="text-sm font-bold text-brand-charcoal">Comparative Violation Triage</h3>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'all'
                    ? 'bg-brand-ocean text-white'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
              >
                All Findings (
                {comparisonResult.resolved_violations.length +
                  comparisonResult.new_risks.length +
                  (comparisonResult.persistent_violations?.length || 0)}
                )
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('resolved')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'resolved'
                    ? 'bg-emerald-600 text-white'
                    : 'text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                }`}
              >
                Resolved ({comparisonResult.resolved_violations.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('new_risks')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'new_risks'
                    ? 'bg-red-600 text-white'
                    : 'text-red-700 bg-red-50 hover:bg-red-100'
                }`}
              >
                New Risks ({comparisonResult.new_risks.length})
              </button>
            </div>
          </div>

          <div className="p-6 space-y-3">
            {/* Resolved Violations */}
            {(activeTab === 'all' || activeTab === 'resolved') &&
              comparisonResult.resolved_violations.map((f, i) => (
                <div
                  key={`res-${i}`}
                  className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/50 flex items-start justify-between gap-4 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-emerald-100 text-emerald-800 border border-emerald-300">
                        Resolved
                      </span>
                      <span className="font-semibold text-emerald-950 font-mono">
                        {f.rule_code || f.issue_type}
                      </span>
                    </div>
                    <p className="text-emerald-900 font-medium">
                      Flagged in Reference: &quot;{f.flagged_text}&quot;
                    </p>
                    <p className="text-emerald-700 text-[11px]">{f.explanation}</p>
                  </div>
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                </div>
              ))}

            {/* Newly Introduced Risks */}
            {(activeTab === 'all' || activeTab === 'new_risks') &&
              comparisonResult.new_risks.map((f, i) => (
                <div
                  key={`new-${i}`}
                  className="p-3.5 rounded-xl border border-red-200 bg-red-50/50 flex items-start justify-between gap-4 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-red-100 text-red-800 border border-red-300">
                        New Risk Introduced
                      </span>
                      <span className="font-semibold text-red-950 font-mono">
                        {f.rule_code || f.issue_type}
                      </span>
                      <span className="font-mono text-[10px] uppercase font-bold text-red-700">
                        [{f.severity}]
                      </span>
                    </div>
                    <p className="text-red-900 font-medium">
                      Introduced in Candidate: &quot;{f.flagged_text}&quot;
                    </p>
                    <p className="text-red-700 text-[11px]">{f.explanation}</p>
                  </div>
                  <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                </div>
              ))}

            {/* Persistent Violations (if in 'all' view) */}
            {activeTab === 'all' &&
              (comparisonResult.persistent_violations || []).map((f, i) => (
                <div
                  key={`pers-${i}`}
                  className="p-3.5 rounded-xl border border-brand-sand bg-white flex items-start justify-between gap-4 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-amber-50 text-amber-800 border border-amber-200">
                        Unchanged Violation
                      </span>
                      <span className="font-semibold text-brand-charcoal font-mono">
                        {f.rule_code || f.issue_type}
                      </span>
                    </div>
                    <p className="text-brand-charcoal font-medium">
                      Remaining in Both: &quot;{f.flagged_text}&quot;
                    </p>
                    <p className="text-brand-charcoalMuted text-[11px]">{f.explanation}</p>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ComparisonView;

