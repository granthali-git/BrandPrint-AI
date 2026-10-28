import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  FileText,
  UploadCloud,
  Globe,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Loader2,
  FileCheck,
  ShieldCheck,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { reviewsApi } from '../../api/reviews';
import { apiClient, BASE_URL } from '../../api/client';

export const NewReviewModal: React.FC = () => {
  const { isNewReviewOpen, closeNewReview, currentBrand } = useApp();
  const navigate = useNavigate();

  const [contentType, setContentType] = useState<'text' | 'file' | 'url'>('text');
  const [rawContent, setRawContent] = useState('');
  const [url, setUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendWarming, setBackendWarming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successInfo, setSuccessInfo] = useState<string | null>(null);
  const [progressIndex, setProgressIndex] = useState(0);

  const PROGRESS_MESSAGES = [
    "Analyzing image visual & text copy...",
    "Grounding against brand guidelines with Gemini...",
    "Cross-referencing deterministic policy rules...",
    "Validating semantic citations and fix variations...",
  ];

  // Preemptive health ping on modal mount to wake sleeping Render instance early
  useEffect(() => {
    if (!isNewReviewOpen) return;
    apiClient.get('/health', { timeout: 15000 }).catch(() => {
      // Intentionally silent: first ping wakes up Render container if sleeping
    });
  }, [isNewReviewOpen]);

  // Rotate friendly progress indicators while pipeline processes
  useEffect(() => {
    if (!isSubmitting) {
      setProgressIndex(0);
      return;
    }
    const timer = setInterval(() => {
      setProgressIndex((prev) => (prev + 1) % PROGRESS_MESSAGES.length);
    }, 2800);
    return () => clearInterval(timer);
  }, [isSubmitting]);

  if (!isNewReviewOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const executeSubmission = async (retryCount = 0) => {
    setErrorMsg(null);
    setSuccessInfo(null);

    // Validation
    if (contentType === 'text' && !rawContent.trim()) {
      setErrorMsg('Please input marketing copy, headline, or campaign content to evaluate.');
      return;
    }
    if (contentType === 'url' && !url.trim()) {
      setErrorMsg('Please enter a valid URL (e.g., https://example.com/press-release).');
      return;
    }
    if (contentType === 'file' && !selectedFile) {
      setErrorMsg('Please upload a document or creative asset (PDF, DOCX, or Image).');
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append('brand_id', String(currentBrand.id));
      formData.append('content_type', contentType);

      if (contentType === 'text') {
        formData.append('raw_content', rawContent);
      } else if (contentType === 'url') {
        formData.append('url', url);
      } else if (contentType === 'file' && selectedFile) {
        formData.append('file', selectedFile);
      }

      const result = await reviewsApi.submitReview(formData);

      setSuccessInfo(
        `Audit complete! Detected ${result.total_findings || 0} compliance findings.`
      );

      setTimeout(() => {
        closeNewReview();
        setRawContent('');
        setUrl('');
        setSelectedFile(null);
        navigate(`/studio?id=${result.submission.id}`);
      }, 1000);
    } catch (err: any) {
      console.error('Review submission error:', err);
      const errText = err?.message || '';
      const isSleepWake =
        errText.toLowerCase().includes('spinning up') ||
        errText.toLowerCase().includes('network error') ||
        errText.toLowerCase().includes('unreachable') ||
        errText.toLowerCase().includes('unable to connect') ||
        errText.toLowerCase().includes('failed to fetch') ||
        err?.response?.status === 502 ||
        err?.response?.status === 503 ||
        err?.response?.status === 504 ||
        err?.code === 'ECONNABORTED';

      // If backend was sleeping and we haven't retried yet, trigger automatic wake-and-retry
      if (isSleepWake && retryCount === 0) {
        setBackendWarming(true);
        let awake = false;
        // Probe health up to 18 times (~45s) while Render container spins up from cold sleep
        for (let i = 0; i < 18; i++) {
          await new Promise((resolve) => setTimeout(resolve, 2500));
          try {
            const probe = await apiClient.get('/health', { timeout: 6000 });
            if (probe.status === 200) {
              awake = true;
              break;
            }
          } catch {
            // Still booting
          }
        }
        setBackendWarming(false);
        if (awake) {
          return executeSubmission(1);
        }
      }

      setBackendWarming(false);
      const rawBase = import.meta.env.VITE_API_BASE_URL || 'https://brandprint-ai-backend.onrender.com';
      let baseUrl = rawBase.replace(/\/+$/, '');
      if (typeof window !== 'undefined' && window.location.protocol === 'https:' && baseUrl.startsWith('http://') && !baseUrl.includes('localhost')) {
        baseUrl = baseUrl.replace('http://', 'https://');
      }
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        `Failed to process review. Ensure backend is running at ${baseUrl}.`;
      setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSubmission(0);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-oceanDark/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white border border-brand-sand shadow-card-elevated p-6 sm:p-7 text-brand-charcoal max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-5 border-b border-brand-sand">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-amber/15 border border-brand-amber/30 flex items-center justify-center text-brand-amber">
              <Sparkles className="w-5 h-5 text-brand-amber" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-brand-charcoal flex items-center gap-2">
                Initiate Compliance Review
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-brand-oceanLight/10 text-brand-ocean border border-brand-ocean/20">
                  AI Pipeline
                </span>
              </h2>
              <p className="text-xs text-brand-charcoalMuted">
                Evaluating against{' '}
                <span className="font-semibold text-brand-charcoal">{currentBrand.name}</span> guidelines
              </p>
            </div>
          </div>
          <button
            onClick={closeNewReview}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          {/* Content Type Selector */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-brand-charcoalMuted font-bold mb-2">
              Ingestion Source
            </label>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setContentType('text')}
                className={`flex flex-col items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-semibold transition-all ${
                  contentType === 'text'
                    ? 'bg-brand-oceanLight/10 border-brand-amber text-brand-ocean shadow-sm'
                    : 'bg-brand-cream border-brand-sand text-brand-charcoalMuted hover:border-brand-sand hover:text-brand-charcoal'
                }`}
              >
                <FileText className={`w-5 h-5 ${contentType === 'text' ? 'text-brand-amber' : ''}`} />
                <span>Raw Copy / Text</span>
              </button>

              <button
                type="button"
                onClick={() => setContentType('file')}
                className={`flex flex-col items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-semibold transition-all ${
                  contentType === 'file'
                    ? 'bg-brand-oceanLight/10 border-brand-amber text-brand-ocean shadow-sm'
                    : 'bg-brand-cream border-brand-sand text-brand-charcoalMuted hover:border-brand-sand hover:text-brand-charcoal'
                }`}
              >
                <UploadCloud className={`w-5 h-5 ${contentType === 'file' ? 'text-brand-amber' : ''}`} />
                <span>Upload Document</span>
              </button>

              <button
                type="button"
                onClick={() => setContentType('url')}
                className={`flex flex-col items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-semibold transition-all ${
                  contentType === 'url'
                    ? 'bg-brand-oceanLight/10 border-brand-amber text-brand-ocean shadow-sm'
                    : 'bg-brand-cream border-brand-sand text-brand-charcoalMuted hover:border-brand-sand hover:text-brand-charcoal'
                }`}
              >
                <Globe className={`w-5 h-5 ${contentType === 'url' ? 'text-brand-amber' : ''}`} />
                <span>Live URL / Web</span>
              </button>
            </div>
          </div>

          {/* Conditional Inputs */}
          {contentType === 'text' && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-mono uppercase tracking-wider text-brand-charcoalMuted font-bold">
                  Marketing Copy / Creative Content
                </label>
                <button
                  type="button"
                  onClick={() =>
                    setRawContent(
                      'Buy AstraForge Cloud today! We are the cheapest solution and guaranteed #1 platform on the market with 100% infallible uptime. Call now to claim 50% discount.'
                    )
                  }
                  className="text-[11px] text-brand-amber hover:text-brand-amberHover font-mono font-semibold flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3" />
                  Load Sample Copy (With Claims)
                </button>
              </div>
              <textarea
                value={rawContent}
                onChange={(e) => setRawContent(e.target.value)}
                placeholder="Paste marketing copy, press release drafts, advertising headlines, or product claims here..."
                rows={5}
                className="w-full rounded-xl bg-brand-cream border border-brand-sand p-3.5 text-xs text-brand-charcoal placeholder-brand-charcoalMuted focus:outline-none focus:ring-1 focus:ring-brand-amber font-sans"
              />
            </div>
          )}

          {contentType === 'file' && (
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-brand-charcoalMuted font-bold mb-1.5">
                Document / Asset File
              </label>
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                className="border-2 border-dashed border-brand-sand hover:border-brand-amber rounded-xl p-6 text-center bg-brand-cream transition-colors cursor-pointer group"
                onClick={() => document.getElementById('file-upload-input')?.click()}
              >
                <input
                  id="file-upload-input"
                  type="file"
                  accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
                  onChange={handleFileChange}
                  className="hidden"
                />
                {selectedFile ? (
                  <div className="flex items-center justify-center gap-3 text-brand-ocean">
                    <FileCheck className="w-8 h-8 text-brand-amber" />
                    <div className="text-left">
                      <div className="text-sm font-semibold text-brand-charcoal">{selectedFile.name}</div>
                      <div className="text-xs text-brand-charcoalMuted font-mono">
                        {(selectedFile.size / 1024).toFixed(1)} KB • Ready for extraction
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    <div className="w-10 h-10 mx-auto rounded-full bg-white border border-brand-sand flex items-center justify-center text-brand-amber">
                      <UploadCloud className="w-5 h-5" />
                    </div>
                    <div className="text-xs text-brand-charcoal">
                      <span className="font-semibold text-brand-amber">Click to upload</span> or drag and drop
                    </div>
                    <div className="text-[11px] text-brand-charcoalMuted font-mono">
                      PDF, DOCX, TXT, PNG, JPG, or WEBP (Up to 25MB)
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {contentType === 'url' && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-mono uppercase tracking-wider text-brand-charcoalMuted font-bold">
                  Target URL (SSRF Safe)
                </label>
                <div className="flex items-center gap-1.5 text-[11px] font-mono">
                  <span className="text-brand-charcoalMuted">Quick Fill:</span>
                  <button
                    type="button"
                    onClick={() => setUrl('https://example.com/')}
                    className="text-brand-amber hover:underline font-semibold cursor-pointer"
                  >
                    example.com
                  </button>
                </div>
              </div>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/landing-page"
                className="w-full rounded-xl bg-brand-cream border border-brand-sand px-3.5 py-2.5 text-xs text-brand-charcoal placeholder-brand-charcoalMuted focus:outline-none focus:ring-1 focus:ring-brand-amber font-mono"
              />
              <p className="mt-1.5 text-[11px] text-brand-charcoalMuted">
                BrandPrint AI extracts readable HTML, checks image contrast, and scans all claims.
              </p>
            </div>
          )}

          {/* Cold start auto-wake indicator */}
          {backendWarming && (
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-300 text-xs text-brand-charcoal flex items-center gap-3 animate-in fade-in duration-200">
              <Loader2 className="w-5 h-5 text-brand-amber animate-spin shrink-0" />
              <div className="flex-1">
                <div className="font-semibold text-brand-charcoal flex items-center gap-2">
                  <span>Waking up cloud backend (Render spin-up)</span>
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-200/70 text-amber-900">
                    Auto-Retrying
                  </span>
                </div>
                <p className="text-[11px] text-brand-charcoalMuted mt-0.5">
                  The Render free instance is waking up from sleep (~20-25s). Your audit will dispatch automatically once the connection is ready.
                </p>
              </div>
            </div>
          )}

          {/* Friendly Animated Progress Indicator */}
          {isSubmitting && !backendWarming && (
            <div className="p-3.5 rounded-xl bg-brand-oceanLight/10 border border-brand-amber/40 text-xs text-brand-ocean flex items-center gap-3 animate-in fade-in duration-200">
              <Loader2 className="w-5 h-5 text-brand-amber animate-spin shrink-0" />
              <div className="flex-1">
                <div className="font-semibold text-brand-charcoal flex items-center gap-2">
                  <span>Executing Compliance Audit</span>
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-brand-amber/20 text-brand-amberHover">
                    Step {progressIndex + 1}/4
                  </span>
                </div>
                <p className="text-[11px] text-brand-charcoalMuted mt-0.5 animate-pulse font-medium">
                  {PROGRESS_MESSAGES[progressIndex]}
                </p>
              </div>
            </div>
          )}

          {/* Feedback Messages */}
          {errorMsg && (
            <div className="flex flex-col gap-2.5 p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 animate-in fade-in duration-150">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
                <div className="flex-1">
                  <span className="font-semibold text-red-900 block">Service Notice:</span>
                  <span className="mt-0.5 block leading-relaxed">{errorMsg}</span>
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-red-200/60">
                <button
                  type="button"
                  onClick={() => executeSubmission(0)}
                  disabled={isSubmitting || backendWarming}
                  className="px-3.5 py-1.5 rounded-lg bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50 active:scale-95"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Retry Audit Now
                </button>
              </div>
            </div>
          )}

          {successInfo && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-700">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>{successInfo}</span>
            </div>
          )}

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-brand-sand">
            <button
              type="button"
              onClick={closeNewReview}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-medium text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              id="btn-run-compliance-audit"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold shadow-sm transition-all duration-150 active:scale-95 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span className="animate-pulse">{PROGRESS_MESSAGES[progressIndex]}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Run Compliance Audit</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewReviewModal;
