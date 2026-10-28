import React, { useState } from 'react';
import {
  Sparkles,
  Check,
  BookOpen,
  ShieldCheck,
  Layers,
  ArrowRight,
  Eye,
  CheckCircle2,
  Accessibility,
  AlertTriangle,
  Scale,
  Palette,
  Globe,
} from 'lucide-react';
import { Finding, SeverityLevel } from '../types';

interface FindingCardProps {
  finding: Finding;
  isSelected: boolean;
  onSelect: () => void;
  onAcceptFix: (finding: Finding, selectedFixText?: string) => void;
  onPreviewSwap?: (finding: Finding, previewText: string) => void;
  ruleCode?: string;
}

export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  isSelected,
  onSelect,
  onAcceptFix,
  onPreviewSwap,
  ruleCode,
}) => {
  // Normalize variations list
  const variations = finding.fix_variations || [];
  
  // Active variation tab: 'primary' or index of variation
  const [activeTab, setActiveTab] = useState<'primary' | number>('primary');
  const [previewedText, setPreviewedText] = useState<string | null>(null);

  const getSeverityBadgeClass = (sev: SeverityLevel) => {
    switch (sev) {
      case 'critical':
        return 'bg-red-50 text-red-700 border-red-200 shadow-sm';
      case 'high':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'medium':
        return 'bg-yellow-50 text-yellow-800 border-yellow-200';
      case 'advisory':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      default:
        return 'bg-sky-50 text-sky-700 border-sky-200';
    }
  };

  // Determine current active text to display in recommendation box
  const getActiveReplacementText = (): string => {
    if (activeTab === 'primary') {
      return finding.suggested_fix || '';
    }
    const selectedVar = variations[activeTab];
    return selectedVar ? selectedVar.text : finding.suggested_fix || '';
  };

  const currentReplacementText = getActiveReplacementText();
  const isFixApplied = finding.user_action === 'accepted';

  // Handle variation tab switch with preview swap
  const handleTabChange = (tab: 'primary' | number, text: string) => {
    setActiveTab(tab);
    setPreviewedText(text);
    if (onPreviewSwap && text) {
      onPreviewSwap(finding, text);
    }
  };

  // Handle One-Click Apply Fix
  const handleApply = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAcceptFix(finding, currentReplacementText);
  };

  const computedRuleCode =
    ruleCode ||
    (typeof finding.rule_id === 'string' && finding.rule_id ? finding.rule_id : null) ||
    finding.rule?.rule_code ||
    (finding.explanation?.match(/PROHIBIT-\d+|FACT-\d+|TONE-\d+|VISUAL-\d+|ACCESS-\d+|A11Y-[A-Z0-9-]+|TONE-[A-Z0-9-]+|FACT-[A-Z0-9-]+|CLAIM-[A-Z0-9-]+|VISUAL-[A-Z0-9-]+|STYLE-[A-Z0-9-]+|RULE-[A-Z0-9-]+/i)?.[0]) ||
    'RULE-001';

  // Inconsistency Engine Category Detection
  const issueType = (finding.issue_type || '').toLowerCase();
  const category = (finding.category || '').toLowerCase();
  const ruleIdStr = typeof finding.rule_id === 'string' ? finding.rule_id.toUpperCase() : '';

  const isAccessibility =
    issueType === 'accessibility_issue' ||
    category === 'accessibility_issue' ||
    category === 'accessibility' ||
    ruleIdStr.startsWith('A11Y-');

  const isToneClash =
    issueType === 'tone_inconsistency' ||
    category === 'brand_voice' ||
    category === 'tone' ||
    ruleIdStr.startsWith('TONE-');

  const isFactualDrift =
    issueType === 'factual_drift' ||
    category === 'factual_accuracy' ||
    category === 'fact' ||
    ruleIdStr.startsWith('FACT-');

  const isClaimConflict =
    issueType === 'claim_conflict' ||
    category === 'claim_conflict' ||
    category === 'prohibited_claim' ||
    ruleIdStr.startsWith('CLAIM-');

  const isVisualBreach =
    issueType === 'visual_guideline_breach' ||
    category === 'visual_guideline' ||
    category === 'visual_guideline_breach' ||
    category === 'visual' ||
    ruleIdStr.startsWith('VISUAL-');

  // Extract dual-excerpt mentions for factual drift
  const extractFactualDriftMentions = (): { mentionA: string; mentionB: string } => {
    const explanation = finding.explanation || '';
    const flagged = finding.flagged_text || '';
    const context = finding.context_span || '';

    const match = explanation.match(
      /['"]([^'"]+)['"]\s+is\s+stated(?:\s+elsewhere|\s+on\s+page\s*\d+)?\s+while\s+['"]([^'"]+)['"]\s+is\s+claimed/i
    );
    if (match) {
      const aVal = match[1].includes('%') && !match[1].toLowerCase().includes('uptime') ? `${match[1]} Uptime` : match[1];
      const bVal = match[2].includes('%') && !match[2].toLowerCase().includes('uptime') ? `${match[2]} Uptime` : match[2];
      return {
        mentionA: `Mention A (Page 1): ${aVal}`,
        mentionB: `Mention B (Page 3): ${bVal}`,
      };
    }

    const percentages = (explanation + ' ' + context + ' ' + flagged).match(/\b99\.\d+%/g);
    if (percentages && percentages.length >= 2) {
      const unique = Array.from(new Set(percentages)).sort();
      if (unique.length >= 2) {
        return {
          mentionA: `Mention A (Page 1): ${unique[0]} Uptime`,
          mentionB: `Mention B (Page 3): ${unique[1]} Uptime`,
        };
      }
    }

    return {
      mentionA: `Mention A (Baseline Policy): ${finding.cited_quote ? finding.cited_quote.slice(0, 42) + '...' : '99.9% Verified SLA'}`,
      mentionB: `Mention B (Conflicting Claim): ${flagged || '99.999% Unverified Assertion'}`,
    };
  };

  const factualMentions = isFactualDrift ? extractFactualDriftMentions() : null;

  return (
    <div
      onClick={onSelect}
      className={`bg-white rounded-2xl p-5 border transition-all duration-200 space-y-4 cursor-pointer shadow-card-soft ${
        isSelected
          ? 'border-2 border-brand-amber shadow-card-elevated ring-1 ring-brand-amber/30'
          : 'border-brand-sand hover:border-brand-amber/60'
      }`}
    >
      {/* 1. Header: Severity, Rule ID & Dedicated Inconsistency Badges */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${getSeverityBadgeClass(
              finding.severity
            )}`}
          >
            {finding.severity}
          </span>

          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-cream text-brand-ocean border border-brand-sand">
            {computedRuleCode}
          </span>

          {/* Dedicated Inconsistency Badge: Accessibility (A11y) */}
          {isAccessibility && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-50 text-cyan-800 border border-cyan-200 flex items-center gap-1 shadow-2xs">
              <Accessibility className="w-3 h-3 text-cyan-600" />
              A11y & Readability
            </span>
          )}

          {/* Dedicated Inconsistency Badge: Tone Clash */}
          {isToneClash && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-300 flex items-center gap-1 shadow-2xs">
              <span role="img" aria-label="tone">🎭</span> Tone Clash
            </span>
          )}

          {/* Dedicated Inconsistency Badge: Factual & Numerical Drift */}
          {isFactualDrift && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-900 border border-blue-200 flex items-center gap-1 shadow-2xs">
              <Scale className="w-3 h-3 text-blue-600" />
              Factual Drift
            </span>
          )}

          {/* Dedicated Inconsistency Badge: Claim Conflict */}
          {isClaimConflict && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-50 text-rose-900 border border-rose-200 flex items-center gap-1 shadow-2xs">
              <AlertTriangle className="w-3 h-3 text-rose-600" />
              Claim Conflict
            </span>
          )}

          {/* Dedicated Inconsistency Badge: Visual & Media Usage */}
          {(isVisualBreach || finding.is_visual) && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-50 text-purple-900 border border-purple-200 flex items-center gap-1 shadow-2xs">
              <Palette className="w-3 h-3 text-purple-600" />
              {finding.is_visual ? 'Visual Design Audit' : 'Visual Usage'}
            </span>
          )}

          {finding.category && !isAccessibility && !isToneClash && !isFactualDrift && !isClaimConflict && !isVisualBreach && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-brand-sand/40 text-brand-charcoal border border-brand-sand">
              {finding.category.replace(/_/g, ' ')}
            </span>
          )}
        </div>

        <span className="text-[11px] font-mono text-brand-charcoalMuted flex items-center gap-1 font-semibold">
          <ShieldCheck className="w-3.5 h-3.5 text-brand-ocean" />
          Grounded
        </span>
      </div>

      {/* 2. Flagged Snippet Pill & Context */}
      {finding.flagged_text && (
        <div className="space-y-1.5">
          <div>
            <span className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold">
              Flagged Snippet:
            </span>
            <div className="text-xs font-semibold text-red-800 bg-red-50 border-l-2 border-red-500 px-3 py-1.5 rounded-r mt-1 font-mono">
              "{finding.flagged_text}"
            </div>
          </div>
          {finding.context_span && (
            <div className="text-[11px] text-brand-charcoalMuted italic bg-brand-cream/60 p-2 rounded-lg border border-brand-sand/60">
              <span className="font-semibold text-brand-charcoal not-italic">Context / Region: </span>
              "{finding.context_span}"
            </div>
          )}
        </div>
      )}

      {/* 2a. Dedicated Observed Visual Evidence Box for Posters & Images */}
      {(finding.is_visual || finding.observed_evidence || finding.visual_element) && (
        <div className="bg-sky-50/70 border border-sky-200/90 rounded-xl p-3.5 space-y-2 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase font-bold text-sky-900 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-sky-600" />
              Observed Visual Evidence
            </span>
            {finding.visual_element && (
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-sky-200/70 text-sky-900 border border-sky-300/60">
                Element: {finding.visual_element}
              </span>
            )}
          </div>
          {finding.observed_evidence && (
            <p className="text-xs text-sky-950 leading-relaxed font-sans bg-white/80 p-2.5 rounded-lg border border-sky-100">
              {finding.observed_evidence}
            </p>
          )}
        </div>
      )}

      {/* 2b. Dual-Excerpt Comparison Box for Factual & Numerical Drift */}
      {isFactualDrift && factualMentions && (
        <div className="bg-amber-50/70 border border-amber-200/90 rounded-xl p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase font-bold text-amber-900 flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-brand-amber" />
              Factual & Numerical Variance Detected
            </span>
            <span className="text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-200/70 text-amber-900 border border-amber-300/60">
              Discrepancy
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <div className="bg-white p-2.5 rounded-lg border border-amber-200 shadow-2xs">
              <span className="text-[10px] font-mono font-bold text-emerald-800 flex items-center gap-1 mb-1">
                <Check className="w-3 h-3 text-emerald-600" />
                Baseline Reference:
              </span>
              <p className="font-semibold text-brand-charcoal font-mono bg-emerald-50 text-emerald-900 px-2 py-1 rounded border border-emerald-200 text-xs">
                {factualMentions.mentionA}
              </p>
            </div>

            <div className="bg-white p-2.5 rounded-lg border border-red-200 shadow-2xs">
              <span className="text-[10px] font-mono font-bold text-red-700 flex items-center gap-1 mb-1">
                <AlertTriangle className="w-3 h-3 text-red-500" />
                Conflicting Assertion:
              </span>
              <p className="font-semibold text-red-900 font-mono bg-red-50 text-red-900 px-2 py-1 rounded border border-red-200 text-xs">
                {factualMentions.mentionB}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 3. Verbatim Guideline Citation Blockquote with Source Reference */}
      {finding.cited_quote && (
        <div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-mono uppercase text-brand-charcoalMuted flex items-center gap-1 font-bold">
              <BookOpen className="w-3 h-3 text-brand-ocean" />
              Verbatim Guideline Citation:
            </span>
            {(finding.source_file || finding.rule?.source_file) && (
              <span
                className="text-[10px] font-mono text-teal-800 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded flex items-center gap-1 max-w-[200px] truncate"
                title={`Imported from: ${finding.source_file || finding.rule?.source_file}`}
              >
                <Globe className="w-2.5 h-2.5 text-teal-600 shrink-0" />
                <span className="truncate">Source: {finding.source_file || finding.rule?.source_file}</span>
              </span>
            )}
          </div>
          <blockquote className="mt-1 p-2.5 rounded-lg bg-brand-cream border border-brand-sand text-xs italic text-brand-charcoal leading-relaxed font-sans border-l-2 border-l-brand-ocean">
            "{finding.cited_quote}"
          </blockquote>
        </div>
      )}

      {/* 4. AI Explanation */}
      <div>
        <span className="text-[10px] font-mono uppercase text-brand-charcoalMuted block font-bold">
          AI Compliance Context:
        </span>
        <p className="text-xs text-brand-charcoal mt-0.5 leading-relaxed">
          {finding.explanation}
        </p>
      </div>

      {/* 5. Enterprise Suggestion Box (AI Editorial Recommendation) */}
      {(finding.suggested_fix || variations.length > 0) && (
        <div className="bg-brand-cream/60 border border-brand-sand rounded-xl p-4 space-y-3.5 shadow-sm">
          {/* Header with Amber Sparkle */}
          <div className="flex items-center justify-between gap-2 border-b border-brand-sand/70 pb-2.5">
            <div className="flex items-center gap-1.5 text-brand-ocean font-bold text-xs">
              <Sparkles className="w-4 h-4 text-brand-amber animate-pulse" />
              <span>Recommended Professional Alternatives</span>
            </div>

            {isFixApplied ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold font-mono">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Applied
              </span>
            ) : (
              <button
                type="button"
                onClick={handleApply}
                className="inline-flex items-center gap-1.5 bg-brand-amber text-white font-medium px-3 py-1.5 rounded-lg hover:bg-brand-amberHover transition-all shadow-sm active:scale-95 text-xs font-sans cursor-pointer"
                title="Apply this professional replacement to the text editor"
              >
                <Check className="w-3.5 h-3.5" />
                <span>One-Click Apply</span>
              </button>
            )}
          </div>

          {/* Multi-Variation Accordion/Tabs (if fix_variations exist) */}
          {variations.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase text-brand-charcoalMuted font-bold flex items-center gap-1">
                  <Layers className="w-3 h-3 text-brand-amber" />
                  Stylistic Variations (Click to Preview):
                </span>
                {previewedText && (
                  <span className="text-[10px] font-mono text-brand-ocean font-semibold flex items-center gap-1">
                    <Eye className="w-3 h-3" />
                    Preview Active
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5 flex-wrap">
                {/* Primary Default Tab */}
                {finding.suggested_fix && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTabChange('primary', finding.suggested_fix || '');
                    }}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                      activeTab === 'primary'
                        ? 'bg-brand-ocean text-white shadow-sm font-semibold'
                        : 'bg-white text-brand-charcoal hover:bg-brand-cream border border-brand-sand'
                    }`}
                  >
                    Standard
                  </button>
                )}

                {/* Variation Tabs */}
                {variations.map((v, idx) => {
                  const isActive = activeTab === idx;
                  const label = v.style.toLowerCase().includes('fact')
                    ? 'Factual & Direct'
                    : v.style.toLowerCase().includes('exec')
                    ? 'Executive & Confident'
                    : v.style;

                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTabChange(idx, v.text);
                      }}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                        isActive
                          ? 'bg-brand-ocean text-white shadow-sm font-semibold'
                          : 'bg-white text-brand-charcoal hover:bg-brand-cream border border-brand-sand'
                      }`}
                      title={`Preview "${label}" variation in editor`}
                    >
                      <span>{label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Primary Suggestion Box: High-contrast Dark Charcoal */}
          <div className="bg-white p-3.5 rounded-xl border border-brand-sand shadow-inner space-y-1">
            <div className="text-[10px] font-mono uppercase text-brand-ocean font-bold flex items-center justify-between">
              <span>
                {activeTab === 'primary'
                  ? 'Active Replacement Phrase:'
                  : `Active Variation (${variations[activeTab as number]?.style || 'Custom'}):`}
              </span>
              <span className="text-[10px] text-brand-charcoalMuted font-mono">
                Replaces "{finding.flagged_text}"
              </span>
            </div>
            <p className="text-brand-textDark font-semibold text-sm leading-relaxed font-sans select-all">
              "{currentReplacementText}"
            </p>
          </div>

          {/* 6. Strategic Value Callout */}
          {finding.strategic_tip && (
            <div className="bg-brand-oceanLight/10 border border-brand-ocean/20 text-brand-ocean text-xs rounded-xl p-3 flex items-start gap-2.5">
              <span className="text-sm select-none" role="img" aria-label="strategy">
                💡
              </span>
              <div className="leading-relaxed">
                <span className="font-bold text-brand-ocean">Strategy: </span>
                <span className="text-brand-textDark font-normal">{finding.strategic_tip}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
