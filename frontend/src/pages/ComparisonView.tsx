import React, { useState, useEffect } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
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
  Award,
  Crown,
  FileSpreadsheet,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { reviewsApi } from '../api/reviews';
import { historyApi } from '../api/history';
import { DualComparisonResponse, Finding } from '../types';
import { SlotCard, SlotState } from '../components/comparison/SlotCard';

export const ComparisonView: React.FC = () => {
  const { currentBrand } = useApp();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const historyIdParam = searchParams.get('history_id');
  const restoredSessionState = (location.state as any)?.restoreSession;
  const [saveToast, setSaveToast] = useState<string | null>(null);

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

  // Slot B State (Campaign Iteration 1 / Test Copy)
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

  // Slot C State (Campaign Iteration 2 / Final Variant)
  const [slotC, setSlotC] = useState<SlotState>({
    sourceType: 'text',
    content:
      'AstraForge Enterprise Cloud: Certified high-availability infrastructure. Rated 99.99% uptime based on independently verified SOC 2 Type II audit logs. Contact our enterprise advisory team.',
    file: null,
    url: '',
    previewUrl: null,
    isExtracting: false,
    extractionMsg: null,
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<DualComparisonResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'matrix' | 'all' | 'resolved' | 'new_risks' | 'diff'>('matrix');
  const [approvedVariant, setApprovedVariant] = useState<string | null>(null);

  const handleApproveVariant = (slotKey: string) => {
    setApprovedVariant(slotKey);
    const title =
      slotKey === 'slot_a'
        ? 'Slot A (Baseline)'
        : slotKey === 'slot_b'
        ? 'Slot B (Iteration 1)'
        : 'Slot C (Final Variant)';
    setSaveToast(`✓ ${title} approved for production publishing!`);
    setTimeout(() => setSaveToast(null), 3500);
  };

  const getStatusBadge = (score: number, status?: string) => {
    if (status === 'FULLY_COMPLIANT' || score >= 85) {
      return {
        label: 'Production Ready',
        color: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30',
        barColor: 'bg-emerald-400',
      };
    } else if (status === 'NEEDS_REVISION' || score >= 60) {
      return {
        label: 'Warning',
        color: 'bg-amber-500/20 text-amber-300 border-amber-400/30',
        barColor: 'bg-amber-400',
      };
    } else {
      return {
        label: 'High Risk',
        color: 'bg-rose-500/20 text-rose-300 border-rose-400/30',
        barColor: 'bg-rose-500',
      };
    }
  };

  // Reset Handlers for each slot
  const handleResetSlotA = () => {
    setSlotA({
      sourceType: 'text',
      content: '',
      file: null,
      url: '',
      previewUrl: null,
      isExtracting: false,
      extractionMsg: null,
    });
  };

  const handleResetSlotB = () => {
    setSlotB({
      sourceType: 'text',
      content: '',
      file: null,
      url: '',
      previewUrl: null,
      isExtracting: false,
      extractionMsg: null,
    });
  };

  const handleResetSlotC = () => {
    setSlotC({
      sourceType: 'text',
      content: '',
      file: null,
      url: '',
      previewUrl: null,
      isExtracting: false,
      extractionMsg: null,
    });
  };

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

  // Extraction Handlers for Slot C
  const handleExtractFileC = async (file: File) => {
    setSlotC((prev) => ({
      ...prev,
      isExtracting: true,
      extractionMsg: `Processing '${file.name}' via Pillow OCR & document parser...`,
    }));
    try {
      const res = await reviewsApi.extractFile(file);
      setSlotC((prev) => ({
        ...prev,
        content: res.extracted_text || '',
        previewUrl: res.preview_url || null,
        isExtracting: false,
        extractionMsg: null,
      }));
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to extract text from '${file.name}'.`);
      setSlotC((prev) => ({ ...prev, isExtracting: false, extractionMsg: null }));
    }
  };

  const handleScrapeUrlC = async (url: string) => {
    if (!url.trim()) return;
    setSlotC((prev) => ({
      ...prev,
      isExtracting: true,
      extractionMsg: 'Scraping webpage with SSRF sandbox...',
    }));
    try {
      const res = await reviewsApi.scrapeUrl(url, currentBrand.id);
      setSlotC((prev) => ({
        ...prev,
        content: res.extracted_text || '',
        previewUrl: res.image_preview_url || null,
        isExtracting: false,
        extractionMsg: null,
      }));
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to scrape URL '${url}'.`);
      setSlotC((prev) => ({ ...prev, isExtracting: false, extractionMsg: null }));
    }
  };

  // Run 3-Way Comparative Execution
  const handleRunComparison = async () => {
    const textA = slotA.content.trim();
    const textB = slotB.content.trim();
    const textC = slotC.content.trim();

    if (!textA && !textB && !textC) {
      alert('Please enter or extract copy in at least two slots to run comparative analysis.');
      return;
    }

    setLoading(true);
    try {
      const payload: any = {
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

      if (textC || slotC.file || slotC.url) {
        payload.slot_c = {
          source_type: slotC.sourceType,
          text_content: textC,
          file_name: slotC.file?.name,
          url: slotC.url,
        };
        payload.text_c = textC;
      }

      const res = await reviewsApi.compareReviews(payload);
      setComparisonResult(res);

      // Auto-save comparison to History
      try {
        const is3Way = Boolean(payload.slot_c);
        const title = `Multi-Variant Comparison (${is3Way ? '3 Variants' : 'Dual'})`;
        const winner = res.best_variant_title || 'Optimized Variant';
        const summary = `${winner} Winner • ${res.matrix?.length || 0} Dimensions Evaluated`;

        historyApi
          .saveHistory({
            session_type: is3Way ? 'THREE_WAY_COMPARISON' : 'DUAL_COMPARISON',
            title,
            summary,
            inputs_payload: {
              slot_a: {
                sourceType: slotA.sourceType,
                content: textA,
                url: slotA.url,
                fileName: slotA.file?.name,
              },
              slot_b: {
                sourceType: slotB.sourceType,
                content: textB,
                url: slotB.url,
                fileName: slotB.file?.name,
              },
              slot_c: payload.slot_c
                ? {
                    sourceType: slotC.sourceType,
                    content: textC,
                    url: slotC.url,
                    fileName: slotC.file?.name,
                  }
                : null,
            },
            results_payload: res,
            brand_id: currentBrand?.id || 1,
          })
          .catch((err) => console.debug('History comparison save notice:', err));

        setSaveToast('Saved to History');
        setTimeout(() => setSaveToast(null), 3500);
      } catch (err) {
        console.debug('History comparison save caught:', err);
      }
    } catch (err: any) {
      console.error('Comparison execution failed:', err);
      alert(err?.response?.data?.detail || 'Failed to execute comparative audit.');
    } finally {
      setLoading(false);
    }
  };

  const restoreComparisonSession = (detail: any) => {
    try {
      const inputs = detail.inputs_payload || {};
      const results = detail.results_payload || {};

      if (inputs.slot_a) {
        setSlotA((prev) => ({
          ...prev,
          sourceType: inputs.slot_a.sourceType || 'text',
          content: inputs.slot_a.content || '',
          url: inputs.slot_a.url || '',
          file: null,
        }));
      }
      if (inputs.slot_b) {
        setSlotB((prev) => ({
          ...prev,
          sourceType: inputs.slot_b.sourceType || 'text',
          content: inputs.slot_b.content || '',
          url: inputs.slot_b.url || '',
          file: null,
        }));
      }
      if (inputs.slot_c) {
        setSlotC((prev) => ({
          ...prev,
          sourceType: inputs.slot_c.sourceType || 'text',
          content: inputs.slot_c.content || '',
          url: inputs.slot_c.url || '',
          file: null,
        }));
      }

      if (results && (results.matrix || results.best_variant)) {
        setComparisonResult(results);
      }

      setSaveToast(`Restored: "${detail.title || 'Comparison'}"`);
      setTimeout(() => setSaveToast(null), 3500);
    } catch (e) {
      console.error('Failed to restore comparison session:', e);
    }
  };

  const loadComparisonHistoryById = async (historyId: string) => {
    setLoading(true);
    try {
      const detail = await historyApi.getHistoryDetail(historyId);
      restoreComparisonSession(detail);
    } catch (e) {
      console.error('Failed to load comparison history by id:', e);
      handleRunComparison();
    } finally {
      setLoading(false);
    }
  };

  // Auto-run comparison on mount with defaults only if not restoring from history
  useEffect(() => {
    if (restoredSessionState) {
      restoreComparisonSession(restoredSessionState);
    } else if (historyIdParam) {
      loadComparisonHistoryById(historyIdParam);
    } else {
      handleRunComparison();
    }
  }, [historyIdParam, restoredSessionState]);

  const metrics = comparisonResult?.metrics;
  const bestVariant = comparisonResult?.best_variant || 'slot_c';
  const bestVariantTitle = comparisonResult?.best_variant_title || 'Slot C';
  const matrix = comparisonResult?.matrix || [];

  // Text diff renderer
  const renderVisualTextDiff = () => {
    if (!comparisonResult) return null;
    const wordsA = new Set(
      comparisonResult.content_a
        .toLowerCase()
        .replace(/[^\w\s]/g, '')
        .split(/\s+/)
    );
    const targetContent = comparisonResult.content_c || comparisonResult.content_b || '';
    const targetWords = targetContent.split(/\s+/);

    return (
      <div className="p-4 rounded-xl bg-[#FBF9F4] border border-brand-sand leading-relaxed text-xs font-sans space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono text-brand-charcoalMuted border-b border-brand-sand pb-2">
          <span className="font-bold text-brand-charcoal">
            {comparisonResult.content_c ? 'Slot C (Final Candidate) Text Diff' : 'Slot B Text Diff'} vs Slot A Baseline
          </span>
          <span className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-emerald-700">
              <span className="w-2.5 h-2.5 rounded bg-emerald-100 border border-emerald-300 inline-block" />
              New / Optimized Wording
            </span>
            <span className="flex items-center gap-1 text-slate-700">
              <span className="w-2.5 h-2.5 rounded bg-white border border-slate-300 inline-block" />
              Retained Baseline
            </span>
          </span>
        </div>

        <div className="p-2 select-text leading-loose">
          {targetWords.map((word, idx) => {
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
    <div className="space-y-6 animate-in fade-in duration-200 text-brand-charcoal relative">
      {/* Toast Notification */}
      {saveToast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-oceanDark text-white shadow-lg border border-brand-oceanLight/30 text-xs font-medium animate-in fade-in slide-in-from-bottom-3 duration-200">
          <CheckCircle2 className="w-4 h-4 text-brand-amber shrink-0" />
          <span>{saveToast}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-brand-sand">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-brand-charcoal flex items-center gap-2">
              <Columns className="w-6 h-6 text-brand-ocean" />
              3-Way Multi-Asset & Version Comparison
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-brand-ocean text-white border border-brand-oceanLight">
              3 Slots Active (A vs B vs C)
            </span>
          </div>
          <p className="text-xs text-brand-charcoalMuted mt-1">
            Compare Raw Copy, Document/Image Uploads (OCR), and Live Web URLs side-by-side across three concurrent variations.
          </p>
        </div>

        {/* Brand pill */}
        <div className="flex items-center gap-2 text-xs font-mono font-semibold px-3 py-1.5 rounded-xl bg-white border border-brand-sand text-brand-charcoal shadow-2xs">
          <span>Active Brand:</span>
          <span className="text-brand-ocean font-bold">{currentBrand.name}</span>
        </div>
      </div>

      {/* 3-Column Responsive Grid Layout (Slot A, Slot B, Slot C) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Slot A: Baseline Asset */}
        <SlotCard
          slotId="A"
          roleLabel="Baseline / Original"
          state={slotA}
          onChange={(updates) => setSlotA((prev) => ({ ...prev, ...updates }))}
          onExtractFile={handleExtractFileA}
          onScrapeUrl={handleScrapeUrlA}
          onReset={handleResetSlotA}
          isWinner={comparisonResult?.best_variant === 'slot_a'}
          isApproved={approvedVariant === 'slot_a'}
          onApprove={() => handleApproveVariant('slot_a')}
        />

        {/* Slot B: Campaign Iteration 1 */}
        <SlotCard
          slotId="B"
          roleLabel="Iteration 1 / Test Copy"
          state={slotB}
          onChange={(updates) => setSlotB((prev) => ({ ...prev, ...updates }))}
          onExtractFile={handleExtractFileB}
          onScrapeUrl={handleScrapeUrlB}
          onReset={handleResetSlotB}
          isWinner={comparisonResult?.best_variant === 'slot_b'}
          isApproved={approvedVariant === 'slot_b'}
          onApprove={() => handleApproveVariant('slot_b')}
        />

        {/* Slot C: Campaign Iteration 2 / Final Variant */}
        <SlotCard
          slotId="C"
          roleLabel="Iteration 2 / Final Variant"
          state={slotC}
          onChange={(updates) => setSlotC((prev) => ({ ...prev, ...updates }))}
          onExtractFile={handleExtractFileC}
          onScrapeUrl={handleScrapeUrlC}
          onReset={handleResetSlotC}
          isWinner={comparisonResult?.best_variant === 'slot_c'}
          isApproved={approvedVariant === 'slot_c'}
          onApprove={() => handleApproveVariant('slot_c')}
        />

        {/* Primary Action Button Bar */}
        <div className="lg:col-span-3 flex flex-col sm:flex-row items-center justify-between bg-brand-cream/60 p-4 rounded-2xl border border-brand-sand text-xs text-brand-charcoalMuted shadow-card-soft gap-3">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-brand-ocean shrink-0" />
            <span>
              <strong>Tri-Variant Auditing:</strong> Evaluates all three slots against active FAISS brand guidelines
              concurrently to determine the optimal compliance iteration.
            </span>
          </div>

          <button
            onClick={handleRunComparison}
            disabled={loading || slotA.isExtracting || slotB.isExtracting || slotC.isExtracting}
            className="px-6 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white font-bold text-xs shadow-sm transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 active:scale-95 shrink-0"
            id="btn-run-3way-comparison"
          >
            <Sparkles className="w-4 h-4" />
            <span>{loading ? 'Evaluating 3 Variations...' : 'Run 3-Way Comparison (Slot A vs B vs C)'}</span>
          </button>
        </div>
      </div>

      {/* Executive Winner & Decision Banner */}
      {comparisonResult && (
        <div className="bg-gradient-to-br from-[#0B3C49] via-[#072730] to-[#04161C] border border-teal-800/80 rounded-2xl p-6 text-white shadow-xl space-y-6 animate-in fade-in duration-200">
          {/* Header Row: Glowing Warm Amber Badge + Action Button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-teal-800/60">
            <div className="space-y-1.5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/40 text-xs font-bold font-mono shadow-sm">
                <Crown className="w-4 h-4 text-amber-400 animate-pulse" />
                <span>🏆 Recommended Best Variant: {bestVariantTitle}</span>
              </div>
              <h2 className="text-lg font-extrabold tracking-tight text-white flex items-center gap-2">
                <span>Executive Guideline Decision Engine</span>
              </h2>
            </div>

            {/* Action Button: Approve Variant for Publishing */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => handleApproveVariant(bestVariant)}
                className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shadow-sm active:scale-95 ${
                  approvedVariant === bestVariant
                    ? 'bg-emerald-600 text-white'
                    : 'bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600 hover:from-amber-500 hover:to-amber-700 text-slate-950 font-black shadow-lg shadow-amber-500/25'
                }`}
                id="btn-approve-variant-publishing"
              >
                {approvedVariant === bestVariant ? (
                  <>
                    <Check className="w-4 h-4 text-white" />
                    <span>Variant Approved for Publishing</span>
                  </>
                ) : (
                  <>
                    <Award className="w-4 h-4" />
                    <span>Approve Variant for Publishing</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Clear Score Progress Meters for Each Variant */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Slot A Progress Meter */}
            {(() => {
              const scoreA = metrics?.score_a ?? 35;
              const evalA = comparisonResult.slot_evaluations?.slot_a;
              const statusA = getStatusBadge(scoreA, evalA?.status);
              return (
                <div
                  className={`p-4 rounded-xl border bg-white/5 backdrop-blur-xs space-y-2.5 ${
                    bestVariant === 'slot_a' ? 'border-amber-400/60 bg-amber-500/10' : 'border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-200">Slot A (Baseline)</span>
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border ${statusA.color}`}>
                      {scoreA}% - {statusA.label}
                    </span>
                  </div>
                  {/* Progress Bar */}
                  <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${statusA.barColor}`}
                      style={{ width: `${Math.max(4, scoreA)}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>{evalA?.violations_count ?? comparisonResult.metrics.violations_count_a} violation(s)</span>
                    {evalA?.critical_issues?.[0] && (
                      <span className="truncate max-w-[140px] text-rose-300" title={evalA.critical_issues[0]}>
                        {evalA.critical_issues[0]}
                      </span>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Slot B Progress Meter */}
            {(() => {
              const scoreB = metrics?.score_b ?? 75;
              const evalB = comparisonResult.slot_evaluations?.slot_b;
              const statusB = getStatusBadge(scoreB, evalB?.status);
              return (
                <div
                  className={`p-4 rounded-xl border bg-white/5 backdrop-blur-xs space-y-2.5 ${
                    bestVariant === 'slot_b' ? 'border-amber-400/60 bg-amber-500/10' : 'border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-200">Slot B (Iteration 1)</span>
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border ${statusB.color}`}>
                      {scoreB}% - {statusB.label}
                    </span>
                  </div>
                  {/* Progress Bar */}
                  <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${statusB.barColor}`}
                      style={{ width: `${Math.max(4, scoreB)}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>{evalB?.violations_count ?? comparisonResult.metrics.violations_count_b} violation(s)</span>
                    {evalB?.critical_issues?.[0] && (
                      <span className="truncate max-w-[140px] text-amber-300" title={evalB.critical_issues[0]}>
                        {evalB.critical_issues[0]}
                      </span>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Slot C Progress Meter */}
            {(() => {
              const scoreC = metrics?.score_c ?? 98;
              const evalC = comparisonResult.slot_evaluations?.slot_c;
              const statusC = getStatusBadge(scoreC, evalC?.status);
              return (
                <div
                  className={`p-4 rounded-xl border bg-white/5 backdrop-blur-xs space-y-2.5 ${
                    bestVariant === 'slot_c'
                      ? 'border-emerald-400/60 bg-emerald-500/10 ring-1 ring-emerald-400/30'
                      : 'border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-200">Slot C (Final Variant)</span>
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border ${statusC.color}`}>
                      {scoreC}% - {statusC.label}
                    </span>
                  </div>
                  {/* Progress Bar */}
                  <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${statusC.barColor}`}
                      style={{ width: `${Math.max(4, scoreC)}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>{evalC?.violations_count ?? (comparisonResult.metrics.violations_count_c ?? 0)} violation(s)</span>
                    <span className="text-emerald-300 font-semibold font-mono">
                      {evalC?.status === 'FULLY_COMPLIANT' ? '✓ Production Ready' : 'Evaluated'}
                    </span>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* AI Reasoning Box */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4.5 space-y-2.5">
            <div className="flex items-center gap-2 text-amber-300 font-bold text-xs uppercase tracking-wider font-mono">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Why {bestVariantTitle} Won:</span>
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-sans">
              {comparisonResult.executive_verdict ||
                `Evaluated strictly against ${currentBrand.name} Brand Safety Policy, ${bestVariantTitle} resolved all prohibited promotional phrases and adheres strictly to substantiation rules.`}
            </p>

            {/* Key Improvements Noted */}
            {comparisonResult.key_improvements_noted && comparisonResult.key_improvements_noted.length > 0 && (
              <div className="pt-2 border-t border-white/10 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-300">
                {comparisonResult.key_improvements_noted.map((imp, idx) => (
                  <div key={idx} className="flex items-center gap-2 font-mono text-[11px]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{imp}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3-Way Comparative Diff & Metrics UI */}
      {comparisonResult && (
        <div className="bg-white rounded-2xl border border-brand-sand shadow-card-soft overflow-hidden">
          {/* Tabs bar */}
          <div className="px-6 py-4 border-b border-brand-sand bg-brand-cream/40 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-brand-ocean" />
              <h3 className="text-sm font-bold text-brand-charcoal">3-Way Differential Analysis</h3>
            </div>

            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => setActiveTab('matrix')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all flex items-center gap-1 ${
                  activeTab === 'matrix'
                    ? 'bg-brand-ocean text-white shadow-2xs'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Comparison Matrix</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'all'
                    ? 'bg-brand-ocean text-white shadow-2xs'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
              >
                All Findings
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('resolved')}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'resolved'
                    ? 'bg-emerald-600 text-white shadow-2xs'
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
                    ? 'bg-red-600 text-white shadow-2xs'
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
                    ? 'bg-brand-ocean text-white shadow-2xs'
                    : 'text-brand-charcoal bg-brand-cream hover:bg-brand-sand/50'
                }`}
              >
                <Diff className="w-3.5 h-3.5" />
                <span>Text Diff</span>
              </button>
            </div>
          </div>

          <div className="p-6">
            {/* Tab 1: Comparison Matrix Table (Side-by-side columns: Attribute | Slot A | Slot B | Slot C) */}
            {activeTab === 'matrix' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-brand-sand bg-brand-cream/60 text-brand-charcoal font-bold">
                      <th className="py-3 px-4 uppercase text-[10px] font-mono tracking-wider">
                        Attribute / Metric
                      </th>
                      <th className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="w-5 h-5 rounded-md bg-brand-ocean text-white font-mono text-[10px] flex items-center justify-center font-bold">
                            A
                          </span>
                          <span>Slot A (Baseline)</span>
                        </div>
                      </th>
                      <th className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="w-5 h-5 rounded-md bg-brand-amber text-white font-mono text-[10px] flex items-center justify-center font-bold">
                            B
                          </span>
                          <span>Slot B (Iteration 1)</span>
                        </div>
                      </th>
                      <th className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="w-5 h-5 rounded-md bg-[#0D5C75] text-white font-mono text-[10px] flex items-center justify-center font-bold">
                            C
                          </span>
                          <span>Slot C (Final Variant)</span>
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-sand/60">
                    {matrix.map((row, idx) => {
                      const isBestA = row.best === 'slot_a';
                      const isBestB = row.best === 'slot_b';
                      const isBestC = row.best === 'slot_c';

                      return (
                        <tr key={idx} className="hover:bg-brand-cream/30 transition-colors">
                          <td className="py-3.5 px-4 font-semibold text-brand-charcoal">
                            {row.metric}
                          </td>
                          <td className="py-3.5 px-4 font-mono">
                            <span
                              className={`px-2 py-0.5 rounded-lg ${
                                isBestA
                                  ? 'bg-emerald-50 text-emerald-800 font-bold border border-emerald-200'
                                  : 'text-brand-charcoal'
                              }`}
                            >
                              {row.slot_a}
                              {isBestA && ' ★'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-mono">
                            <span
                              className={`px-2 py-0.5 rounded-lg ${
                                isBestB
                                  ? 'bg-emerald-50 text-emerald-800 font-bold border border-emerald-200'
                                  : 'text-brand-charcoal'
                              }`}
                            >
                              {row.slot_b}
                              {isBestB && ' ★'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-mono">
                            <span
                              className={`px-2 py-0.5 rounded-lg ${
                                isBestC
                                  ? 'bg-emerald-50 text-emerald-800 font-bold border border-emerald-200'
                                  : 'text-brand-charcoal'
                              }`}
                            >
                              {row.slot_c}
                              {isBestC && ' ★'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab 2: Visual Text Diff */}
            {activeTab === 'diff' && renderVisualTextDiff()}

            {/* Tab 3: Resolved Violations */}
            {(activeTab === 'all' || activeTab === 'resolved') && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-900 mb-2">
                  Remediated Baseline Issues ({comparisonResult.resolved_violations.length})
                </h4>
                {comparisonResult.resolved_violations.length === 0 ? (
                  <p className="text-xs text-brand-charcoalMuted italic">No baseline violations resolved.</p>
                ) : (
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
                          Flagged in Slot A: &ldquo;{f.flagged_text}&rdquo;
                        </p>
                        <p className="text-emerald-700 text-[11px]">{f.explanation}</p>
                      </div>
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 4: Newly Introduced Risks */}
            {(activeTab === 'all' || activeTab === 'new_risks') && (
              <div className="space-y-3 pt-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-red-900 mb-2">
                  Newly Introduced Risks ({comparisonResult.new_risks.length})
                </h4>
                {comparisonResult.new_risks.length === 0 ? (
                  <p className="text-xs text-emerald-700 font-medium flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Zero new risk infractions introduced across variants.
                  </p>
                ) : (
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
                          Introduced in Variant: &ldquo;{f.flagged_text}&rdquo;
                        </p>
                        <p className="text-red-700 text-[11px]">{f.explanation}</p>
                      </div>
                      <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ComparisonView;
