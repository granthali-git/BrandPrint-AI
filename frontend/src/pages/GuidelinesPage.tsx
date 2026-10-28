import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Plus,
  UploadCloud,
  Search,
  CheckCircle,
  FileText,
  Loader2,
  X,
  Globe,
  Sparkles,
  Layers,
  Check,
  Edit2,
  Trash2,
  CheckSquare,
  Square,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Image as ImageIcon,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { guidelinesApi } from '../api/guidelines';
import { GuidelineRule, RuleCategory } from '../types';

export const GuidelinesPage: React.FC = () => {
  const { currentBrand } = useApp();
  const [rules, setRules] = useState<GuidelineRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Top Ingestion Center State
  const [ingestionTab, setIngestionTab] = useState<'upload' | 'url' | 'manual'>('upload');
  const [isIngestionOpen, setIsIngestionOpen] = useState(false);

  // Document & Image Upload Tab State
  interface UploadedGuidelineItem {
    id: string;
    file: File;
    name: string;
    size: number;
    isImage: boolean;
    previewUrl?: string;
  }

  const [selectedFiles, setSelectedFiles] = useState<UploadedGuidelineItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgressStage, setUploadProgressStage] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);

  // Validate and append incoming files
  const handleAddFiles = (fileList: FileList | File[]) => {
    setErrorMessage(null);
    const incoming = Array.from(fileList);
    const validItems: UploadedGuidelineItem[] = [];

    for (const f of incoming) {
      const ext = f.name.substring(f.name.lastIndexOf('.')).toLowerCase();
      const isImg = ['.jpg', '.jpeg', '.png', '.webp'].includes(ext) || f.type.startsWith('image/');
      const isDoc = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.txt', '.md'].includes(ext);

      if (!isImg && !isDoc) {
        setErrorMessage(
          `File "${f.name}" has an unsupported format. Supported formats: Images (JPG, JPEG, PNG, WEBP), PDF, Word (.docx), PowerPoint (.pptx), and Plain Text (.txt).`
        );
        return;
      }

      if (f.size > 10 * 1024 * 1024) {
        setErrorMessage(
          `File "${f.name}" exceeds the 10MB maximum upload limit (${(f.size / (1024 * 1024)).toFixed(1)}MB). Please upload files under 10MB.`
        );
        return;
      }

      const id = `${f.name}-${f.size}-${Date.now()}-${Math.random()}`;
      const previewUrl = isImg ? URL.createObjectURL(f) : undefined;

      validItems.push({
        id,
        file: f,
        name: f.name,
        size: f.size,
        isImage: isImg,
        previewUrl,
      });
    }

    if (validItems.length > 0) {
      setSelectedFiles((prev) => [...prev, ...validItems]);
    }
  };

  const handleRemoveFile = (id: string) => {
    setSelectedFiles((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter((item) => item.id !== id);
    });
  };

  const handleClearAllFiles = () => {
    selectedFiles.forEach((item) => {
      if (item.previewUrl) {
        URL.revokeObjectURL(item.previewUrl);
      }
    });
    setSelectedFiles([]);
  };

  // URL Ingest Tab State
  const [urlInput, setUrlInput] = useState('');
  const [isIngestingUrl, setIsIngestingUrl] = useState(false);

  // Manual Entry Tab State
  const [newTitle, setNewTitle] = useState('');
  const [newRuleCode, setNewRuleCode] = useState('');
  const [newCategory, setNewCategory] = useState<RuleCategory>('tone');
  const [newRuleText, setNewRuleText] = useState('');
  const [newSeverity, setNewSeverity] = useState<'critical' | 'high' | 'medium' | 'low'>('high');
  const [submittingManual, setSubmittingManual] = useState(false);

  // Extraction Review Drawer State
  const [isReviewDrawerOpen, setIsReviewDrawerOpen] = useState(false);
  const [extractedReviewRules, setExtractedReviewRules] = useState<any[]>([]);
  const [selectedRuleIndices, setSelectedRuleIndices] = useState<Set<number>>(new Set());
  const [editingRuleIndex, setEditingRuleIndex] = useState<number | null>(null);
  const [reviewSourceTitle, setReviewSourceTitle] = useState<string>('');
  const [isCommittingRules, setIsCommittingRules] = useState(false);

  // General Notification / Error State
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchGuidelines = async () => {
    setLoading(true);
    try {
      const data = await guidelinesApi.list(currentBrand.id);
      if (data && data.length > 0) {
        setRules(data);
      } else {
        setRules([]);
      }
    } catch (err: any) {
      console.error('Failed to fetch guidelines:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGuidelines();
  }, [currentBrand.id]);

  // Handle Document & Image Upload & Rule Extraction
  const handleUploadDocumentSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (selectedFiles.length === 0) {
      setErrorMessage('Please select or drop at least one brand guideline document or image (JPG, JPEG, PNG, WEBP).');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);

    const hasImages = selectedFiles.some((f) => f.isImage);
    const hasDocs = selectedFiles.some((f) => !f.isImage);

    setUploadProgressStage(
      hasImages && hasDocs
        ? 'Extracting document hierarchies and running Tesseract OCR on images...'
        : hasImages
        ? 'Running Pillow decoding & Tesseract OCR on guideline images...'
        : 'Extracting document sections and slide hierarchies...'
    );

    try {
      const stageTimer1 = setTimeout(() => {
        setUploadProgressStage('Synthesizing atomic rules & Brand DNA via LLM reasoning...');
      }, 1400);

      const stageTimer2 = setTimeout(() => {
        setUploadProgressStage('Generating vector embeddings & formatting rules...');
      }, 2800);

      const filesToUpload = selectedFiles.map((item) => item.file);

      // Call uploadDocument with preview_only=true to populate the Review Drawer first
      const res = await guidelinesApi.uploadDocument(
        currentBrand.id,
        filesToUpload,
        undefined,
        false, // autoCommit = false
        true   // previewOnly = true
      );

      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);

      const rawRules = res?.rules || [];
      if (rawRules.length === 0) {
        throw new Error('No discrete brand rules could be extracted from the uploaded file(s).');
      }

      setExtractedReviewRules(rawRules);
      setSelectedRuleIndices(new Set(rawRules.map((_: any, idx: number) => idx)));
      setReviewSourceTitle(
        selectedFiles.length === 1
          ? selectedFiles[0].name
          : `${selectedFiles.length} guideline files (${selectedFiles.map((f) => f.name).join(', ')})`
      );
      setIsReviewDrawerOpen(true);
      handleClearAllFiles();
      setIsIngestionOpen(false);
    } catch (err: any) {
      setErrorMessage(
        err?.response?.data?.detail || err?.message || 'Failed to extract rules from document.'
      );
    } finally {
      setIsUploading(false);
      setUploadProgressStage('');
    }
  };

  // Handle URL Scraping & Rule Extraction
  const handleIngestUrlSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!urlInput.trim()) {
      setErrorMessage('Please enter a valid URL (e.g., https://company.com/brand-manual).');
      return;
    }

    setIsIngestingUrl(true);
    setErrorMessage(null);
    setUploadProgressStage('Verifying SSRF boundaries & fetching public webpage...');

    try {
      const stageTimer1 = setTimeout(() => {
        setUploadProgressStage('Synthesizing atomic rules from HTML structure...');
      }, 1400);

      const res = await guidelinesApi.ingestUrl(
        currentBrand.id,
        urlInput.trim(),
        false, // autoCommit = false
        true   // previewOnly = true
      );

      clearTimeout(stageTimer1);

      const rawRules = res?.rules || [];
      if (rawRules.length === 0) {
        throw new Error('No discrete rules could be extracted from this webpage.');
      }

      setExtractedReviewRules(rawRules);
      setSelectedRuleIndices(new Set(rawRules.map((_: any, idx: number) => idx)));
      setReviewSourceTitle(urlInput.trim());
      setIsReviewDrawerOpen(true);
      setUrlInput('');
      setIsIngestionOpen(false);
    } catch (err: any) {
      setErrorMessage(
        err?.response?.data?.detail || err?.message || 'Failed to ingest and extract rules from URL.'
      );
    } finally {
      setIsIngestingUrl(false);
      setUploadProgressStage('');
    }
  };

  // Handle Manual Single Rule Creation
  const handleManualCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newRuleText.trim()) {
      setErrorMessage('Please enter both Rule Title and Rule Text.');
      return;
    }

    setSubmittingManual(true);
    setErrorMessage(null);

    try {
      const activeBrandId = currentBrand?.id || 1;
      const ruleCode = newRuleCode.trim();
      const title = newTitle.trim();
      const ruleText = newRuleText.trim();
      const category = newCategory;

      const payload = {
        brand_id: activeBrandId || 1,
        rule_code: ruleCode.trim() || `${newCategory.slice(0, 4).toUpperCase()}-${Date.now().toString().slice(-3)}`,
        title: title.trim(),
        rule_text: ruleText.trim(),
        category: category.toLowerCase().replace(/\s+/g, '_'), // e.g. "Prohibited Claim" -> "prohibited_claim"
      };

      const created = await guidelinesApi.create(payload as any);

      if (Array.isArray(created)) {
        setRules((prev) => [...created, ...prev]);
      } else {
        setRules((prev) => [created, ...prev]);
      }

      setToastMessage(`Guideline rule "${newTitle}" saved and vectorized.`);
      setIsIngestionOpen(false);
      setNewTitle('');
      setNewRuleText('');
      setNewRuleCode('');
    } catch (err: any) {
      setErrorMessage(err?.message || err?.response?.data?.detail || 'Failed to create rule.');
    } finally {
      setSubmittingManual(false);
    }
  };

  // Toggle selection of rule in Review Drawer
  const toggleRuleSelection = (idx: number) => {
    setSelectedRuleIndices((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  const handleSelectAllRules = () => {
    if (selectedRuleIndices.size === extractedReviewRules.length) {
      setSelectedRuleIndices(new Set());
    } else {
      setSelectedRuleIndices(new Set(extractedReviewRules.map((_, i) => i)));
    }
  };

  // Commit selected & reviewed rules to database
  const handleConfirmAndSaveRules = async () => {
    const rulesToSave = extractedReviewRules.filter((_, idx) => selectedRuleIndices.has(idx));
    if (rulesToSave.length === 0) {
      setErrorMessage('Please select at least one rule to save.');
      return;
    }

    setIsCommittingRules(true);
    try {
      const res = await guidelinesApi.bulkSave(
        currentBrand.id,
        rulesToSave,
        reviewSourceTitle || 'Ingested Document'
      );

      const savedList = res?.rules || [];
      if (savedList.length > 0) {
        setRules((prev) => [...savedList, ...prev]);
      } else {
        await fetchGuidelines();
      }

      setToastMessage(
        `Successfully committed ${rulesToSave.length} rules to active guidelines and updated FAISS vector store!`
      );
      setIsReviewDrawerOpen(false);
      setExtractedReviewRules([]);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || 'Failed to commit rules to active database.');
    } finally {
      setIsCommittingRules(false);
    }
  };

  const filteredRules = rules.filter((rule) => {
    const matchesCat = selectedCategory === 'all' || rule.category === selectedCategory;
    const matchesSearch =
      (rule.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (rule.rule_code || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (rule.rule_text || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const categories: { label: string; value: string }[] = [
    { label: 'All Rules', value: 'all' },
    { label: 'Prohibited Claims', value: 'prohibited_claim' },
    { label: 'Tone of Voice', value: 'tone' },
    { label: 'Legal Compliance', value: 'legal_compliance' },
    { label: 'Brand Voice', value: 'brand_voice' },
    { label: 'Visual & Design', value: 'visual' },
    { label: 'Facts & Citations', value: 'fact' },
    { label: 'Accessibility', value: 'accessibility' },
  ];

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

      {/* Error Banner */}
      {errorMessage && (
        <div className="rounded-2xl bg-rose-50 border border-rose-200 p-4 text-xs text-rose-800 flex items-start gap-3 shadow-sm animate-in fade-in duration-200" id="guidelines-ingestion-error-banner">
          <X className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold block text-sm">Ingestion Error</span>
            <p className="mt-0.5 leading-relaxed">{errorMessage}</p>
            {errorMessage.toLowerCase().includes('copy') && (
              <div className="flex items-center gap-2 mt-2.5 flex-wrap">
                <button
                  type="button"
                  onClick={() => {
                    setIsIngestionOpen(true);
                    setIngestionTab('manual');
                    setErrorMessage(null);
                  }}
                  className="px-3 py-1 rounded-lg bg-white border border-rose-300 text-rose-900 font-bold hover:bg-rose-100 transition-colors cursor-pointer shadow-2xs"
                >
                  ✍️ Enter Rules Manually
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsIngestionOpen(true);
                    setIngestionTab('upload');
                    setErrorMessage(null);
                  }}
                  className="px-3 py-1 rounded-lg bg-white border border-rose-300 text-rose-900 font-bold hover:bg-rose-100 transition-colors cursor-pointer shadow-2xs"
                >
                  📄 Upload as Document
                </button>
              </div>
            )}
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="p-1 rounded-lg text-rose-500 hover:text-rose-800 hover:bg-rose-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 1. Page Header with Ingestion Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-brand-sand">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-brand-charcoal flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-brand-ocean" />
              Brand Safety Codex & Rule Inventory
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-brand-oceanLight/10 text-brand-ocean border border-brand-ocean/20">
              {rules.length} Active Rules
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-brand-cream text-brand-charcoal border border-brand-sand">
              {currentBrand.name}
            </span>
          </div>
          <p className="text-xs text-brand-charcoalMuted mt-1">
            Individual enforceable guidelines parsed from documents and public web docs, indexed for FAISS vector search and real-time compliance review.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              setIsIngestionOpen((prev) => !prev);
              setErrorMessage(null);
            }}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold shadow-sm transition-all active:scale-95 cursor-pointer ${
              isIngestionOpen
                ? 'bg-brand-ocean text-white shadow-card-elevated'
                : 'bg-brand-amber hover:bg-brand-amberHover text-white'
            }`}
            id="btn-open-ingestion"
          >
            <UploadCloud className="w-4 h-4" />
            <span>{isIngestionOpen ? 'Close Ingestion Hub' : '📥 Ingest Guidelines & Documents'}</span>
          </button>
        </div>
      </div>

      {/* 2. Unified 3-Tab Ingestion Hub (Deep Ocean Teal & Warm Amber) */}
      {isIngestionOpen && (
        <div className="bg-white rounded-2xl p-6 border-2 border-brand-ocean/30 shadow-card-elevated space-y-6 animate-in slide-in-from-top-4 duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-brand-sand">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-brand-ocean text-white flex items-center justify-center shadow-sm">
                <Sparkles className="w-5 h-5 text-brand-amber" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-brand-charcoal">
                  Multi-Modal Guideline Ingestion Hub
                </h2>
                <p className="text-xs text-brand-charcoalMuted">
                  Automatically extracts, normalizes, and embeds atomic compliance rules into FAISS.
                </p>
              </div>
            </div>

            {/* 3-Tab Segmented Switcher */}
            <div className="flex items-center p-1 rounded-xl bg-brand-cream border border-brand-sand">
              <button
                type="button"
                onClick={() => setIngestionTab('upload')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  ingestionTab === 'upload'
                    ? 'bg-brand-ocean text-white shadow-sm'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
                id="tab-doc-upload"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Document Upload</span>
              </button>

              <button
                type="button"
                onClick={() => setIngestionTab('url')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  ingestionTab === 'url'
                    ? 'bg-brand-ocean text-white shadow-sm'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
                id="tab-url-ingest"
              >
                <Globe className="w-3.5 h-3.5" />
                <span>Import from URL</span>
              </button>

              <button
                type="button"
                onClick={() => setIngestionTab('manual')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  ingestionTab === 'manual'
                    ? 'bg-brand-ocean text-white shadow-sm'
                    : 'text-brand-charcoalMuted hover:text-brand-charcoal'
                }`}
                id="tab-manual-entry"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Manual Entry</span>
              </button>
            </div>
          </div>

          {/* TAB 1: Document & Image Upload */}
          {ingestionTab === 'upload' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs font-mono text-brand-charcoalMuted flex-wrap gap-2">
                <span className="font-bold uppercase tracking-wider text-brand-charcoal">
                  Supported Enterprise Formats:
                </span>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200 font-bold text-[10px] flex items-center gap-1 shadow-xs">
                    <ImageIcon className="w-2.5 h-2.5 text-teal-700" />
                    Images (JPG, JPEG, PNG, WEBP)
                  </span>
                  <span className="px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 font-bold text-[10px]">
                    PDF Book
                  </span>
                  <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 font-bold text-[10px]">
                    Word Policy (.docx)
                  </span>
                  <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 font-bold text-[10px]">
                    PPT Deck (.pptx)
                  </span>
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-bold text-[10px]">
                    Plain Text (.txt)
                  </span>
                </div>
              </div>

              {/* Hidden multi-file input */}
              <input
                id="guideline-file-input"
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.md,.png,.jpg,.jpeg,.webp"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleAddFiles(e.target.files);
                  }
                  e.target.value = '';
                }}
                className="hidden"
              />

              {/* Dropzone or Multi-File Preview List */}
              {selectedFiles.length === 0 ? (
                /* Empty Drag & Drop Zone */
                <div
                  className={`p-8 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center space-y-3 ${
                    isDragging
                      ? 'border-brand-amber bg-brand-amber/10 scale-[1.01]'
                      : 'border-brand-sand hover:border-brand-ocean bg-brand-cream/30'
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
                    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                      handleAddFiles(e.dataTransfer.files);
                    }
                  }}
                  onClick={() => document.getElementById('guideline-file-input')?.click()}
                  id="guideline-dropzone"
                >
                  <div className="w-12 h-12 rounded-xl bg-brand-ocean/10 text-brand-ocean mx-auto flex items-center justify-center">
                    <UploadCloud className="w-6 h-6 text-brand-ocean" />
                  </div>

                  <div className="space-y-1">
                    <div className="text-sm font-bold text-brand-charcoal">
                      Drop enterprise guideline documents or images here, or click to browse
                    </div>
                    <p className="text-xs text-brand-charcoalMuted">
                      Upload single or multiple guideline images (JPG, JPEG, PNG, WEBP), multi-page PDF whitepapers, Word manuals, or slide decks.
                    </p>
                  </div>
                </div>
              ) : (
                /* Selected Files Gallery & List with Previews */
                <div className="p-4 rounded-2xl border border-brand-sand bg-brand-cream/30 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-brand-sand/60">
                    <div className="flex items-center gap-2 text-xs font-mono font-bold text-brand-charcoal">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>
                        {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected (
                        {(selectedFiles.reduce((acc, f) => acc + f.size, 0) / 1024).toFixed(1)} KB total)
                      </span>
                      <span className="text-brand-charcoalMuted font-normal">• Ready for extraction</span>
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => document.getElementById('guideline-file-input')?.click()}
                        className="text-[11px] font-mono text-brand-ocean hover:text-brand-oceanDark font-bold flex items-center gap-1 cursor-pointer"
                      >
                        <Plus className="w-3 h-3" />
                        <span>Add More</span>
                      </button>
                      <span className="text-brand-sand">•</span>
                      <button
                        type="button"
                        onClick={handleClearAllFiles}
                        className="text-[11px] font-mono text-rose-600 hover:text-rose-800 font-bold cursor-pointer"
                      >
                        Clear All
                      </button>
                    </div>
                  </div>

                  {/* Selected Files Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-64 overflow-y-auto pr-1">
                    {selectedFiles.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center gap-3 p-2.5 rounded-xl bg-white border border-brand-sand shadow-card-soft transition-all hover:border-brand-ocean/40"
                      >
                        {item.isImage && item.previewUrl ? (
                          <img
                            src={item.previewUrl}
                            alt={item.name}
                            className="w-12 h-12 rounded-lg object-cover border border-brand-sand shrink-0 shadow-xs"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-lg bg-brand-ocean/10 text-brand-ocean flex items-center justify-center shrink-0">
                            <FileText className="w-6 h-6" />
                          </div>
                        )}

                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-bold text-brand-charcoal truncate" title={item.name}>
                            {item.name}
                          </div>
                          <div className="flex items-center gap-2 text-[10px] font-mono text-brand-charcoalMuted mt-0.5">
                            <span>{(item.size / 1024).toFixed(1)} KB</span>
                            <span className="text-brand-sand">•</span>
                            <span className={item.isImage ? 'text-teal-700 font-bold' : 'text-blue-700 font-bold'}>
                              {item.isImage ? 'Image (OCR)' : 'Document'}
                            </span>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveFile(item.id);
                          }}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors shrink-0 cursor-pointer"
                          title="Remove file"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Drop zone strip for adding more */}
                  <div
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
                      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                        handleAddFiles(e.dataTransfer.files);
                      }
                    }}
                    onClick={() => document.getElementById('guideline-file-input')?.click()}
                    className={`py-2 px-3 rounded-xl border border-dashed text-center text-[11px] font-mono transition-all cursor-pointer ${
                      isDragging
                        ? 'border-brand-amber bg-brand-amber/10 text-brand-amber'
                        : 'border-brand-sand/80 hover:border-brand-ocean text-brand-charcoalMuted hover:text-brand-charcoal'
                    }`}
                  >
                    + Drag and drop more images or click to browse additional files
                  </div>
                </div>
              )}

              {/* Progress and Actions */}
              {isUploading && (
                <div className="p-4 rounded-xl bg-brand-cream border border-brand-sand space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono text-brand-ocean font-bold">
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-amber" />
                      {uploadProgressStage}
                    </span>
                    <span>AI Ingestion in Progress</span>
                  </div>
                  <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-brand-ocean to-brand-amber animate-pulse w-3/4 rounded-full" />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between pt-2 flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await fetch('/test_assets/brand_visual_policy.png');
                        const blob = await res.blob();
                        const file = new File([blob], 'brand_visual_policy.png', {
                          type: 'image/png',
                        });
                        handleAddFiles([file]);
                      } catch (err) {
                        console.error('Failed to load sample image:', err);
                      }
                    }}
                    className="text-[11px] font-mono text-teal-800 hover:text-teal-950 flex items-center gap-1 font-bold bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-200 cursor-pointer shadow-xs"
                    id="btn-sample-image-guidelines"
                  >
                    <ImageIcon className="w-3 h-3 text-teal-700" />
                    <span>Load Sample Image Guidelines</span>
                  </button>
                  <span className="text-brand-sand">•</span>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await fetch('/test_assets/product_guidelines.docx');
                        const blob = await res.blob();
                        const file = new File([blob], 'product_guidelines.docx', {
                          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        });
                        handleAddFiles([file]);
                      } catch (err) {
                        console.error(err);
                      }
                    }}
                    className="text-[11px] font-mono text-brand-ocean hover:text-brand-charcoal flex items-center gap-1 font-bold"
                  >
                    <FileText className="w-3 h-3 text-brand-ocean" />
                    Load Sample Word Guidelines
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
                        handleAddFiles([file]);
                      } catch (err) {
                        console.error(err);
                      }
                    }}
                    className="text-[11px] font-mono text-brand-ocean hover:text-brand-charcoal flex items-center gap-1 font-bold"
                  >
                    <Layers className="w-3 h-3 text-brand-amber" />
                    Load Sample PPTX Deck
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => handleUploadDocumentSubmit()}
                  disabled={selectedFiles.length === 0 || isUploading}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
                  id="btn-submit-doc-upload"
                >
                  {isUploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 text-white" />
                  )}
                  <span>Extract Atomic Rules {selectedFiles.length > 0 ? `(${selectedFiles.length})` : ''}</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: Import from URL */}
          {ingestionTab === 'url' && (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-mono uppercase text-brand-charcoal font-bold">
                  Enter Public Documentation Link (Notion, Google Docs Web view, Company Wiki):
                </label>
                <div className="relative">
                  <Globe className="w-4 h-4 text-brand-charcoalMuted absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="url"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    placeholder="https://brand.company.com/guidelines or public documentation URL..."
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white border border-brand-sand text-xs text-brand-charcoal font-mono placeholder-brand-charcoalMuted focus:outline-none focus:ring-1 focus:ring-brand-amber shadow-card-soft"
                    id="input-guideline-url"
                  />
                </div>
              </div>

              {/* SSRF & Security Badge */}
              <div className="flex items-center gap-2 text-[11px] font-mono text-brand-charcoalMuted bg-brand-cream p-3 rounded-xl border border-brand-sand">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>
                  <strong>SSRF Protected:</strong> Private subnets, localhost endpoints, and cloud metadata services (169.254.169.254) are strictly blocked.
                </span>
              </div>

              {/* Presets */}
              <div className="flex items-center gap-2 text-[11px] font-mono text-brand-charcoalMuted flex-wrap">
                <span className="font-bold">Verified Presets:</span>
                <button
                  type="button"
                  onClick={() => setUrlInput('https://www.site-example.com/')}
                  className="text-brand-ocean hover:underline font-semibold"
                >
                  Site Example (Scraper QA)
                </button>
                <span>•</span>
                <button
                  type="button"
                  onClick={() => setUrlInput('https://en.wikipedia.org/wiki/Brand_management')}
                  className="text-brand-ocean hover:underline"
                >
                  Brand Standards Wiki
                </button>
                <span>•</span>
                <button
                  type="button"
                  onClick={() => setUrlInput('https://www.ftc.gov/business-guidance/advertising-marketing')}
                  className="text-brand-ocean hover:underline"
                >
                  FTC Truth-in-Advertising
                </button>
              </div>

              {isIngestingUrl && (
                <div className="p-4 rounded-xl bg-brand-cream border border-brand-sand space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono text-brand-ocean font-bold">
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-amber" />
                      {uploadProgressStage}
                    </span>
                    <span>Scraping Web Page</span>
                  </div>
                  <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-brand-ocean to-brand-amber animate-pulse w-2/3 rounded-full" />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end pt-2">
                <button
                  type="button"
                  onClick={() => handleIngestUrlSubmit()}
                  disabled={!urlInput.trim() || isIngestingUrl}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
                  id="btn-submit-url-ingest"
                >
                  {isIngestingUrl ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Globe className="w-4 h-4 text-white" />
                  )}
                  <span>Fetch & Extract Rules</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: Manual Entry */}
          {ingestionTab === 'manual' && (
            <form onSubmit={handleManualCreateSubmit} className="space-y-4">
              {errorMessage && (
                <div
                  className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5 animate-in fade-in duration-150"
                  id="guideline-manual-error-banner"
                >
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                  <div className="flex-1 font-medium leading-relaxed">
                    {errorMessage || 'Failed to create rule.'}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
                    Category
                  </label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value as RuleCategory)}
                    className="w-full rounded-xl bg-brand-cream border border-brand-sand px-3 py-2 text-xs text-brand-charcoal focus:outline-none focus:ring-1 focus:ring-brand-amber"
                  >
                    <option value="tone">Tone of Voice</option>
                    <option value="prohibited_claim">Prohibited Claim</option>
                    <option value="legal_compliance">Legal Compliance</option>
                    <option value="brand_voice">Brand Voice</option>
                    <option value="visual">Visual & Design</option>
                    <option value="fact">Fact & Certification</option>
                    <option value="accessibility">Accessibility & WCAG</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
                    Severity Level
                  </label>
                  <select
                    value={newSeverity}
                    onChange={(e) => setNewSeverity(e.target.value as any)}
                    className="w-full rounded-xl bg-brand-cream border border-brand-sand px-3 py-2 text-xs text-brand-charcoal focus:outline-none focus:ring-1 focus:ring-brand-amber"
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
                    Rule Code (Optional)
                  </label>
                  <input
                    type="text"
                    value={newRuleCode}
                    onChange={(e) => setNewRuleCode(e.target.value)}
                    placeholder="e.g. CLAIM-01"
                    className="w-full rounded-xl bg-brand-cream border border-brand-sand px-3 py-2 text-xs text-brand-charcoal font-mono focus:outline-none focus:ring-1 focus:ring-brand-amber"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
                  Rule Title
                </label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. No Unsubstantiated Uptime Guarantees"
                  className="w-full rounded-xl bg-brand-cream border border-brand-sand px-3 py-2 text-xs text-brand-charcoal focus:outline-none focus:ring-1 focus:ring-brand-amber font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
                  Enforceable Rule Text
                </label>
                <textarea
                  value={newRuleText}
                  onChange={(e) => setNewRuleText(e.target.value)}
                  rows={3}
                  placeholder="Exact imperative statement (e.g. Never advertise 100% bug-free uptime without citing independent audit reports)..."
                  className="w-full rounded-xl bg-brand-cream border border-brand-sand p-3 text-xs text-brand-charcoal font-mono focus:outline-none focus:ring-1 focus:ring-brand-amber leading-relaxed"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="submit"
                  disabled={submittingManual}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
                  id="btn-submit-manual-rule"
                >
                  {submittingManual ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Plus className="w-4 h-4 text-white" />
                  )}
                  <span>Save Rule to Codex</span>
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* 3. Extraction Review Drawer / Modal */}
      {isReviewDrawerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-oceanDark/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl bg-white border border-brand-sand shadow-card-elevated text-brand-charcoal animate-in zoom-in-95 duration-150">
            {/* Drawer Header */}
            <div className="flex items-center justify-between p-6 border-b border-brand-sand">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-ocean text-white flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-brand-amber" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-brand-charcoal">
                    Extraction Review & Verification Checklist
                  </h3>
                  <p className="text-xs text-brand-charcoalMuted">
                    Discovered {extractedReviewRules.length} atomic rules from{' '}
                    <strong className="text-brand-ocean">{reviewSourceTitle}</strong>. Select and tweak rules before saving.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleSelectAllRules}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-cream border border-brand-sand text-xs font-semibold text-brand-charcoal hover:border-brand-amber"
                >
                  {selectedRuleIndices.size === extractedReviewRules.length ? (
                    <>
                      <CheckSquare className="w-3.5 h-3.5 text-brand-ocean" />
                      <span>Deselect All</span>
                    </>
                  ) : (
                    <>
                      <Square className="w-3.5 h-3.5 text-brand-charcoalMuted" />
                      <span>Select All</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => setIsReviewDrawerOpen(false)}
                  className="p-1.5 rounded-lg text-brand-charcoalMuted hover:text-brand-charcoal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Drawer Body: Checklist of Extracted Rules */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {extractedReviewRules.map((rule, idx) => {
                const isSelected = selectedRuleIndices.has(idx);
                const isEditing = editingRuleIndex === idx;

                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-xl border transition-all ${
                      isSelected
                        ? 'border-brand-ocean/40 bg-white shadow-sm'
                        : 'border-slate-200 bg-slate-50/50 opacity-70'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <button
                        type="button"
                        onClick={() => toggleRuleSelection(idx)}
                        className="mt-1 text-brand-ocean hover:text-brand-oceanDark"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-5 h-5 text-brand-ocean" />
                        ) : (
                          <Square className="w-5 h-5 text-slate-400" />
                        )}
                      </button>

                      <div className="flex-1 space-y-2">
                        {isEditing ? (
                          /* Inline Edit Mode */
                          <div className="space-y-3 bg-brand-cream p-4 rounded-xl border border-brand-sand">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                              <div>
                                <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                                  Rule Code
                                </label>
                                <input
                                  type="text"
                                  value={rule.rule_code}
                                  onChange={(e) => {
                                    const updated = [...extractedReviewRules];
                                    updated[idx].rule_code = e.target.value;
                                    setExtractedReviewRules(updated);
                                  }}
                                  className="w-full bg-white border border-brand-sand rounded-lg px-2.5 py-1 text-xs font-mono"
                                />
                              </div>

                              <div>
                                <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                                  Category
                                </label>
                                <select
                                  value={rule.category}
                                  onChange={(e) => {
                                    const updated = [...extractedReviewRules];
                                    updated[idx].category = e.target.value;
                                    setExtractedReviewRules(updated);
                                  }}
                                  className="w-full bg-white border border-brand-sand rounded-lg px-2.5 py-1 text-xs"
                                >
                                  <option value="prohibited_claim">Prohibited Claim</option>
                                  <option value="legal_compliance">Legal Compliance</option>
                                  <option value="brand_voice">Brand Voice</option>
                                  <option value="tone">Tone of Voice</option>
                                  <option value="visual">Visual & Design</option>
                                  <option value="fact">Fact & Certification</option>
                                  <option value="accessibility">Accessibility</option>
                                </select>
                              </div>

                              <div>
                                <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                                  Severity
                                </label>
                                <select
                                  value={rule.severity || 'high'}
                                  onChange={(e) => {
                                    const updated = [...extractedReviewRules];
                                    updated[idx].severity = e.target.value;
                                    setExtractedReviewRules(updated);
                                  }}
                                  className="w-full bg-white border border-brand-sand rounded-lg px-2.5 py-1 text-xs"
                                >
                                  <option value="critical">Critical</option>
                                  <option value="high">High</option>
                                  <option value="medium">Medium</option>
                                  <option value="low">Low</option>
                                </select>
                              </div>
                            </div>

                            <div>
                              <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                                Title
                              </label>
                              <input
                                type="text"
                                value={rule.title}
                                onChange={(e) => {
                                  const updated = [...extractedReviewRules];
                                  updated[idx].title = e.target.value;
                                  setExtractedReviewRules(updated);
                                }}
                                className="w-full bg-white border border-brand-sand rounded-lg px-2.5 py-1 text-xs font-bold"
                              />
                            </div>

                            <div>
                              <label className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold block mb-1">
                                Rule Text
                              </label>
                              <textarea
                                value={rule.rule_text}
                                onChange={(e) => {
                                  const updated = [...extractedReviewRules];
                                  updated[idx].rule_text = e.target.value;
                                  setExtractedReviewRules(updated);
                                }}
                                rows={2}
                                className="w-full bg-white border border-brand-sand rounded-lg p-2.5 text-xs font-mono"
                              />
                            </div>

                            <div className="flex justify-end">
                              <button
                                type="button"
                                onClick={() => setEditingRuleIndex(null)}
                                className="px-3 py-1 rounded-lg bg-brand-ocean text-white text-xs font-bold"
                              >
                                Done Editing
                              </button>
                            </div>
                          </div>
                        ) : (
                          /* View Mode */
                          <div>
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-cream border border-brand-sand text-brand-ocean">
                                  {rule.rule_code}
                                </span>
                                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider font-bold bg-slate-100 text-slate-800 border border-slate-200">
                                  {rule.category.replace('_', ' ')}
                                </span>
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold border ${
                                    rule.severity === 'critical'
                                      ? 'bg-rose-100 text-rose-900 border-rose-300'
                                      : 'bg-amber-100 text-amber-900 border-amber-300'
                                  }`}
                                >
                                  {(rule.severity || 'high').toUpperCase()}
                                </span>
                                {rule.source_file && (
                                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-teal-50 text-teal-800 border border-teal-200 flex items-center gap-1">
                                    <FileText className="w-2.5 h-2.5 text-teal-700" />
                                    <span className="max-w-[160px] truncate" title={rule.source_file}>
                                      {rule.source_file}
                                    </span>
                                  </span>
                                )}
                              </div>

                              <button
                                type="button"
                                onClick={() => setEditingRuleIndex(idx)}
                                className="text-xs text-brand-charcoalMuted hover:text-brand-ocean flex items-center gap-1 font-semibold"
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                                <span>Edit</span>
                              </button>
                            </div>

                            <div className="text-xs font-bold text-brand-charcoal mt-1.5">
                              {rule.title}
                            </div>
                            <p className="text-xs text-brand-charcoal font-mono bg-brand-cream p-2.5 rounded-lg border border-brand-sand mt-1">
                              "{rule.rule_text}"
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Drawer Footer Actions */}
            <div className="flex items-center justify-between p-6 border-t border-brand-sand bg-brand-cream/30">
              <div className="text-xs font-mono text-brand-charcoalMuted">
                <strong className="text-brand-charcoal">{selectedRuleIndices.size}</strong> of{' '}
                {extractedReviewRules.length} rules selected for commit.
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsReviewDrawerOpen(false)}
                  disabled={isCommittingRules}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleConfirmAndSaveRules}
                  disabled={selectedRuleIndices.size === 0 || isCommittingRules}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
                  id="btn-confirm-save-rules"
                >
                  {isCommittingRules ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Updating Vector Index...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4 text-white" />
                      <span>Confirm & Save {selectedRuleIndices.size} Rules to Active Guidelines</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Filter and Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === cat.value
                  ? 'bg-brand-ocean text-white shadow-sm'
                  : 'bg-white text-brand-charcoalMuted hover:text-brand-charcoal border border-brand-sand shadow-card-soft'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-brand-charcoalMuted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search rules, codes, keywords..."
            className="w-full pl-9 pr-3.5 py-2 rounded-xl bg-white border border-brand-sand text-xs text-brand-charcoal placeholder-brand-charcoalMuted focus:outline-none focus:ring-1 focus:ring-brand-amber shadow-card-soft"
          />
        </div>
      </div>

      {/* 5. Rules Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-brand-charcoalMuted gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-brand-ocean" />
          <span className="text-sm font-mono">Loading guideline codex...</span>
        </div>
      ) : filteredRules.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-brand-sand shadow-card-soft space-y-3">
          <FileText className="w-10 h-10 text-brand-charcoalMuted mx-auto mb-2" />
          <h3 className="text-base font-bold text-brand-charcoal">No matching guidelines found</h3>
          <p className="text-xs text-brand-charcoalMuted">
            Ingest brand manuals (.pdf/.docx/.pptx) or enter public documentation URLs to auto-populate your rules codex.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRules.map((rule) => {
            const categoryColors: Record<string, string> = {
              prohibited_claim: 'bg-red-50 text-red-700 border-red-200',
              legal_compliance: 'bg-rose-50 text-rose-800 border-rose-200',
              brand_voice: 'bg-brand-oceanLight/10 text-brand-ocean border-brand-ocean/20',
              tone: 'bg-brand-oceanLight/10 text-brand-ocean border-brand-ocean/20',
              visual: 'bg-sky-50 text-sky-800 border-sky-200',
              fact: 'bg-amber-50 text-amber-800 border-amber-200',
              accessibility: 'bg-emerald-50 text-emerald-700 border-emerald-200',
            };
            const catBadgeStyle =
              categoryColors[rule.category] || 'bg-brand-cream text-brand-charcoal border-brand-sand';

            return (
              <div
                key={rule.id}
                className="bg-white rounded-2xl p-5 border border-brand-sand shadow-card-soft hover:shadow-card-elevated hover:border-brand-amber/50 transition-all flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded-lg text-[11px] font-mono font-bold bg-brand-cream border border-brand-sand text-brand-ocean">
                        {rule.rule_code}
                      </span>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono uppercase tracking-wider font-bold border ${catBadgeStyle}`}>
                        {rule.category.replace('_', ' ')}
                      </span>
                    </div>
                    <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-700 font-bold shrink-0">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                      Active
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-brand-charcoal mt-3">{rule.title}</h3>
                  <p className="text-xs text-brand-charcoal leading-relaxed bg-brand-cream p-3.5 rounded-xl border border-brand-sand font-mono mt-2.5">
                    "{rule.rule_text}"
                  </p>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-brand-sand/60 text-[11px] font-mono text-brand-charcoalMuted">
                  <span className="truncate max-w-[200px]" title={rule.source_file || 'Manual Entry'}>
                    Source: {rule.source_file || 'Manual Entry'}
                  </span>
                  <span className="font-semibold text-brand-charcoal">v{rule.version || 1}.0</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default GuidelinesPage;
