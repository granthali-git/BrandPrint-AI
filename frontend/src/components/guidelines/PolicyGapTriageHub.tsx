import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  X,
  Edit2,
  Check,
  RefreshCw,
  Scale,
  Zap,
  ArrowRight,
  BookOpen,
} from 'lucide-react';
import { guidelinesApi } from '../../api/guidelines';
import { GuidelineGap } from '../../types';

interface PolicyGapTriageHubProps {
  brandId: number | string;
  onRuleAdopted?: () => void;
}

export const PolicyGapTriageHub: React.FC<PolicyGapTriageHubProps> = ({ brandId, onRuleAdopted }) => {
  const [gaps, setGaps] = useState<GuidelineGap[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [editingGapId, setEditingGapId] = useState<number | null>(null);

  // In-place edit state
  const [editTitle, setEditTitle] = useState('');
  const [editRuleText, setEditRuleText] = useState('');
  const [editCategory, setEditCategory] = useState('tone');
  const [toast, setToast] = useState<string | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  const fetchGaps = async () => {
    setLoading(true);
    try {
      const res = await guidelinesApi.getGaps(brandId, 'PENDING_DECISION');
      const list = Array.isArray(res) ? res : res?.gaps || res?.proposed_rules || [];
      setGaps(list);
    } catch (err) {
      console.warn('Failed to fetch guideline gaps:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGaps();
  }, [brandId]);

  const handleAdopt = async (gap: GuidelineGap) => {
    setActionLoadingId(gap.id);
    setErrorToast(null);
    try {
      await guidelinesApi.triageGap(gap.id, { action: 'ACCEPT_PROPOSAL' });
      setToast(`Proposal codified as active brand guideline & vectorized in FAISS!`);
      await fetchGaps();
      onRuleAdopted?.();
    } catch (err: any) {
      setErrorToast(err?.response?.data?.detail || err?.message || 'Failed to adopt gap as guideline rule.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleStartEdit = (gap: GuidelineGap) => {
    setEditingGapId(gap.id);
    setEditTitle(`Formal Standard: ${gap.claim.slice(0, 40)}`);
    setEditRuleText(gap.suggested_rule_proposal);
    setEditCategory('tone');
  };

  const handleSaveRevised = async (gapId: number) => {
    if (!editRuleText.trim()) return;
    setActionLoadingId(gapId);
    setErrorToast(null);
    try {
      await guidelinesApi.triageGap(gapId, {
        action: 'REVISE',
        custom_title: editTitle.trim() || undefined,
        custom_rule_text: editRuleText.trim(),
        category: editCategory,
      });
      setToast('Custom policy proposal codified and indexed into active FAISS store.');
      setEditingGapId(null);
      await fetchGaps();
      onRuleAdopted?.();
    } catch (err: any) {
      setErrorToast(err?.response?.data?.detail || err?.message || 'Failed to save revised rule.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDismiss = async (gapId: number) => {
    setActionLoadingId(gapId);
    setErrorToast(null);
    try {
      await guidelinesApi.triageGap(gapId, { action: 'DISMISS' });
      setToast('Gap dismissed as intentional marketing exception.');
      await fetchGaps();
    } catch (err: any) {
      setErrorToast(err?.response?.data?.detail || err?.message || 'Failed to dismiss gap.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const uncoveredCount = gaps.filter((g) => g.gap_type === 'UNCOVERED_TOPIC').length;
  const ambiguousCount = gaps.filter((g) => g.gap_type === 'AMBIGUOUS_RULE').length;

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toast && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{toast}</span>
          </div>
          <button onClick={() => setToast(null)} className="text-emerald-600 hover:text-emerald-900 cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {errorToast && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{errorToast}</span>
          </div>
          <button onClick={() => setErrorToast(null)} className="text-red-600 hover:text-red-900 cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Header Info & Metric Banner */}
      <div className="bg-white rounded-2xl p-6 border border-brand-sand shadow-card-soft space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-ocean text-white flex items-center justify-center font-bold shadow-sm">
              <Sparkles className="w-5 h-5 text-brand-amber" />
            </div>
            <div>
              <h2 className="text-base font-bold text-brand-charcoal">
                Autonomous Policy Gap & Ambiguity Triage Hub
              </h2>
              <p className="text-xs text-brand-charcoalMuted">
                Detects unregulated marketing claims and vague brand directives, synthesizing concrete enforceable policy proposals.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchGaps}
              disabled={loading}
              className="p-2 rounded-xl bg-brand-cream border border-brand-sand hover:border-brand-ocean text-brand-charcoal text-xs flex items-center gap-1.5 cursor-pointer"
              title="Refresh detected gaps"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Counter Pills */}
        <div className="flex items-center gap-3 flex-wrap pt-2 border-t border-brand-sand/60">
          <span className="px-3 py-1 rounded-xl bg-brand-cream border border-brand-sand text-xs font-mono font-semibold text-brand-charcoal">
            Pending Proposals: <strong className="text-brand-ocean">{gaps.length}</strong>
          </span>
          <span className="px-3 py-1 rounded-xl bg-amber-50 border border-amber-200 text-xs font-mono font-semibold text-amber-900">
            Unregulated Topics: <strong>{uncoveredCount}</strong>
          </span>
          <span className="px-3 py-1 rounded-xl bg-purple-50 border border-purple-200 text-xs font-mono font-semibold text-purple-900">
            Ambiguous Directives: <strong>{ambiguousCount}</strong>
          </span>
        </div>
      </div>

      {/* Gaps List */}
      <div className="space-y-4">
        {loading && gaps.length === 0 ? (
          <div className="py-16 text-center bg-white rounded-2xl border border-brand-sand">
            <div className="w-8 h-8 border-3 border-brand-amber border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs font-mono text-brand-charcoalMuted">Scanning for uncodified policy gaps...</p>
          </div>
        ) : gaps.length === 0 ? (
          <div className="py-16 text-center bg-white rounded-2xl border border-dashed border-brand-sand p-8">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-brand-charcoal">Zero Policy Gaps Pending Triage</h3>
            <p className="text-xs text-brand-charcoalMuted mt-1 max-w-md mx-auto">
              All reviewed marketing statements and creatives currently match active, codified brand guidelines.
            </p>
          </div>
        ) : (
          gaps.map((gap) => {
            const isEditing = editingGapId === gap.id;
            const isUncovered = gap.gap_type === 'UNCOVERED_TOPIC';
            const isTriaging = actionLoadingId === gap.id;

            return (
              <div
                key={gap.id}
                className="bg-white rounded-2xl p-5 border border-brand-sand shadow-card-soft space-y-4 hover:border-brand-amber/40 transition-all"
              >
                {/* Card Header */}
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold ${
                        isUncovered
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'bg-purple-50 text-purple-800 border border-purple-200'
                      }`}
                    >
                      {isUncovered ? <Zap className="w-3.5 h-3.5" /> : <Scale className="w-3.5 h-3.5" />}
                      {isUncovered ? 'Unregulated Content Claim' : 'Ambiguous / Subjective Directive'}
                    </span>

                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        gap.severity === 'CRITICAL' || gap.severity === 'HIGH'
                          ? 'bg-red-50 text-red-700 border border-red-200'
                          : 'bg-yellow-50 text-yellow-800 border border-yellow-200'
                      }`}
                    >
                      {gap.severity} Priority
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-brand-charcoalMuted">
                    ID #{gap.id}
                  </span>
                </div>

                {/* Flagged Claim Box */}
                <div className="bg-[#FBF9F4] p-3 rounded-xl border border-brand-sand space-y-1">
                  <span className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block">
                    Detected In Content:
                  </span>
                  <p className="text-xs font-semibold text-brand-charcoal italic">
                    &ldquo;{gap.claim}&rdquo;
                  </p>
                </div>

                {/* In-place Edit Form vs Proposal View */}
                {isEditing ? (
                  <div className="p-4 rounded-xl bg-brand-cream/60 border border-brand-sand space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                          Rule Title
                        </label>
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full px-3 py-1.5 rounded-lg border border-brand-sand bg-white text-xs text-brand-charcoal font-semibold"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                          Category
                        </label>
                        <select
                          value={editCategory}
                          onChange={(e) => setEditCategory(e.target.value)}
                          className="w-full px-3 py-1.5 rounded-lg border border-brand-sand bg-white text-xs text-brand-charcoal"
                        >
                          <option value="prohibited_claim">Prohibited Claim</option>
                          <option value="legal_compliance">Legal Compliance</option>
                          <option value="tone">Tone of Voice</option>
                          <option value="visual">Visual & Design</option>
                          <option value="fact">Fact & Certification</option>
                          <option value="accessibility">Accessibility</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                        Concrete Enforceable Policy Standard
                      </label>
                      <textarea
                        value={editRuleText}
                        onChange={(e) => setEditRuleText(e.target.value)}
                        rows={3}
                        className="w-full p-2.5 rounded-lg border border-brand-sand bg-white text-xs text-brand-charcoal font-mono"
                      />
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-1">
                      <button
                        onClick={() => setEditingGapId(null)}
                        className="px-3 py-1.5 rounded-lg text-xs text-brand-charcoalMuted hover:text-brand-charcoal"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveRevised(gap.id)}
                        disabled={isTriaging}
                        className="px-4 py-1.5 rounded-lg bg-brand-ocean hover:bg-brand-oceanDark text-white font-bold text-xs shadow-sm cursor-pointer"
                      >
                        Save & Codify Rule
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5 text-brand-ocean" />
                      Suggested Rule Proposal:
                    </span>
                    <p className="text-xs text-brand-charcoal font-mono bg-white p-3 rounded-xl border border-brand-sand/80 leading-relaxed">
                      {gap.suggested_rule_proposal}
                    </p>
                  </div>
                )}

                {/* Managerial Governance Actions */}
                {!isEditing && (
                  <div className="flex items-center justify-between pt-2 border-t border-brand-sand/60 flex-wrap gap-2">
                    <div className="text-[11px] text-brand-charcoalMuted font-mono">
                      Governance Decision Required
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDismiss(gap.id)}
                        disabled={isTriaging}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-sand hover:bg-red-50 hover:border-red-200 text-xs font-semibold text-brand-charcoalMuted hover:text-red-700 transition-colors cursor-pointer"
                        title="Dismiss as intentional exception"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Dismiss Exception</span>
                      </button>

                      <button
                        onClick={() => handleStartEdit(gap)}
                        disabled={isTriaging}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-sand hover:border-brand-ocean bg-white text-xs font-semibold text-brand-charcoal transition-colors cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5 text-brand-ocean" />
                        <span>Edit & Save</span>
                      </button>

                      <button
                        onClick={() => handleAdopt(gap)}
                        disabled={isTriaging}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-brand-ocean hover:bg-brand-oceanDark text-white text-xs font-bold shadow-sm transition-all active:scale-95 cursor-pointer"
                      >
                        <Check className="w-3.5 h-3.5 text-brand-amber" />
                        <span>Adopt as Active Rule</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default PolicyGapTriageHub;

