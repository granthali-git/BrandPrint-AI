import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  Search,
  Trash2,
  ExternalLink,
  RotateCcw,
  Sparkles,
  Columns,
  ScanSearch,
  Scale,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Filter,
  CheckCircle2,
  X,
  ArrowRight,
} from 'lucide-react';
import { historyApi } from '../api/history';
import { HistorySessionItem, HistorySessionDetail } from '../types';

type CategoryFilter = 'ALL' | 'AUDIT' | 'COMPARISON' | 'CONTRADICTION';

export const HistoryView: React.FC = () => {
  const navigate = useNavigate();

  const [sessions, setSessions] = useState<HistorySessionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>('ALL');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isClearModalOpen, setIsClearModalOpen] = useState<boolean>(false);
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Fetch history list from backend
  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const typeParam =
        selectedCategory === 'ALL'
          ? undefined
          : selectedCategory;
      const data = await historyApi.getHistoryList({
        search: searchQuery.trim() || undefined,
        type: typeParam,
        limit: 100,
      });
      setSessions(data || []);
    } catch (err: any) {
      console.warn('Failed to load audit history:', err);
      setError(
        err?.response?.data?.detail ||
        err?.message ||
        'Unable to load audit history. Please ensure backend is reachable.'
      );
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedCategory]);

  useEffect(() => {
    const handler = setTimeout(() => {
      fetchHistory();
    }, 250);
    return () => clearTimeout(handler);
  }, [fetchHistory]);

  // Handle restoring a session
  const handleRestoreSession = async (item: HistorySessionItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      showToast(`Restoring "${item.title}"...`);
      const detail: HistorySessionDetail = await historyApi.getHistoryDetail(item.id);

      if (detail.session_type === 'SINGLE_AUDIT') {
        navigate(`/studio?history_id=${detail.id}`, { state: { restoreSession: detail } });
      } else if (
        detail.session_type === 'DUAL_COMPARISON' ||
        detail.session_type === 'THREE_WAY_COMPARISON'
      ) {
        navigate(`/compare?history_id=${detail.id}`, { state: { restoreSession: detail } });
      } else if (detail.session_type === 'CONTRADICTION_CHECK') {
        navigate(`/audit?history_id=${detail.id}`, { state: { restoreSession: detail } });
      } else {
        navigate(`/studio?history_id=${detail.id}`, { state: { restoreSession: detail } });
      }
    } catch (err: any) {
      console.error('Failed to retrieve full session detail:', err);
      showToast('Error restoring session payload. Navigating to tool...');
      if (item.session_type.includes('COMPARISON')) {
        navigate(`/compare?history_id=${item.id}`);
      } else if (item.session_type === 'CONTRADICTION_CHECK') {
        navigate(`/audit?history_id=${item.id}`);
      } else {
        navigate(`/studio?history_id=${item.id}`);
      }
    }
  };

  // Delete individual record
  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletingId(id);
    try {
      await historyApi.deleteHistory(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      showToast('Session record deleted.');
    } catch (err: any) {
      console.error('Failed to delete history record:', err);
      showToast('Failed to delete history record.');
    } finally {
      setDeletingId(null);
    }
  };

  // Clear all history records
  const handleClearAllHistory = async () => {
    setIsClearing(true);
    try {
      await historyApi.clearAllHistory();
      setSessions([]);
      setIsClearModalOpen(false);
      showToast('Audit history cleared successfully.');
    } catch (err: any) {
      console.error('Failed to clear history:', err);
      showToast('Error clearing history.');
    } finally {
      setIsClearing(false);
    }
  };

  // Group items chronologically (Today, Yesterday, Previous 7 Days, Older)
  const groupedSessions = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const groups: {
      today: HistorySessionItem[];
      yesterday: HistorySessionItem[];
      previous7Days: HistorySessionItem[];
      older: HistorySessionItem[];
    } = {
      today: [],
      yesterday: [],
      previous7Days: [],
      older: [],
    };

    sessions.forEach((s) => {
      const sessionDate = new Date(s.created_at);
      if (sessionDate >= today) {
        groups.today.push(s);
      } else if (sessionDate >= yesterday) {
        groups.yesterday.push(s);
      } else if (sessionDate >= sevenDaysAgo) {
        groups.previous7Days.push(s);
      } else {
        groups.older.push(s);
      }
    });

    return groups;
  }, [sessions]);

  // Relative timestamp formatter
  const formatTimeAgo = (dateStr: string) => {
    try {
      const now = new Date();
      const past = new Date(dateStr);
      const diffMs = now.getTime() - past.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays}d ago`;
      return past.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  // Icon selector based on session type
  const renderSessionIcon = (type: string) => {
    switch (type) {
      case 'SINGLE_AUDIT':
        return (
          <div className="w-9 h-9 rounded-xl bg-teal-50 border border-teal-200 text-brand-ocean flex items-center justify-center shrink-0">
            <ScanSearch className="w-4 h-4" />
          </div>
        );
      case 'DUAL_COMPARISON':
      case 'THREE_WAY_COMPARISON':
        return (
          <div className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-200 text-brand-amber flex items-center justify-center shrink-0">
            <Columns className="w-4 h-4" />
          </div>
        );
      case 'CONTRADICTION_CHECK':
        return (
          <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center shrink-0">
            <Scale className="w-4 h-4" />
          </div>
        );
      default:
        return (
          <div className="w-9 h-9 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 flex items-center justify-center shrink-0">
            <FileText className="w-4 h-4" />
          </div>
        );
    }
  };

  // Badge label & badge color
  const renderTypeBadge = (type: string) => {
    switch (type) {
      case 'SINGLE_AUDIT':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-teal-50 text-teal-800 border border-teal-200 font-medium">
            Single Audit
          </span>
        );
      case 'DUAL_COMPARISON':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200 font-medium">
            Dual Comparison
          </span>
        );
      case 'THREE_WAY_COMPARISON':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-50 text-amber-900 border border-amber-300 font-medium">
            3-Way Comparison
          </span>
        );
      case 'CONTRADICTION_CHECK':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-800 border border-indigo-200 font-medium">
            Policy Audit
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-50 text-slate-700 border border-slate-200">
            {type}
          </span>
        );
    }
  };

  // Render individual session card
  const renderSessionCard = (item: HistorySessionItem) => {
    const isDeleting = deletingId === item.id;
    return (
      <div
        key={item.id}
        onClick={() => handleRestoreSession(item)}
        className="group relative bg-white rounded-2xl border border-brand-sand hover:border-brand-ocean/40 shadow-card-soft hover:shadow-card-hover transition-all p-4.5 cursor-pointer flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
      >
        <div className="flex items-start gap-3.5 flex-1 min-w-0">
          {renderSessionIcon(item.session_type)}

          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-bold text-brand-charcoal group-hover:text-brand-ocean transition-colors truncate">
                {item.title}
              </h3>
              {renderTypeBadge(item.session_type)}
            </div>

            {item.summary && (
              <p className="text-xs text-brand-charcoalMuted line-clamp-1">
                {item.summary}
              </p>
            )}

            <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <Clock className="w-3 h-3 text-slate-400" />
              <span>{formatTimeAgo(item.created_at)}</span>
              <span>•</span>
              <span className="truncate max-w-[200px]">ID: {item.id.slice(0, 8)}...</span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
          <button
            type="button"
            onClick={(e) => handleRestoreSession(item, e)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-cream hover:bg-brand-ocean hover:text-white text-brand-charcoal text-xs font-semibold border border-brand-sand transition-all group-hover:border-brand-ocean cursor-pointer"
            title="Restore exact inputs, findings, and scores"
          >
            <span>Restore Session</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            disabled={isDeleting}
            onClick={(e) => handleDeleteSession(item.id, e)}
            className="p-1.5 rounded-lg text-slate-300 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
            title="Delete this history record"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  };

  const totalSessionsCount = sessions.length;

  return (
    <div className="min-h-screen bg-[#FBF9F4] text-brand-charcoal pb-16">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-oceanDark text-white shadow-lg border border-brand-oceanLight/30 text-xs font-medium animate-in fade-in slide-in-from-bottom-3 duration-200">
          <CheckCircle2 className="w-4 h-4 text-brand-amber shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="bg-white border-b border-brand-sand px-6 py-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-brand-amber/15 text-brand-amber border border-brand-amber/30">
                <Clock className="w-5 h-5 text-brand-oceanDark" />
              </span>
              <h1 className="text-2xl font-extrabold tracking-tight text-brand-charcoal">
                Audit & Session History
              </h1>
            </div>
            <p className="text-sm text-brand-charcoalMuted max-w-2xl">
              Inspect past compliance evaluations, multi-asset comparative analyses, and policy contradiction audits.
              Click any item to immediately restore the full workspace without re-running AI model calls.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={fetchHistory}
              disabled={loading}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-brand-sand bg-white text-brand-charcoal hover:bg-brand-cream text-xs font-semibold transition-colors cursor-pointer"
              title="Refresh history sessions"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-brand-amber' : ''}`} />
              <span>Refresh</span>
            </button>

            {totalSessionsCount > 0 && (
              <button
                type="button"
                onClick={() => setIsClearModalOpen(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-rose-200 bg-rose-50/60 text-rose-700 hover:bg-rose-100 text-xs font-semibold transition-colors cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear All</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="max-w-7xl mx-auto px-6 py-6 space-y-4">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          {/* Search Box */}
          <div className="relative flex-1 max-w-lg">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search past audits, campaigns, or comparisons..."
              className="w-full pl-9.5 pr-8 py-2.5 rounded-xl border border-brand-sand bg-white text-sm text-brand-charcoal placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-ocean/30 focus:border-brand-ocean transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Category Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            {(
              [
                { id: 'ALL', label: 'All Sessions' },
                { id: 'AUDIT', label: 'Compliance Audits' },
                { id: 'COMPARISON', label: 'Comparisons' },
                { id: 'CONTRADICTION', label: 'Contradictions' },
              ] as const
            ).map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                  selectedCategory === cat.id
                    ? 'bg-brand-ocean text-white shadow-sm font-semibold'
                    : 'bg-white text-brand-charcoal border border-brand-sand hover:bg-brand-cream'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={fetchHistory}
              className="text-xs font-bold underline hover:text-rose-900"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="space-y-3 pt-2">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-20 bg-white rounded-2xl border border-brand-sand animate-pulse p-4 flex items-center gap-4"
              >
                <div className="w-10 h-10 rounded-xl bg-slate-100" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-slate-100 rounded w-1/3" />
                  <div className="h-3 bg-slate-100 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && totalSessionsCount === 0 && (
          <div className="bg-white rounded-2xl border border-brand-sand p-12 text-center max-w-lg mx-auto my-8 space-y-4 shadow-sm">
            <div className="w-14 h-14 rounded-2xl bg-brand-cream border border-brand-sand flex items-center justify-center mx-auto text-brand-ocean">
              <Clock className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-brand-charcoal">
                {searchQuery ? 'No matching audit records found' : 'No saved sessions yet'}
              </h3>
              <p className="text-xs text-brand-charcoalMuted">
                {searchQuery
                  ? `No previous sessions match "${searchQuery}". Try clearing your search filter.`
                  : 'Run an audit in Review Studio or compare variants in Asset Comparison to automatically record session history.'}
              </p>
            </div>
            <div className="pt-2 flex flex-wrap items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => navigate('/studio')}
                className="px-4 py-2 rounded-xl bg-brand-ocean text-white text-xs font-semibold hover:bg-brand-oceanDark transition-colors cursor-pointer"
              >
                Open Review Studio
              </button>
              <button
                type="button"
                onClick={() => navigate('/compare')}
                className="px-4 py-2 rounded-xl border border-brand-sand bg-white text-brand-charcoal text-xs font-semibold hover:bg-brand-cream transition-colors cursor-pointer"
              >
                Open Asset Comparison
              </button>
            </div>
          </div>
        )}

        {/* Grouped Chronological History List */}
        {!loading && totalSessionsCount > 0 && (
          <div className="space-y-6 pt-2">
            {groupedSessions.today.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 px-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-brand-charcoalMuted">
                    Today
                  </span>
                  <div className="flex-1 h-px bg-brand-sand" />
                  <span className="text-[11px] font-mono text-slate-400">
                    {groupedSessions.today.length} {groupedSessions.today.length === 1 ? 'session' : 'sessions'}
                  </span>
                </div>
                <div className="space-y-2.5">
                  {groupedSessions.today.map(renderSessionCard)}
                </div>
              </div>
            )}

            {groupedSessions.yesterday.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 px-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-brand-charcoalMuted">
                    Yesterday
                  </span>
                  <div className="flex-1 h-px bg-brand-sand" />
                  <span className="text-[11px] font-mono text-slate-400">
                    {groupedSessions.yesterday.length} {groupedSessions.yesterday.length === 1 ? 'session' : 'sessions'}
                  </span>
                </div>
                <div className="space-y-2.5">
                  {groupedSessions.yesterday.map(renderSessionCard)}
                </div>
              </div>
            )}

            {groupedSessions.previous7Days.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 px-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-brand-charcoalMuted">
                    Previous 7 Days
                  </span>
                  <div className="flex-1 h-px bg-brand-sand" />
                  <span className="text-[11px] font-mono text-slate-400">
                    {groupedSessions.previous7Days.length} {groupedSessions.previous7Days.length === 1 ? 'session' : 'sessions'}
                  </span>
                </div>
                <div className="space-y-2.5">
                  {groupedSessions.previous7Days.map(renderSessionCard)}
                </div>
              </div>
            )}

            {groupedSessions.older.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 px-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-brand-charcoalMuted">
                    Older
                  </span>
                  <div className="flex-1 h-px bg-brand-sand" />
                  <span className="text-[11px] font-mono text-slate-400">
                    {groupedSessions.older.length} {groupedSessions.older.length === 1 ? 'session' : 'sessions'}
                  </span>
                </div>
                <div className="space-y-2.5">
                  {groupedSessions.older.map(renderSessionCard)}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Clear All Confirmation Modal */}
      {isClearModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl border border-brand-sand shadow-2xl max-w-md w-full p-6 space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-rose-600">
              <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-brand-charcoal">Clear All Audit History?</h3>
                <p className="text-xs text-brand-charcoalMuted">This action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              All persisted compliance reviews, 3-way comparisons, and contradiction audits will be permanently erased.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setIsClearModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-brand-sand text-xs font-semibold text-brand-charcoal hover:bg-brand-cream transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isClearing}
                onClick={handleClearAllHistory}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
              >
                {isClearing ? 'Clearing...' : 'Yes, Clear All History'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryView;
