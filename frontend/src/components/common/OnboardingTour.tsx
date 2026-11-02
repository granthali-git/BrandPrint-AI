import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  LayoutDashboard,
  ScanSearch,
  Columns,
  History,
  FileText,
  UploadCloud,
  Globe,
  ArrowRight,
  ArrowLeft,
  X,
  CheckCircle2,
  Trophy,
  ExternalLink,
  HelpCircle,
  Layers,
  Lock,
  Check,
  Compass,
  Play,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

interface TourStep {
  id: string;
  stepNumber: number;
  badge: string;
  title: string;
  description: string;
  targetRoute?: string;
  targetLabel?: string;
  highlights: string[];
  visualType: 'welcome' | 'sidebar' | 'studio' | 'compare' | 'history';
}

const TOUR_STEPS: TourStep[] = [
  {
    id: 'step-welcome',
    stepNumber: 1,
    badge: 'Step 1 of 5 • Workspace Overview',
    title: 'Welcome to BrandPrint AI Workspace',
    description:
      'Your enterprise platform for automated brand governance, legal compliance auditing, and multi-modal safety verification.',
    targetRoute: '/',
    targetLabel: 'Explore Dashboard',
    highlights: [
      'Multi-modal content auditing (Text copy, Poster creatives, multi-page PDFs, and live URLs)',
      'Strict grounding against active Brand Guidelines via FAISS semantic retrieval + Gemini 1.5',
      'Real-time automated compliance scoring, zero-tolerance checks, and legal certificate generation',
    ],
    visualType: 'welcome',
  },
  {
    id: 'step-sidebar',
    stepNumber: 2,
    badge: 'Step 2 of 5 • Platform Navigation',
    title: 'Platform Navigation & Core Workspaces',
    description:
      'Access all core workspaces here. Quickly switch between live campaign audits, multi-asset comparisons, and historical review logs.',
    targetRoute: '/studio',
    targetLabel: 'Open Review Studio',
    highlights: [
      'Dashboard: Executive compliance metrics, active brand status, and recent health checks',
      'Review Studio: The primary auditing workbench with dual independently scrollable panels',
      'Asset Comparison: Benchmark up to 3 campaign variants side-by-side to crown the winner',
      'Audit & Contradictions: Deep semantic contradiction checks across multi-page whitepapers',
      'Audit History: Chronological archive of all past audit sessions with instant session restoration',
    ],
    visualType: 'sidebar',
  },
  {
    id: 'step-studio',
    stepNumber: 3,
    badge: 'Step 3 of 5 • Main Ingestion Hub',
    title: 'Review Studio & Input Modalities',
    description:
      'Ingest content via text copy, uploaded posters/PDFs (with instant OCR), or live webpage URLs to detect prohibited claims and missing disclaimers.',
    targetRoute: '/studio',
    targetLabel: 'Launch Review Studio',
    highlights: [
      'Raw Text: Monaco buffer for advertising headlines, social statement copy, and PR announcements',
      'File Upload & OCR: Native parsing for slide decks (PPTX), whitepapers (PDF), DOCX, and visual posters',
      'Web Scraping: SSRF-sandboxed HTML parsing with readability indices and WCAG visual contrast checks',
      'Interactive Fixes: Review citations against active policies with one-click fix substitutions',
    ],
    visualType: 'studio',
  },
  {
    id: 'step-compare',
    stepNumber: 4,
    badge: 'Step 4 of 5 • Multi-Asset Comparison',
    title: 'Asset Comparison & Winner Decision',
    description:
      'Compare up to 3 versions of campaign assets side-by-side. The AI automatically benchmarks them against company guidelines and selects the production-ready winner.',
    targetRoute: '/compare',
    targetLabel: 'Open Comparison View',
    highlights: [
      '3-Way Responsive Grid: Benchmark Baseline (Slot A), Iteration 1 (Slot B), and Final Variant (Slot C)',
      'Objective Scoring Matrix: Evaluates prohibited claims (-30 pts), factual drift (-15 pts), and tone shifts',
      'Best Compliant Variant Coronation: Crowns the winning iteration with detailed executive rationale',
      'Differential Finding Matrix: Visualizes exactly which claims each iteration improved or introduced',
    ],
    visualType: 'compare',
  },
  {
    id: 'step-history',
    stepNumber: 5,
    badge: 'Step 5 of 5 • Governance & Records',
    title: 'Audit History & Transparency',
    description:
      'Search past audits chronologically and inspect complete transparency records with PII masking details.',
    targetRoute: '/history',
    targetLabel: 'View Audit History',
    highlights: [
      'Chronological Timeline: Sessions automatically grouped into Today, Yesterday, Previous 7 Days, and Earlier',
      'Live Real-Time Search: Query past audits by asset title, copy phrase, or specific policy violation',
      'Instant Session Restore: Click any card to resurrect exact inputs, files, findings, and scores',
      'Cryptographic AI Audit Log: SHA-256 prompt digest and PII redaction ledgers for legal verification',
    ],
    visualType: 'history',
  },
];

export const OnboardingTour: React.FC = () => {
  const { isOnboardingOpen, closeOnboarding, startLiveDemo } = useApp();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const navigate = useNavigate();

  // Reset to first step whenever reopened
  useEffect(() => {
    if (isOnboardingOpen) {
      setCurrentStepIndex(0);
    }
  }, [isOnboardingOpen]);

  // Keyboard navigation: Escape closes, ArrowRight advances, ArrowLeft steps back
  useEffect(() => {
    if (!isOnboardingOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeOnboarding();
      } else if (e.key === 'ArrowRight') {
        setCurrentStepIndex((prev) => Math.min(prev + 1, TOUR_STEPS.length - 1));
      } else if (e.key === 'ArrowLeft') {
        setCurrentStepIndex((prev) => Math.max(prev - 1, 0));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOnboardingOpen, closeOnboarding]);

  if (!isOnboardingOpen) return null;

  const currentStep = TOUR_STEPS[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === TOUR_STEPS.length - 1;

  const handleNext = () => {
    if (isLastStep) {
      closeOnboarding();
    } else {
      setCurrentStepIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (!isFirstStep) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  };

  const handleNavigateAndClose = (route?: string) => {
    if (route) {
      navigate(route);
    }
    closeOnboarding();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-brand-oceanDark/60 backdrop-blur-sm animate-in fade-in duration-200"
      id="onboarding-tour-modal"
    >
      <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-3xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 text-brand-charcoal">
        {/* Top Header Bar */}
        <div className="px-6 py-4 border-b border-brand-sand bg-brand-cream/70 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-brand-ocean text-brand-amber flex items-center justify-center shadow-md">
              <Sparkles className="w-5 h-5 text-brand-amber" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono uppercase tracking-wider font-extrabold text-brand-ocean">
                  BrandPrint AI
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-brand-amber/15 text-brand-amberHover border border-brand-amber/30">
                  Platform Guide
                </span>
              </div>
              <p className="text-xs font-medium text-brand-charcoalMuted">
                Interactive Feature Tour & Governance Walkthrough
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono font-bold text-brand-charcoalMuted bg-white px-2.5 py-1 rounded-xl border border-brand-sand shadow-2xs">
              {currentStepIndex + 1} / {TOUR_STEPS.length}
            </span>
            <button
              onClick={closeOnboarding}
              className="p-1.5 rounded-xl text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors cursor-pointer"
              title="Close tour (Esc)"
              id="btn-close-onboarding"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Main Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {/* Step Pill & Title */}
          <div className="space-y-2">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-bold bg-brand-oceanLight/10 text-brand-ocean border border-brand-ocean/20">
              <Compass className="w-3.5 h-3.5 text-brand-amber" />
              <span>{currentStep.badge}</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-brand-charcoal tracking-tight">
              {currentStep.title}
            </h2>
            <p className="text-sm text-brand-charcoal leading-relaxed text-slate-600">
              {currentStep.description}
            </p>
          </div>

          {/* Visual Interactive Showcase Card */}
          <div className="rounded-2xl border border-brand-sand bg-brand-cream/40 p-5 space-y-4 shadow-inner">
            {currentStep.visualType === 'welcome' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="bg-white p-3.5 rounded-xl border border-brand-sand shadow-sm space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-brand-ocean">
                    <span>Multi-Modal OCR</span>
                    <FileText className="w-4 h-4 text-brand-amber" />
                  </div>
                  <p className="text-[11px] text-brand-charcoalMuted">
                    Parse text, slide decks, PDFs, and creative posters seamlessly.
                  </p>
                </div>
                <div className="bg-white p-3.5 rounded-xl border border-brand-sand shadow-sm space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-brand-ocean">
                    <span>FAISS + Gemini</span>
                    <Sparkles className="w-4 h-4 text-brand-amber" />
                  </div>
                  <p className="text-[11px] text-brand-charcoalMuted">
                    Grounded evaluation against active enterprise brand rules.
                  </p>
                </div>
                <div className="bg-white p-3.5 rounded-xl border border-brand-sand shadow-sm space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-brand-ocean">
                    <span>Safety Score</span>
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  </div>
                  <p className="text-[11px] text-brand-charcoalMuted">
                    Objective penalty deduction with certified legal clearances.
                  </p>
                </div>
              </div>

              {/* Prominent Live Demo Feature Banner on Welcome Screen */}
              <div className="mt-4 p-4 rounded-2xl bg-gradient-to-r from-brand-oceanDark to-brand-ocean border border-brand-amber/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-white shadow-md">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-brand-amber flex items-center gap-1.5 uppercase font-mono tracking-wider">
                      <Sparkles className="w-3.5 h-3.5" /> Autonomous Tour
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">
                      Live Working APIs
                    </span>
                  </div>
                  <p className="text-xs text-brand-sand leading-relaxed">
                    Sit back and watch BrandPrint AI autonomously audit guidelines, evaluate marketing copy, and benchmark 3-way assets in real-time.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    closeOnboarding();
                    startLiveDemo();
                  }}
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-md transition-all active:scale-95 shrink-0 cursor-pointer border border-white/20"
                  id="btn-welcome-hero-live-demo"
                >
                  <Play className="w-3.5 h-3.5 fill-white text-white" />
                  <span>WATCH LIVE DEMO</span>
                </button>
              </div>
            </>
            )}

            {currentStep.visualType === 'sidebar' && (
              <div className="bg-white rounded-xl border border-brand-sand p-3 shadow-sm space-y-2">
                <div className="text-[11px] font-mono text-brand-charcoalMuted uppercase font-bold flex items-center justify-between">
                  <span>Sidebar Workspace Hub</span>
                  <span className="text-brand-amber font-semibold">5 Core Modules</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs font-semibold">
                  <div className="p-2 rounded-lg bg-brand-cream/80 border border-brand-sand flex flex-col items-center text-center gap-1">
                    <LayoutDashboard className="w-4 h-4 text-brand-ocean" />
                    <span className="text-[11px]">Dashboard</span>
                  </div>
                  <div className="p-2 rounded-lg bg-brand-ocean text-white shadow-xs flex flex-col items-center text-center gap-1">
                    <ScanSearch className="w-4 h-4 text-brand-amber" />
                    <span className="text-[11px]">Review Studio</span>
                  </div>
                  <div className="p-2 rounded-lg bg-brand-cream/80 border border-brand-sand flex flex-col items-center text-center gap-1">
                    <Columns className="w-4 h-4 text-brand-ocean" />
                    <span className="text-[11px]">Comparison</span>
                  </div>
                  <div className="p-2 rounded-lg bg-brand-cream/80 border border-brand-sand flex flex-col items-center text-center gap-1">
                    <ShieldAlert className="w-4 h-4 text-brand-amber" />
                    <span className="text-[11px]">Audit Gaps</span>
                  </div>
                  <div className="p-2 rounded-lg bg-brand-cream/80 border border-brand-sand flex flex-col items-center text-center gap-1">
                    <History className="w-4 h-4 text-brand-ocean" />
                    <span className="text-[11px]">History</span>
                  </div>
                </div>
              </div>
            )}

            {currentStep.visualType === 'studio' && (
              <div className="bg-white rounded-xl border border-brand-sand p-3.5 shadow-sm space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                  <span className="font-mono font-bold text-brand-charcoal">3 Ingestion Modalities:</span>
                  <div className="flex items-center gap-1 p-0.5 rounded-lg bg-brand-cream border border-brand-sand text-[11px] font-semibold">
                    <span className="px-2 py-0.5 rounded bg-brand-ocean text-white">Raw Text</span>
                    <span className="px-2 py-0.5 text-brand-charcoalMuted">File Upload</span>
                    <span className="px-2 py-0.5 text-brand-charcoalMuted">Live URL</span>
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-brand-cream/60 border border-brand-sand font-mono text-[11px] text-brand-charcoal">
                  <span className="text-emerald-700 font-bold">✓ Dual Independent Scroll:</span> Left pane displays long submitted copy/visuals, right pane displays interactive policy citations & recommendations.
                </div>
              </div>
            )}

            {currentStep.visualType === 'compare' && (
              <div className="bg-white rounded-xl border border-brand-sand p-3.5 shadow-sm space-y-2">
                <div className="flex items-center justify-between text-xs font-bold">
                  <span>3-Slot Comparison Engine</span>
                  <span className="text-emerald-700 flex items-center gap-1 font-mono text-[11px]">
                    <Trophy className="w-3.5 h-3.5 text-brand-amber" /> Auto-Crown Winner
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-lg bg-brand-cream border border-brand-sand">
                    <span className="font-bold text-[11px] block">Slot A</span>
                    <span className="text-[10px] text-brand-charcoalMuted">Baseline (72%)</span>
                  </div>
                  <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-300 ring-1 ring-emerald-400">
                    <span className="font-bold text-[11px] text-emerald-800 flex items-center justify-center gap-1">
                      👑 Slot B
                    </span>
                    <span className="text-[10px] text-emerald-700 font-bold">Winner (98%)</span>
                  </div>
                  <div className="p-2 rounded-lg bg-brand-cream border border-brand-sand">
                    <span className="font-bold text-[11px] block">Slot C</span>
                    <span className="text-[10px] text-brand-charcoalMuted">Test Copy (65%)</span>
                  </div>
                </div>
              </div>
            )}

            {currentStep.visualType === 'history' && (
              <div className="bg-white rounded-xl border border-brand-sand p-3.5 shadow-sm space-y-2">
                <div className="flex items-center justify-between text-xs font-bold">
                  <span>Audit History Timeline</span>
                  <span className="text-[10px] font-mono text-brand-charcoalMuted">Instant 1-Click Restore</span>
                </div>
                <div className="space-y-1.5 text-xs font-mono">
                  <div className="p-2 rounded-lg bg-brand-cream/80 border border-brand-sand flex items-center justify-between">
                    <span className="font-semibold text-brand-charcoal truncate max-w-xs">
                      Enterprise Cloud Launch Copy
                    </span>
                    <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                      94% • Today
                    </span>
                  </div>
                  <div className="p-2 rounded-lg bg-brand-cream/50 border border-brand-sand flex items-center justify-between">
                    <span className="text-brand-charcoalMuted truncate max-w-xs">
                      Q4 Fintech Campaign Whitepaper
                    </span>
                    <span className="text-[10px] font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full">
                      78% • Yesterday
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Feature Highlights Checklist */}
            <div className="space-y-2 pt-1 border-t border-brand-sand">
              <span className="text-[11px] font-mono uppercase font-bold text-brand-charcoalMuted block">
                Key Highlights & Capabilities:
              </span>
              <ul className="space-y-1.5 text-xs text-brand-charcoal">
                {currentStep.highlights.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="px-6 py-4 border-t border-brand-sand bg-brand-cream/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Step Indicator Dots */}
          <div className="flex items-center gap-2">
            {TOUR_STEPS.map((step, idx) => (
              <button
                key={step.id}
                onClick={() => setCurrentStepIndex(idx)}
                className={`transition-all rounded-full cursor-pointer ${
                  idx === currentStepIndex
                    ? 'w-7 h-2.5 bg-brand-amber shadow-xs'
                    : 'w-2.5 h-2.5 bg-brand-sand hover:bg-brand-charcoalMuted'
                }`}
                title={`Go to ${step.title}`}
              />
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end flex-wrap">
            {currentStep.targetRoute && (
              <button
                type="button"
                onClick={() => handleNavigateAndClose(currentStep.targetRoute)}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-brand-ocean hover:bg-brand-cream border border-brand-sand transition-colors cursor-pointer"
                title={`Jump directly to ${currentStep.targetLabel}`}
              >
                <span>{currentStep.targetLabel}</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            )}

            <button
              type="button"
              onClick={closeOnboarding}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors cursor-pointer"
            >
              Skip Tour
            </button>

            {!isFirstStep && (
              <button
                type="button"
                onClick={handlePrev}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-brand-sand bg-white text-xs font-semibold text-brand-charcoal hover:bg-brand-cream transition-colors shadow-2xs cursor-pointer active:scale-95"
                id="btn-onboarding-prev"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>
            )}

            {/* Live Demo button on Welcome Step (Step 1) and Final Step (Step 5) */}
            {(isFirstStep || isLastStep) && (
              <button
                type="button"
                onClick={() => {
                  closeOnboarding();
                  startLiveDemo();
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-brand-amber via-amber-500 to-brand-amberHover text-white text-xs font-bold shadow-md hover:shadow-lg transition-all active:scale-95 cursor-pointer ring-2 ring-brand-amber/40 hover:ring-brand-amber"
                id="btn-onboarding-watch-live-demo-footer"
                title="Watch autonomous live working product demonstration"
              >
                <Play className="w-3.5 h-3.5 fill-white text-white" />
                <span>WATCH LIVE DEMO</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleNext}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-brand-ocean hover:bg-brand-oceanDark text-white text-xs font-bold transition-all shadow-card-soft active:scale-95 cursor-pointer border border-brand-oceanLight/30"
              id="btn-onboarding-next"
            >
              <span>{isLastStep ? 'Get Started' : 'Next'}</span>
              {!isLastStep && <ArrowRight className="w-3.5 h-3.5 text-brand-amber" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingTour;
