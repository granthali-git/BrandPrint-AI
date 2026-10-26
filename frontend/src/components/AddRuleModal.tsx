import React, { useState } from 'react';
import { X, Plus, AlertCircle, Loader2, Sparkles, BookOpen } from 'lucide-react';
import { api } from '../api/client';
import { RuleCategory } from '../types';

export interface AddRuleModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeBrandId?: number | string;
  onRuleCreated?: (rule: any) => void;
}

export const AddRuleModal: React.FC<AddRuleModalProps> = ({
  isOpen,
  onClose,
  activeBrandId = 1,
  onRuleCreated,
}) => {
  const [ruleCode, setRuleCode] = useState('');
  const [title, setTitle] = useState('');
  const [ruleText, setRuleText] = useState('');
  const [category, setCategory] = useState<string>('Tone of Voice');
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !ruleText.trim()) {
      setErrorMessage('Please provide both Rule Title and Enforceable Rule Text.');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    // Payload Normalization: sanitize category strings to snake_case
    const payload = {
      brand_id: activeBrandId || 1,
      rule_code: ruleCode.trim() || `RULE-${Date.now().toString().slice(-4)}`,
      title: title.trim(),
      rule_text: ruleText.trim(),
      category: category.toLowerCase().replace(/\s+/g, '_'), // e.g. "Prohibited Claim" -> "prohibited_claim"
    };

    try {
      const response = await api.post('/api/guidelines', payload);
      const createdRule = response.data;
      if (onRuleCreated) {
        onRuleCreated(createdRule);
      }
      // Reset form
      setRuleCode('');
      setTitle('');
      setRuleText('');
      setCategory('Tone of Voice');
      onClose();
    } catch (err: any) {
      console.error('Failed to create rule:', err);
      // Dynamic Error Display: show specific constraint or validation error
      setErrorMessage(err?.message || err?.response?.data?.detail || 'Failed to create rule.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-oceanDark/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-xl flex flex-col rounded-2xl bg-white border border-brand-sand shadow-card-elevated text-brand-charcoal animate-in zoom-in-95 duration-150 overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-brand-sand">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-ocean text-white flex items-center justify-center shadow-sm">
              <BookOpen className="w-5 h-5 text-brand-amber" />
            </div>
            <div>
              <h3 className="text-base font-bold text-brand-charcoal">
                Add Enforceable Guideline Rule
              </h3>
              <p className="text-xs text-brand-charcoalMuted">
                Rule will be vectorized into FAISS and evaluated during compliance scans.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Dynamic Error Display */}
          {errorMessage && (
            <div
              className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5 animate-in fade-in duration-150"
              id="rule-modal-error-banner"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">
                {errorMessage || 'Failed to create rule.'}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-xl bg-brand-cream border border-brand-sand px-3 py-2 text-xs text-brand-charcoal focus:outline-none focus:ring-1 focus:ring-brand-amber"
              >
                <option value="Tone of Voice">Tone of Voice</option>
                <option value="Prohibited Claim">Prohibited Claim</option>
                <option value="Legal Compliance">Legal Compliance</option>
                <option value="Brand Voice">Brand Voice</option>
                <option value="Visual Design">Visual & Design</option>
                <option value="Fact Certification">Fact & Certification</option>
                <option value="Accessibility WCAG">Accessibility & WCAG</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
                Rule Code (Optional)
              </label>
              <input
                type="text"
                value={ruleCode}
                onChange={(e) => setRuleCode(e.target.value)}
                placeholder="e.g. CLAIM-001"
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
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. No Unsubstantiated Uptime Guarantees"
              className="w-full rounded-xl bg-brand-cream border border-brand-sand px-3 py-2 text-xs text-brand-charcoal focus:outline-none focus:ring-1 focus:ring-brand-amber font-semibold"
            />
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-brand-charcoalMuted font-bold mb-1">
              Enforceable Rule Text
            </label>
            <textarea
              value={ruleText}
              onChange={(e) => setRuleText(e.target.value)}
              rows={3}
              placeholder="Exact imperative statement (e.g. Never claim to be the number one or cheapest brand without verified audit proof)..."
              className="w-full rounded-xl bg-brand-cream border border-brand-sand p-3 text-xs text-brand-charcoal font-mono focus:outline-none focus:ring-1 focus:ring-brand-amber leading-relaxed"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-brand-sand">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-cream transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-amber hover:bg-brand-amberHover text-white text-xs font-bold shadow-sm transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
              id="btn-submit-add-rule-modal"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 text-white" />
              )}
              <span>Save Rule to Codex</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddRuleModal;
