import React, { useState, useEffect } from 'react';
import {
  History as HistoryIcon,
  Search,
  Filter,
  Download,
  Trash2,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  FileJson,
  RefreshCw,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiUrl } from '../config/api';

export const History = () => {
  const { addNotification } = useApp();
  const [logs, setLogs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [gestureFilter, setGestureFilter] = useState('ALL');
  const [page, setPage] = useState(0);
  const limit = 20;

  const [gesturesCatalog, setGesturesCatalog] = useState([]);

  useEffect(() => {
    fetch(apiUrl('/api/gestures/list'))
      .then(res => res.json())
      .then(data => {
        if (data.all_gestures) setGesturesCatalog(data.all_gestures);
      })
      .catch(() => {});
  }, []);

  const fetchHistory = async () => {
    try {
      const offset = page * limit;
      const url = `/api/history?limit=${limit}&offset=${offset}&query=${encodeURIComponent(searchQuery)}&gesture_filter=${encodeURIComponent(gestureFilter)}`;
      const res = await fetch(apiUrl(url));
      const data = await res.json();
      setLogs(data.items || []);
      setTotalCount(data.total || 0);
    } catch (e) {
      console.error('Failed to load history:', e);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, searchQuery, gestureFilter]);

  const handleDeleteItem = async (id) => {
    try {
      const res = await fetch(apiUrl(`/api/history/${id}`), { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        addNotification(`Deleted log #${id}`, 'info');
        fetchHistory();
      }
    } catch (e) {
      addNotification('Delete failed', 'error');
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to delete all historical gesture logs?')) {
      return;
    }
    try {
      const res = await fetch(apiUrl('/api/history'), { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        addNotification('All historical logs cleared', 'info');
        fetchHistory();
      }
    } catch (e) {
      addNotification('Clear failed', 'error');
    }
  };

  const totalPages = Math.ceil(totalCount / limit);

  return (
    <div className="space-y-6 sm:space-y-8 w-full">
      {/* Top Header Card */}
      <div className="glass-card rounded-3xl p-5 sm:p-8 border border-light-border dark:border-dark-border">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/15 text-primary text-xs font-bold uppercase tracking-wider mb-2">
              <HistoryIcon className="h-3.5 w-3.5" />
              SQLite Persistent Database
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white brand-font">
              Gesture Recognition History
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Logged instances with spatial confidence, handedness tags, and precise timestamps
            </p>
          </div>

          {/* Export & Actions Group */}
          <div className="flex flex-wrap items-center gap-2.5">
            <a
              href="/api/history/export?format=csv"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent/15 hover:bg-accent/25 border border-accent/40 text-accent font-bold text-xs transition-colors"
              download
            >
              <FileSpreadsheet className="h-4 w-4" />
              <span>Export CSV</span>
            </a>

            <a
              href="/api/history/export?format=json"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary/15 hover:bg-primary/25 border border-primary/40 text-primary font-bold text-xs transition-colors"
              download
            >
              <FileJson className="h-4 w-4" />
              <span>Export JSON</span>
            </a>

            <button
              onClick={handleClearAll}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-500 font-bold text-xs transition-colors"
            >
              <Trash2 className="h-4 w-4" />
              <span>Clear History</span>
            </button>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-2 relative">
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by gesture name or hand (e.g. 'Victory', 'Left')..."
              value={searchQuery}
              onChange={(e) => {
                setPage(0);
                setSearchQuery(e.target.value);
              }}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-light-border dark:border-dark-border text-xs font-medium text-slate-800 dark:text-white placeholder-slate-400 outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <select
              value={gestureFilter}
              onChange={(e) => {
                setPage(0);
                setGestureFilter(e.target.value);
              }}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-light-border dark:border-dark-border text-xs font-semibold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="ALL">All Gestures Filter</option>
              {gesturesCatalog.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* History Table Card */}
      <div className="glass-card rounded-3xl p-4 sm:p-8 border border-light-border dark:border-dark-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-light-border dark:border-dark-border text-[11px] font-bold uppercase tracking-wider text-slate-400">
                <th className="py-3 px-4"># ID</th>
                <th className="py-3 px-4">Gesture Recognized</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4">Hand Side</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-light-border dark:divide-dark-border text-sm">
              {logs.length > 0 ? (
                logs.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-400">
                      #{row.id}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-800 dark:text-white flex items-center gap-2">
                      <span className="text-lg">{row.icon || '✋'}</span>
                      <span>{row.gesture}</span>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-accent">
                      {Math.round(row.confidence <= 1 ? row.confidence * 100 : row.confidence)}%
                    </td>
                    <td className="py-3.5 px-4 text-xs font-semibold text-slate-500">
                      {row.hand_type} Hand
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-400">
                      {row.timestamp}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleDeleteItem(row.id)}
                        className="text-slate-400 hover:text-rose-500 transition-colors p-1"
                        title="Delete entry"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-xs text-slate-400">
                    No gesture records match the filter query.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="mt-6 pt-4 border-t border-light-border dark:border-dark-border flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {page * limit + 1} - {Math.min(totalCount, (page + 1) * limit)} of {totalCount} logs
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1.5 rounded-lg border border-light-border dark:border-dark-border disabled:opacity-30 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="font-mono font-bold">
                Page {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1.5 rounded-lg border border-light-border dark:border-dark-border disabled:opacity-30 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
