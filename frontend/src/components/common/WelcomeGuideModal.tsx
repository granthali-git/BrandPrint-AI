import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  Layers,
  GitCompare,
  History,
  X,
  ChevronRight,
  ChevronLeft,
  Volume2,
  VolumeX,
  Play,
  Sparkles,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

interface GuideStep {
  title: string;
  badge: string;
  icon: React.ReactNode;
  description: string;
  speechText: string;
  details: string[];
}

const steps: GuideStep[] = [
  {
    title: 'Welcome to BrandPrint AI',
    badge: 'Enterprise Safety & Audit',
    icon: <ShieldCheck className="w-7 h-7 text-[#F4A321]" />,
    description:
      'BrandPrint AI detects brand guidelines violations, contradiction rules, and regulatory risks across multi-modal marketing assets.',
    speechText:
      'Welcome to BrandPrint AI. This platform automates brand governance and verifies legal compliance across your campaign text, images, and live websites.',
    details: [
      'Automated evaluation using Gemini & Local models',
      'Protects confidential brand assets with PII masking',
      'Verifies disclaimers, medical claims, and competitor mentions',
    ],
  },
  {
    title: 'Review Studio (Live Audit Hub)',
    badge: 'Ingestion Engine',
    icon: <Layers className="w-7 h-7 text-teal-400" />,
    description: 'Upload and audit your marketing assets through three flexible input channels:',
    speechText:
      'In the Review Studio, you can test marketing content using raw copy, uploaded images and documents with OCR, or live website URLs.',
    details: [
      'Raw Copy / Text: Paste headlines, promos, and copy directly',
      'Upload Document: Extract and audit images and PDFs with OCR',
      'Live URL / Web: Enter any webpage link to automatically scrape copy',
    ],
  },
  {
    title: 'Multi-Asset Comparison (Up to 3 Items)',
    badge: 'Winner Decision Engine',
    icon: <GitCompare className="w-7 h-7 text-indigo-400" />,
    speechText:
      'The comparison view lets you compare up to three assets side-by-side. The AI evaluates each against company rules and selects the best production-ready variant.',
    description: 'Compare baseline assets, campaign drafts, and final variants side by side:',
    details: [
      'Independent ingestion for Slot A, Slot B, and Slot C',
      'Automated scoring against loaded guidelines',
      'AI automatically crowns the "Production Ready Winner" with reasoning',
    ],
  },
  {
    title: 'Audit History & Search',
    badge: 'Session Replay',
    icon: <History className="w-7 h-7 text-emerald-400" />,
    speechText:
      'With Audit History, you can search all past reviews, view exact dates, and click any item to restore the previous inputs and results.',
    description: 'Keep track of every audit and comparison session just like ChatGPT and Gemini:',
    details: [
      'Search past audits by campaign name or keyword',
      'Clear timestamp grouping: Today, Yesterday, and Previous 7 Days',
      'Click any past session to instantly reload inputs and results',
    ],
  },
];

export const WelcomeGuideModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  // Initialize voice preference from localStorage (defaults to true if not set)
  const [isVoiceEnabled, setIsVoiceEnabled] = useState<boolean>(() => {
    const saved = localStorage.getItem('brandprint_voice_enabled');
    return saved !== null ? saved === 'true' : true;
  });

  const [isSpeaking, setIsSpeaking] = useState(false);
  const synthRef = useRef<SpeechSynthesis | null>(null);

  // App context hook to trigger Watch Live Demo if clicked
  let startLiveDemo: (() => void) | undefined;
  try {
    const app = useApp();
    startLiveDemo = app.startLiveDemo;
  } catch {
    startLiveDemo = undefined;
  }

  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      synthRef.current = window.speechSynthesis;
    }

    const hasSeenGuide =
      localStorage.getItem('brandprint_guide_seen') ||
      localStorage.getItem('brandprint_onboarding_completed');
    if (!hasSeenGuide) {
      setIsOpen(true);
    }

    const handleOpenGuide = () => {
      setCurrentStep(0);
      setIsOpen(true);
    };
    window.addEventListener('open-platform-guide', handleOpenGuide);
    return () => window.removeEventListener('open-platform-guide', handleOpenGuide);
  }, []);

  const speakCurrentStep = (stepIdx: number) => {
    if (!synthRef.current || !isVoiceEnabled) return;
    synthRef.current.cancel();

    const textToSpeak = steps[stepIdx].speechText;
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick a natural English voice if available
    const voices = synthRef.current.getVoices();
    const naturalVoice = voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        (v.name.includes('Natural') ||
          v.name.includes('Google') ||
          v.name.includes('Jenny') ||
          v.name.includes('Samantha'))
    );
    if (naturalVoice) {
      utterance.voice = naturalVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    synthRef.current.speak(utterance);
  };

  useEffect(() => {
    if (isOpen && isVoiceEnabled) {
      speakCurrentStep(currentStep);
    } else if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }

    return () => {
      if (synthRef.current) {
        synthRef.current.cancel();
      }
    };
  }, [currentStep, isOpen, isVoiceEnabled]);

  const handleClose = () => {
    if (synthRef.current) synthRef.current.cancel();
    localStorage.setItem('brandprint_guide_seen', 'true');
    localStorage.setItem('brandprint_onboarding_completed', 'true');
    setIsOpen(false);
  };

  const toggleVoicePreference = () => {
    const nextState = !isVoiceEnabled;
    setIsVoiceEnabled(nextState);
    localStorage.setItem('brandprint_voice_enabled', String(nextState));

    if (!nextState && synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  };

  const handleWatchLiveDemo = () => {
    handleClose();
    if (startLiveDemo) {
      startLiveDemo();
    }
  };

  if (!isOpen) return null;

  const step = steps[currentStep];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      id="welcome-guide-modal"
    >
      <div className="bg-white border border-slate-200 rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="bg-[#0B3C49] text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-white/10 rounded-2xl shadow-inner">{step.icon}</div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#F4A321]">
                {step.badge}
              </span>
              <h3 className="text-lg font-bold">{step.title}</h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Direct Voice Assistance ON/OFF Toggle */}
            <button
              onClick={toggleVoicePreference}
              className={`px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 text-xs font-semibold cursor-pointer ${
                isVoiceEnabled
                  ? 'bg-[#F4A321] text-slate-900 border-[#F4A321] shadow-sm'
                  : 'bg-white/10 text-white/80 border-white/20 hover:bg-white/20'
              }`}
              title={isVoiceEnabled ? 'Voice is ON (Click to Mute)' : 'Voice is OFF (Click to Listen)'}
              id="btn-toggle-voice"
            >
              {isVoiceEnabled ? (
                <>
                  <Volume2 className="w-4 h-4 animate-pulse text-slate-900" />
                  <span>Voice ON</span>
                </>
              ) : (
                <>
                  <VolumeX className="w-4 h-4 text-white/70" />
                  <span>Voice OFF</span>
                </>
              )}
            </button>

            <button
              onClick={handleClose}
              className="text-white/70 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
              title="Close guide"
              id="btn-close-welcome-guide"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Voice Narration Pill Status Bar */}
        <div className="px-6 py-2 bg-slate-100/70 border-b border-slate-200/60 flex items-center justify-between text-[11px] font-mono text-slate-600">
          <div className="flex items-center gap-2">
            {isSpeaking ? (
              <span className="flex items-center gap-1.5 text-emerald-700 font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                Audio Narration Playing
              </span>
            ) : isVoiceEnabled ? (
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Web Speech Synthesizer Ready
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-slate-300" />
                Narration Muted
              </span>
            )}
          </div>
          <span className="text-slate-400">SpeechSynthesis API</span>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 text-slate-700">
          <p className="text-sm font-medium leading-relaxed">{step.description}</p>
          <div className="space-y-2.5 bg-slate-50 p-4 rounded-2xl border border-slate-200/80">
            {step.details.map((item, idx) => (
              <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-600">
                <div className="w-1.5 h-1.5 rounded-full bg-teal-600 mt-1.5 flex-shrink-0" />
                <span>{item}</span>
              </div>
            ))}
          </div>

          {/* Quick Live Demo CTA on Step 1 */}
          {currentStep === 0 && startLiveDemo && (
            <div className="p-3 rounded-2xl bg-gradient-to-r from-[#0B3C49] to-[#144f60] text-white flex items-center justify-between gap-2 shadow-sm">
              <div className="space-y-0.5">
                <div className="flex items-center gap-1 text-[11px] font-bold text-[#F4A321]">
                  <Sparkles className="w-3.5 h-3.5" /> Autopilot Tour Available
                </div>
                <p className="text-[11px] text-slate-200">
                  Watch BrandPrint AI automatically demonstrate all features.
                </p>
              </div>
              <button
                type="button"
                onClick={handleWatchLiveDemo}
                className="px-3.5 py-1.5 rounded-xl bg-[#F4A321] hover:bg-amber-500 text-slate-900 font-bold text-xs flex items-center gap-1.5 transition-all active:scale-95 shrink-0 cursor-pointer shadow-xs"
                id="btn-welcome-guide-live-demo"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>WATCH LIVE DEMO</span>
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400">
            Step {currentStep + 1} of {steps.length}
          </span>
          <div className="flex items-center gap-2">
            {currentStep > 0 && (
              <button
                onClick={() => setCurrentStep((prev) => prev - 1)}
                className="px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200/60 rounded-xl transition-colors flex items-center gap-1 cursor-pointer"
                id="btn-welcome-guide-prev"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Back
              </button>
            )}
            {currentStep < steps.length - 1 ? (
              <button
                onClick={() => setCurrentStep((prev) => prev + 1)}
                className="px-4 py-1.5 text-xs font-semibold bg-[#0B3C49] text-white hover:bg-[#072730] rounded-xl transition-colors flex items-center gap-1 cursor-pointer active:scale-95 shadow-sm"
                id="btn-welcome-guide-next"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={handleClose}
                className="px-4 py-1.5 text-xs font-semibold bg-[#F4A321] text-slate-900 hover:bg-amber-400 rounded-xl transition-colors cursor-pointer active:scale-95 shadow-sm"
                id="btn-welcome-guide-finish"
              >
                Got it, Let's Start!
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WelcomeGuideModal;
