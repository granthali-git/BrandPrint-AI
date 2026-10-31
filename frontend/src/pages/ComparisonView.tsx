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
  ChevronRight,
  Diff,
  Eye,
  Check,
  X,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { reviewsApi } from '../api/reviews';
import { DualComparisonResponse, Finding } from '../types';
import { SlotCard, SlotState } from '../components/comparison/SlotCard';

export const ComparisonView: React.FC = () => {
  const { currentBrand } = useApp();

  // Slot A State (Baseline / Reference)
  const [slotA, setSlotA] = useState<SlotState>({
    sourceType: 'text',
    content:
      'Discover AstraForge Enterprise Cloud! We are the cheapest solution and guaranteed #1 platform on the market with 100% infallible uptime. Call right now to claim your exclusive 50% limited promotion discount!',
    file: null,
    url: '',
    previewUrl: null,
    isExtracting: false,
    extractionMsg: null,
  });

  // Slot B State (Revised / Test Candidate)
  const [slotB, setSlotB] = useState<SlotState>({
    sourceType: 'text',
    content:
      'AstraForge Enterprise Cloud delivers high-availability infrastructure engineered for mission-critical operations. Review our published SOC 2 Type II report and third-party verified 99.99% uptime metrics.',
    file: null,
    url: '',
    previewUrl: null,
    isExtracting: false,
    extractionMsg: null,
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<DualComparisonResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'resolved' | 'new_risks' | 'diff'>('all');

  // Extraction Handlers for Slot A
  const handleExtractFileA = async (file: File) => {
    setSlotA((prev) => ({
      ...prev,
      isExtracting: true,
      extractionMsg: `Processing '${file.name}' via Pillow OCR & document parser...`,
    }));
    try {
      const res = await reviewsApi.extractFile(file);
      setSlotA((prev) => ({
        ...prev,
        content: res.extracted_text || '',
        previewUrl: res.preview_url || null,
        isExtracting: false,
        extractionMsg: null,
      }));
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to extract text from '${file.name}'.`);
      setSlotA((prev) => ({ ...prev, isExtracting: false, extractionMsg: null }));
    }
  };

  const handleScrapeUrlA = async (url: string) => {
    if (!url.trim()) return;
    setSlotA((prev) => ({
      ...prev,
      isExtracting: true,
      extractionMsg: 'Scraping webpage with SSRF sandbox...',
    }));
    try {
      const res = await reviewsApi.scrapeUrl(url, currentBrand.id);
      setSlotA((prev) => ({
        ...prev,
        content: res.extracted_text || '',
        previewUrl: res.image_preview_url || null,
        isExtracting: false,
        extractionMsg: null,
      }));
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to scrape URL '${url}'.`);
      setSlotA((prev) => ({ ...prev, isExtracting: false, extractionMsg: null }));
    }
  };

  // Extraction Handlers for Slot B
  const handleExtractFileB = async (file: File) => {
    setSlotB((prev) => ({
      ...prev,
      isExtracting: true,
      extractionMsg: `Processing '${file.name}' via Pillow OCR & document parser...`,
    }));
    try {
      const res = await reviewsApi.extractFile(file);
      setSlotB((prev) => ({
        ...prev,
        content: res.extracted_text || '',
        previewUrl: res.preview_url || null,
        isExtracting: false,
        extractionMsg: null,
      }));
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to extract text from '${file.name}'.`);
      setSlotB((prev) => ({ ...prev, isExtracting: false, extractionMsg: null }));
    }
  };

  const handleScrapeUrlB = async (url: string) => {
    if (!url.trim()) return;
    setSlotB((prev) => ({
      ...prev,
      isExtracting: true,
      extractionMsg: 'Scraping webpage with SSRF sandbox...',
    }));
    try {
      const res = await reviewsApi.scrapeUrl(url, currentBrand.id);
      setSlotB((prev) => ({
        ...prev,
        content: res.extracted_text || '',
        previewUrl: res.image_preview_url || null,
        isExtracting: false,
        extractionMsg: null,
      }));
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to scrape URL '${url}'.`);
      setSlotB((prev) => ({ ...prev, isExtracting: false, extractionMsg: null }));
    }
  };

  // Run Side-by-Side Dual Comparison Execution
  const handleRunComparison = async () => {
    const textA = slotA.content.trim();
    const textB = slotB.content.trim();

    if (!textA || !textB) {
      alert('Please provide or extract content for both Slot A and Slot B before comparing.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        brand_id: currentBrand.id,
        slot_a: {
          source_type: slotA.sourceType,
          text_content: textA,
          file_name: slotA.file?.name,
          url: slotA.url,
        },
        slot_b: {
          source_type: slotB.sourceType,
          text_content: textB,
          file_name: slotB.file?.name,
          url: slotB.url,
        },
        text_a: textA,
        text_b: textB,
      };

      const res = await reviewsApi.compareReviews(payload);
      setComparisonResult(res);
    } catch (err: any) {
      console.error('Comparison execution failed:', err);
      alert(err?.response?.data?.detail || 'Failed to execute comparative audit.');
    } finally {
      setLoading(false);
    }
  };

  // Run automatically on first mount
  useEffect(() => {
    handleRunComparison();
  }, []);

  const metrics = comparisonResult?.metrics;
  const scoreDelta = comparisonResult?.score_delta ?? 0;
  const isPositiveDelta = scoreDelta >= 0;

  // Simple text diff rendering for visual changes
  const renderVisualTextDiff = () => {
    if (!comparisonResult) return null;
    const wordsA = new Set(
      comparisonResult.content_a
        .toLowerCase()
        .replace(/[^\w\s]/g, '')
        .split(/\s+/)
    );
    const wordsBList = comparisonResult.content_b.split(/\s+/);

    return (
      <div className="p-4 rounded-xl bg-[#FBF9F4] border border-brand-sand leading-relaxed text-xs font-sans space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono text-brand-charcoalMuted border-b border-brand-sand pb-2">
          <span className="font-bold text-brand-charcoal">Slot B Text with Comparative Inclusions</span>
          <span className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-emerald-700">
              <span className="w-2.5 h-2.5 rounded bg-emerald-100 border border-emerald-300 inline-block" />
              New or Modified Wording
            </span>
            <span className="flex items-center gap-1 text-slate-700">
              <span className="w-2.5 h-2.5 rounded bg-white border border-slate-300 inline-block" />
              Retained Baseline
            </span>
          </span>
        </div>

        <div className="p-2 select-text leading-loose">
          {wordsBList.map((word, idx) => {
            const cleanWord = word.toLowerCase().replace(/[^\w\s]/g, '');
            const isNew = cleanWord.length > 2 && !wordsA.has(cleanWord);

            if (isNew) {
              return (
                <span
                  key={idx}
                  className="inline-block px-1 py-0.5 mx-0.5 bg-emerald-100 text-emerald-900 rounded font-semibold border-b border-emerald-400"
                >
                  {word}{' '}
                </span>
              );
            }
            return <span key={idx}>{word} </span>;
          })}
        </div>
      </div>
    );
  };

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
            Compare Raw Copy, Uploaded Documents & Images (OCR), or Live Web URLs across two dedicated slots.
          </p>
        </div>

        {/* Brand indicator */}
        <div className="flex items-center gap-2 text-xs font-mono font-semibold px-3 py-1.5 rounded-xl bg-white border border-brand-sand text-brand-charcoal shadow-2xs">
          <span>Brand:</span>
          <span className="text-brand-ocean font-bold">{currentBrand.name}</span>
        </div>
      </div>

      {/* Dual Input Slots (Slot A and Slot B with Full 3 Ingestion Modes) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Slot A: Reference Asset */}
        <SlotCard
          slotId="A"
          roleLabel="Reference / Baseline"
          state={slotA}
          onChange={(updates) => setSlotA((prev) => ({ ...prev, ...updates }))}
          onExtractFile={handleExtractFileA}
          onScrapeUrl={handleScrapeUrlA}
        />

        {/* Slot B: Revised Asset */}
        <SlotCard
          slotId="B"
          roleLabel="Revised / Candidate Asset"
          state={slotB}
          onChange={(updates) => setSlotB((prev) => ({ ...prev, ...updates }))}
          onExtractFile={handleExtractFileB}
          onScrapeUrl={handleScrapeUrlB}
        />

        {/* Primary Action Button Bar */}
        <div className="md:col-span-2 flex items-center justify-between bg-brand-cream/60 p-4 rounded-2xl border border-brand-sand text-xs text-brand-charcoalMuted shadow-card-soft">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-brand-ocean" />
            <span>
              <strong>Hard Capacity Rule:</strong> Comparison workspace is strictly capped at maximum 2 items to
              guarantee deterministic delta scoring.
            </span>
          </div>

          <button
            onClick={handleRunComparison}
            disabled={loading || slotA.isExtracting || slotB.isExtracting}
            className="px-6 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white font-bold text-xs shadow-sm transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 active:scale-95"
            id="btn-run-dual-comparison"
          >
            <Sparkles className="w-4 h-4" />
            <span>{loading ? 'Evaluating Compliance Delta...' : 'Compare Assets (Slot A vs Slot B)'}</span>
          </button>
        </div>
      </div>

      {/* Comparison Metrics Delta Bar */}
      {comparisonResult && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Metric 1: Safety Score Delta */}
          <div className="bg-white p-4 rounded-xl border border-brand-sand shadow-card-soft">
            <span className="text-[11px] font-mono text-brand-charcoalMuted uppercase font-semibold">
              Compliance Adherence Delta
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
                {isPositiveDelta ? (
                  <TrendingUp className="w-3 h-3 mr-0.5" />
                ) : (
                  <TrendingDown className="w-3 h-3 mr-0.5" />
                )}
                {isPositiveDelta ? 'More Compliant' : 'Risk Drift'}
              </span>
            </div>
            <div className="text-[11px] text-brand-charcoalMuted mt-1">
              {metrics?.score_a}% (Slot A) → {metrics?.score_b}% (Slot B)
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
                {comparisonResult.new_risks.length > 0 ? 'Action Needed' : 'Zero Infractions'}
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

      {/* Comparative Violation Triage & Diff View */}
      {comparisonResult && (
        <div className="bg-white rounded-2xl border border-brand-sand shadow-card-soft overflow-hidden">
          <div className="px-6 py-4 border-b border-brand-sand bg-brand-cream/40 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-brand-ocean" />
              <h3 className="text-sm font-bold text-brand-charcoal">Comparative Violation Triage</h3>
            </div>

            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'all'
                    ? 'bg-brand-ocean text-white'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
              >
                All Violations (
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
              <button
                type="button"
                onClick={() => setActiveTab('diff')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all flex items-center gap-1 ${
                  activeTab === 'diff'
                    ? 'bg-brand-ocean text-white'
                    : 'text-brand-charcoal bg-brand-cream hover:bg-brand-sand/50'
                }`}
              >
                <Diff className="w-3.5 h-3.5" />
                <span>Text Diff</span>
              </button>
            </div>
          </div>

          <div className="p-6 space-y-3">
            {/* Visual Text Diff Tab */}
            {activeTab === 'diff' && renderVisualTextDiff()}

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
                      Flagged in Baseline Slot A: &ldquo;{f.flagged_text}&rdquo;
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
                      Introduced in Candidate Slot B: &ldquo;{f.flagged_text}&rdquo;
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
                      Remaining in Both: &ldquo;{f.flagged_text}&rdquo;
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
