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
  Award,
  Crown,
  FileSpreadsheet,
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
    } catch (err: any) {
      console.error('Comparison execution failed:', err);
      alert(err?.response?.data?.detail || 'Failed to execute comparative audit.');
    } finally {
      setLoading(false);
    }
  };

  // Auto-run comparison on mount with defaults
  useEffect(() => {
    handleRunComparison();
  }, []);

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
    <div className="space-y-6 animate-in fade-in duration-200 text-brand-charcoal">
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

      {/* Best Performing Variant Banner */}
      {comparisonResult && (
        <div className="bg-gradient-to-r from-emerald-500/15 via-emerald-500/5 to-transparent border border-emerald-300 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-card-soft animate-in fade-in duration-200">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold shadow-sm shrink-0">
              <Crown className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-900">
                  Optimal Variant Identified: {bestVariantTitle}
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  Recommended for Distribution
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                {comparisonResult.diff_summary}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="px-3 py-1 rounded-xl bg-white border border-emerald-200 text-xs font-mono font-bold text-emerald-800 shadow-2xs">
              Adherence: {metrics?.score_c ?? metrics?.score_b ?? 95}%
            </span>
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
