import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  X,
  Lock,
  Zap,
  Fingerprint,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
} from 'lucide-react';
import { governanceApi } from '../../api/governance';
import { AITransparencyLog } from '../../types';

interface AITransparencyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AITransparencyModal: React.FC<AITransparencyModalProps> = ({ isOpen, onClose }) => {
  const [logs, setLogs] = useState<AITransparencyLog[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await governanceApi.getAITransparencyLogs(25);
      setLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Failed to load AI transparency audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-oceanDark/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white border border-brand-sand rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-card-elevated overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-brand-sand bg-brand-cream/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-ocean text-brand-amber flex items-center justify-center shadow-sm">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-brand-oceanDark flex items-center gap-2">
                AI Transparency & Model Audit Log
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-brand-amber/15 text-brand-amberHover border border-brand-amber/30">
                  Immutable Ledger
                </span>
              </h2>
              <p className="text-xs text-brand-charcoalMuted">
                Cryptographic SHA-256 prompt hashing, Local/Cloud egress guardrails, and PII redaction audit history.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="p-2 text-brand-charcoalMuted hover:text-brand-ocean hover:bg-brand-sand/50 rounded-lg transition-colors cursor-pointer"
              title="Refresh logs"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-brand-charcoalMuted hover:text-brand-charcoal hover:bg-brand-sand/50 rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3 bg-[#FBF9F4]">
          {loading && logs.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center text-center">
              <div className="w-8 h-8 border-3 border-brand-amber border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs font-mono text-brand-charcoalMuted">Querying AI disclosure records...</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="py-12 text-center bg-white border border-dashed border-brand-sand rounded-xl p-8">
              <ShieldCheck className="w-10 h-10 text-brand-sand mx-auto mb-2" />
              <p className="text-sm font-semibold text-brand-charcoal">No AI Transparency Events Logged Yet</p>
              <p className="text-xs text-brand-charcoalMuted mt-1">
                Run a content review in Review Studio to generate cryptographic audit entries.
              </p>
            </div>
          ) : (
            logs.map((log) => {
              const isLocal =
                log.service_provider.toLowerCase().includes('local') ||
                log.service_provider.toLowerCase().includes('ollama');

              return (
                <div
                  key={log.id}
                  className="bg-white border border-brand-sand rounded-xl p-4 shadow-card-soft hover:border-brand-ocean/30 transition-all text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-sand/60 pb-2.5 mb-2.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold ${
                          isLocal
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : 'bg-blue-50 text-blue-800 border border-blue-200'
                        }`}
                      >
                        {isLocal ? <Lock className="w-3 h-3" /> : <Zap className="w-3 h-3 text-amber-500" />}
                        {log.service_provider}
                      </span>
                      <span className="font-mono text-[11px] text-brand-charcoal font-semibold bg-brand-cream px-2 py-0.5 rounded border border-brand-sand">
                        {log.model_name}
                      </span>
                    </div>

                    <div className="text-[11px] font-mono text-brand-charcoalMuted">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Recent'}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Left details: redactions */}
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-brand-charcoalMuted font-medium">PII & Secret Guardrail:</span>
                        {log.redaction_applied ? (
                          <span className="inline-flex items-center gap-1 font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                            <AlertTriangle className="w-3 h-3 text-amber-600" />
                            {log.redactions_count} Redaction{log.redactions_count !== 1 ? 's' : ''} Applied
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            Zero PII Detected
                          </span>
                        )}
                      </div>

                      {log.redacted_fields && log.redacted_fields.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {log.redacted_fields.map((rf, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.5 bg-brand-sand/40 text-brand-charcoal font-mono text-[10px] rounded"
                            >
                              {rf}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className="text-[11px] text-brand-charcoalMuted">
                        Egress Volume:{' '}
                        <span className="font-mono font-semibold text-brand-charcoal">
                          {log.tokens_or_bytes_sent} bytes
                        </span>
                      </div>
                    </div>

                    {/* Right details: Prompt Hash */}
                    <div className="space-y-1 bg-brand-cream/50 p-2.5 rounded-lg border border-brand-sand/70">
                      <div className="flex items-center justify-between text-brand-charcoalMuted">
                        <span className="flex items-center gap-1 font-medium">
                          <Fingerprint className="w-3 h-3 text-brand-ocean" />
                          SHA-256 Digest:
                        </span>
                        <button
                          onClick={() => copyToClipboard(log.prompt_hash)}
                          className="flex items-center gap-1 text-[10px] font-mono text-brand-ocean hover:text-brand-oceanLight cursor-pointer"
                        >
                          {copiedHash === log.prompt_hash ? (
                            <>
                              <Check className="w-2.5 h-2.5 text-emerald-600" />
                              <span className="text-emerald-600">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-2.5 h-2.5" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                      <div className="font-mono text-[10px] text-brand-charcoal break-all select-all">
                        {log.prompt_hash}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-brand-sand bg-white flex items-center justify-between text-xs text-brand-charcoalMuted">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Active Guardrail Policy: Strict PII Redaction & Non-Egress Local Routing Enabled</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-brand-ocean text-white font-semibold hover:bg-brand-oceanLight transition-colors cursor-pointer text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default AITransparencyModal;

