import React, { useState, useRef } from 'react';
import {
  FileText,
  UploadCloud,
  Globe,
  Loader2,
  File,
  CheckCircle2,
  X,
  Sparkles,
  ExternalLink,
  Eye,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';

export interface SlotState {
  sourceType: 'text' | 'file' | 'url';
  content: string;
  file: File | null;
  url: string;
  previewUrl: string | null;
  isExtracting: boolean;
  extractionMsg: string | null;
}

interface SlotCardProps {
  slotId: 'A' | 'B' | 'C';
  roleLabel: string;
  state: SlotState;
  onChange: (updates: Partial<SlotState>) => void;
  onExtractFile: (file: File) => Promise<void>;
  onScrapeUrl: (url: string) => Promise<void>;
  onReset?: () => void;
}

export const SlotCard: React.FC<SlotCardProps> = ({
  slotId,
  roleLabel,
  state,
  onChange,
  onExtractFile,
  onScrapeUrl,
  onReset,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const badgeBg =
    slotId === 'A'
      ? 'bg-brand-ocean text-white'
      : slotId === 'B'
      ? 'bg-brand-amber text-white'
      : 'bg-[#0D5C75] text-white';

  const badgeBorder =
    slotId === 'A'
      ? 'border-brand-oceanLight'
      : slotId === 'B'
      ? 'border-brand-amberHover'
      : 'border-teal-400';

  const handleFileDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      onChange({ file: droppedFile });
      await onExtractFile(droppedFile);
    }
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0];
      onChange({ file: selected });
      await onExtractFile(selected);
    }
  };

  const handleClearFile = () => {
    onChange({ file: null, previewUrl: null, content: '', extractionMsg: null });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="relative bg-white rounded-2xl p-5 border border-brand-sand shadow-card-soft flex flex-col space-y-4">
      {/* Pinned Absolute Top-Right Reset Button */}
      {onReset && (
        <button
          type="button"
          onClick={onReset}
          className="absolute top-4 right-4 flex items-center gap-1 text-xs text-slate-400 hover:text-rose-600 transition-colors py-1 px-2 rounded-lg hover:bg-rose-50 cursor-pointer z-10"
          title={`Reset Slot ${slotId}`}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="font-medium">Reset</span>
        </button>
      )}

      {/* Header */}
      <div className="border-b border-brand-sand pb-3 space-y-3">
        {/* Row 1: Slot Badge + Title & Subtitle with pr-20 to never collide with top-right Reset */}
        <div className="flex items-center gap-2.5 pr-20">
          <span
            className={`w-7 h-7 rounded-xl ${badgeBg} border ${badgeBorder} text-xs font-mono font-bold flex items-center justify-center shadow-2xs shrink-0`}
          >
            {slotId}
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-brand-charcoal truncate">
              Slot {slotId} ({roleLabel})
            </h2>
            <span className="text-[10px] font-mono text-brand-charcoalMuted block truncate">
              {state.sourceType === 'text'
                ? 'Direct Copy Input'
                : state.sourceType === 'file'
                ? 'Document / Creative Extraction'
                : 'Scraped Web URL'}
            </span>
          </div>
        </div>

        {/* Row 2: 3-Tab Ingestion Selector */}
        <div className="flex items-center p-1 rounded-xl bg-brand-cream border border-brand-sand text-xs font-semibold w-full">
          <button
            type="button"
            onClick={() => onChange({ sourceType: 'text' })}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg transition-all text-xs cursor-pointer ${
              state.sourceType === 'text'
                ? 'bg-brand-ocean text-white shadow-2xs font-bold'
                : 'text-brand-charcoalMuted hover:text-brand-charcoal'
            }`}
            title="Raw Copy / Text Input"
          >
            <FileText className="w-3.5 h-3.5 shrink-0" />
            <span>Raw Copy</span>
          </button>

          <button
            type="button"
            onClick={() => onChange({ sourceType: 'file' })}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg transition-all text-xs cursor-pointer ${
              state.sourceType === 'file'
                ? 'bg-brand-ocean text-white shadow-2xs font-bold'
                : 'text-brand-charcoalMuted hover:text-brand-charcoal'
            }`}
            title="Upload Document or Creative"
          >
            <UploadCloud className="w-3.5 h-3.5 shrink-0" />
            <span>Upload</span>
          </button>

          <button
            type="button"
            onClick={() => onChange({ sourceType: 'url' })}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg transition-all text-xs cursor-pointer ${
              state.sourceType === 'url'
                ? 'bg-brand-ocean text-white shadow-2xs font-bold'
                : 'text-brand-charcoalMuted hover:text-brand-charcoal'
            }`}
            title="Live Webpage URL"
          >
            <Globe className="w-3.5 h-3.5 shrink-0" />
            <span>Live URL</span>
          </button>
        </div>
      </div>

      {/* Mode 1: Raw Copy / Text */}
      {state.sourceType === 'text' && (
        <div className="space-y-2 flex-1 flex flex-col">
          <div className="flex items-center justify-between text-xs text-brand-charcoalMuted">
            <span>Enter Campaign / Marketing Copy:</span>
            <span className="font-mono text-[10px]">
              {state.content.length} chars • {state.content.trim() ? state.content.trim().split(/\s+/).length : 0} words
            </span>
          </div>
          <textarea
            value={state.content}
            onChange={(e) => onChange({ content: e.target.value })}
            rows={6}
            placeholder={`Enter or paste marketing copy for Slot ${slotId}...`}
            className="w-full p-3 rounded-xl border border-brand-sand bg-[#FBF9F4] text-xs text-brand-charcoal focus:ring-1 focus:ring-brand-amber font-sans resize-none leading-relaxed flex-1"
          />
        </div>
      )}

      {/* Mode 2: Upload Document & Creative Extraction */}
      {state.sourceType === 'file' && (
        <div className="space-y-3 flex-1 flex flex-col">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,.pptx,.txt,.png,.jpg,.jpeg,.webp"
            onChange={handleFileInputChange}
            className="hidden"
          />

          {!state.file ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center space-y-2 flex-1 ${
                isDragging
                  ? 'border-brand-amber bg-brand-amber/10'
                  : 'border-brand-sand bg-[#FBF9F4] hover:bg-brand-cream hover:border-brand-ocean/40'
              }`}
            >
              <div className="w-10 h-10 rounded-xl bg-brand-oceanLight/15 text-brand-ocean flex items-center justify-center shadow-2xs">
                <UploadCloud className="w-5 h-5 text-brand-ocean" />
              </div>
              <div>
                <p className="text-xs font-bold text-brand-charcoal">
                  Click or drag file to extract copy
                </p>
                <p className="text-[11px] text-brand-charcoalMuted mt-0.5">
                  Images (JPG, PNG, WEBP), PDF, Word (.docx)
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3 flex-1 flex flex-col">
              {/* File Info Card */}
              <div className="p-3 rounded-xl bg-brand-cream/80 border border-brand-sand flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <div className="w-8 h-8 rounded-lg bg-brand-ocean text-white flex items-center justify-center font-bold text-xs shrink-0">
                    <File className="w-4 h-4" />
                  </div>
                  <div className="overflow-hidden">
                    <p className="font-bold text-brand-charcoal truncate">{state.file.name}</p>
                    <p className="text-[10px] font-mono text-brand-charcoalMuted">
                      {formatFileSize(state.file.size)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-[11px] font-semibold text-brand-ocean hover:underline cursor-pointer"
                  >
                    Replace
                  </button>
                  <button
                    type="button"
                    onClick={handleClearFile}
                    className="p-1 text-brand-charcoalMuted hover:text-red-600 rounded"
                    title="Remove File"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Preview Thumbnail for Images */}
              {state.previewUrl && (
                <div className="relative rounded-xl border border-brand-sand overflow-hidden max-h-36 bg-slate-900 flex items-center justify-center">
                  <img
                    src={state.previewUrl}
                    alt="Uploaded Asset Preview"
                    className="object-contain max-h-36 w-full"
                  />
                  <span className="absolute bottom-1.5 right-1.5 px-2 py-0.5 rounded text-[10px] font-mono bg-black/70 text-white font-semibold">
                    Visual Creative Preview
                  </span>
                </div>
              )}

              {/* Extraction Loader */}
              {state.isExtracting && (
                <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-center gap-3 text-xs text-blue-900">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-700 shrink-0" />
                  <span className="font-mono text-[11px]">
                    {state.extractionMsg || 'Extracting text content and running OCR...'}
                  </span>
                </div>
              )}

              {/* Extracted Text Box */}
              {!state.isExtracting && (
                <div className="space-y-1.5 flex-1 flex flex-col">
                  <div className="flex items-center justify-between text-[11px] text-brand-charcoalMuted font-mono">
                    <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      Extracted Text Content
                    </span>
                    <span>{state.content.length} chars</span>
                  </div>
                  <textarea
                    value={state.content}
                    onChange={(e) => onChange({ content: e.target.value })}
                    rows={4}
                    placeholder="Extracted copy will appear here for review..."
                    className="w-full p-2.5 rounded-xl border border-brand-sand bg-[#FBF9F4] text-xs font-mono text-brand-charcoal resize-none leading-relaxed flex-1 focus:ring-1 focus:ring-brand-amber"
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Mode 3: Live URL / Web Scraping */}
      {state.sourceType === 'url' && (
        <div className="space-y-3 flex-1 flex flex-col">
          <div className="space-y-1.5">
            <label className="text-xs text-brand-charcoalMuted">Public Webpage URL:</label>
            <div className="flex gap-2">
              <input
                type="url"
                value={state.url}
                onChange={(e) => onChange({ url: e.target.value })}
                placeholder="https://example.com/pricing or landing page..."
                className="flex-1 px-3 py-2 text-xs rounded-xl border border-brand-sand bg-[#FBF9F4] text-brand-charcoal font-mono focus:ring-1 focus:ring-brand-amber"
              />
              <button
                type="button"
                onClick={() => onScrapeUrl(state.url)}
                disabled={!state.url.trim() || state.isExtracting}
                className="px-3.5 py-2 rounded-xl bg-brand-ocean hover:bg-brand-oceanDark text-white text-xs font-bold transition-all shadow-2xs flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shrink-0"
              >
                {state.isExtracting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Globe className="w-3.5 h-3.5" />
                )}
                <span>Fetch</span>
              </button>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="flex items-center gap-2 text-[10px] font-mono text-brand-charcoalMuted">
            <span>Presets:</span>
            <button
              type="button"
              onClick={() => {
                onChange({ url: 'https://example.com/' });
                onScrapeUrl('https://example.com/');
              }}
              className="text-brand-ocean hover:underline font-semibold"
            >
              example.com
            </button>
            <span>•</span>
            <button
              type="button"
              onClick={() => {
                onChange({ url: 'https://site-example.com/' });
                onScrapeUrl('https://site-example.com/');
              }}
              className="text-brand-ocean hover:underline font-semibold"
            >
              site-example.com
            </button>
          </div>

          {/* Scrape Status / Loader */}
          {state.isExtracting && (
            <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 flex items-center gap-2.5 text-xs text-blue-900 font-mono">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-700 shrink-0" />
              <span>Fetching URL through SSRF-protected scraper...</span>
            </div>
          )}

          {/* Scraped Content Preview */}
          {!state.isExtracting && (
            <div className="space-y-1.5 flex-1 flex flex-col">
              <div className="flex items-center justify-between text-[11px] text-brand-charcoalMuted font-mono">
                <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Scraped Webpage Content
                </span>
                <span>{state.content.length} chars</span>
              </div>
              <textarea
                value={state.content}
                onChange={(e) => onChange({ content: e.target.value })}
                rows={4}
                placeholder="Scraped web copy will appear here for inspection..."
                className="w-full p-2.5 rounded-xl border border-brand-sand bg-[#FBF9F4] text-xs font-mono text-brand-charcoal resize-none leading-relaxed flex-1 focus:ring-1 focus:ring-brand-amber"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SlotCard;

