import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Bot,
  Play,
  FileText,
  Download,
  Copy,
  Check,
  RefreshCw,
  ShieldCheck,
  AlertTriangle,
  Settings,
  Plus,
  Trash2,
  ExternalLink,
  Search,
  Database,
  Send,
  BookOpen,
} from 'lucide-react';

export default function FlerkenBotView() {
  const [data, setData] = useState({
    bot_status: { is_running: false, status: 'idle', last_run: null, error: null },
    config: { publication: {}, collection: {}, sources: [] },
    seen_count: 0,
    latest_markdown: '',
    latest_filename: null,
    verified_jobs: [],
    review_queue: [],
    issues: [],
  });
  const [loading, setLoading] = useState(true);
  const [subTab, setSubTab] = useState('issue'); // 'issue' | 'verified' | 'review' | 'sources'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [ignoreSeen, setIgnoreSeen] = useState(false);
  const [earlyCareerOnly, setEarlyCareerOnly] = useState(true);
  const [maxJobs, setMaxJobs] = useState(60);
  const [copied, setCopied] = useState(false);
  const [draftFeedback, setDraftFeedback] = useState(null);

  // New source form state
  const [newSourceType, setNewSourceType] = useState('greenhouse');
  const [newSourceName, setNewSourceName] = useState('');
  const [newSourceToken, setNewSourceToken] = useState('');
  const [newSourceKind, setNewSourceKind] = useState('aggregator');

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch('/api/flerken-bot/state');
      if (res.ok) {
        const json = await res.json();
        setData(json);
        if (json.config?.collection?.max_jobs_per_issue) {
          setMaxJobs(json.config.collection.max_jobs_per_issue);
        }
      }
    } catch (err) {
      console.error('Error loading Flerken Studio Bot state:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  // Poll while bot is running
  useEffect(() => {
    if (!data.bot_status?.is_running) return;
    const timer = setInterval(() => {
      fetchState();
    }, 2000);
    return () => clearInterval(timer);
  }, [data.bot_status?.is_running, fetchState]);

  const handleRunBot = async () => {
    setDraftFeedback(null);
    try {
      const res = await fetch('/api/flerken-bot/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ignore_seen: ignoreSeen,
          max_jobs: Number(maxJobs) || 60,
          early_career_only: earlyCareerOnly,
          create_draft: false,
        }),
      });
      if (res.ok) {
        setData((prev) => ({
          ...prev,
          bot_status: { ...prev.bot_status, is_running: true, status: 'running', error: null },
        }));
      }
    } catch (err) {
      console.error('Failed to start Flerken bot:', err);
    }
  };

  const handleResetSeen = async () => {
    try {
      const res = await fetch('/api/flerken-bot/reset-seen', { method: 'POST' });
      if (res.ok) {
        await fetchState();
      }
    } catch (err) {
      console.error('Failed to reset seen store:', err);
    }
  };

  const [showAuthModal, setShowAuthModal] = useState(false);
  const [cookieInput, setCookieInput] = useState('');

  const handleCreateSubstackDraft = async (customCookie = null) => {
    setDraftFeedback({ type: 'info', text: 'Creating unpublished draft on Substack...' });
    try {
      const res = await fetch('/api/flerken-bot/create-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cookies_string: typeof customCookie === 'string' ? customCookie : null,
        }),
      });
      const json = await res.json();
      if (res.ok) {
        setShowAuthModal(false);
        setCookieInput('');
        setDraftFeedback({ type: 'success', text: json.message || 'Unpublished Substack draft created!' });
      } else if (json.auth_required) {
        if (data.latest_markdown) {
          navigator.clipboard.writeText(data.latest_markdown);
          setCopied(true);
          setTimeout(() => setCopied(false), 3000);
        }
        setDraftFeedback(null);
        setShowAuthModal(true);
      } else {
        setDraftFeedback({
          type: 'error',
          text: json.error || 'Could not create Substack draft. Check python-substack CLI & credentials.',
        });
      }
    } catch (err) {
      setDraftFeedback({ type: 'error', text: String(err) });
    }
  };

  const handleToggleSource = async (index, currentEnabled) => {
    try {
      const res = await fetch('/api/flerken-bot/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'toggle', index, enabled: !currentEnabled }),
      });
      if (res.ok) {
        await fetchState();
      }
    } catch (err) {
      console.error('Error toggling source:', err);
    }
  };

  const handleDeleteSource = async (index) => {
    try {
      const res = await fetch('/api/flerken-bot/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'delete', index }),
      });
      if (res.ok) {
        await fetchState();
      }
    } catch (err) {
      console.error('Error deleting source:', err);
    }
  };

  const handleAddSource = async (e) => {
    e.preventDefault();
    if (!newSourceName.trim() || !newSourceToken.trim()) return;
    const sourceObj = {
      type: newSourceType,
      name: newSourceName.trim(),
      enabled: true,
    };
    if (newSourceType === 'greenhouse') {
      sourceObj.board = newSourceToken.trim();
    } else if (newSourceType === 'lever') {
      sourceObj.site = newSourceToken.trim();
    } else {
      sourceObj.url = newSourceToken.trim();
      sourceObj.kind = newSourceKind;
    }

    try {
      const res = await fetch('/api/flerken-bot/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add', source: sourceObj }),
      });
      if (res.ok) {
        setNewSourceName('');
        setNewSourceToken('');
        await fetchState();
      }
    } catch (err) {
      console.error('Error adding source:', err);
    }
  };

  const handleCopyMarkdown = () => {
    if (!data.latest_markdown) return;
    navigator.clipboard.writeText(data.latest_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sources = data.config?.sources || [];
  const enabledSourcesCount = sources.filter((s) => s.enabled).length;
  const verifiedJobs = data.verified_jobs || [];
  const reviewQueue = data.review_queue || [];

  const categories = useMemo(() => {
    const set = new Set();
    verifiedJobs.forEach((j) => {
      if (j.category) set.add(j.category);
    });
    return ['All', ...Array.from(set)];
  }, [verifiedJobs]);

  const filteredVerifiedJobs = useMemo(() => {
    return verifiedJobs.filter((j) => {
      if (selectedCategory !== 'All' && j.category !== selectedCategory) return false;
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        (j.title || '').toLowerCase().includes(q) ||
        (j.company || '').toLowerCase().includes(q) ||
        (j.location || '').toLowerCase().includes(q) ||
        (j.category || '').toLowerCase().includes(q)
      );
    });
  }, [verifiedJobs, selectedCategory, searchQuery]);

  const isRunning = data.bot_status?.is_running;

  return (
    <div className="flex-1 flex flex-col bg-gray-50 overflow-hidden">
      {/* ── Top Action & Telemetry Bar ─────────────────── */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-violet-100 text-violet-700">
              <Bot size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-gray-900">
                  Flerken Studio Bot ({data.config?.publication?.brand || 'InternAtlas'})
                </h2>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-200">
                  flerkenstudio.substack.com
                </span>
              </div>
              <p className="text-xs text-gray-500">
                Automated Greenhouse, Lever &amp; RSS collector with live HTTP link verification, SQLite deduplication &amp; Review Queue
              </p>
            </div>
          </div>

          <div className="h-8 w-px bg-gray-200 hidden md:block" />

          {/* Metrics */}
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-[11px] text-gray-500 block font-medium">Enabled Sources</span>
              <span className="text-lg font-bold text-violet-700">
                {enabledSourcesCount} <span className="text-xs text-gray-400 font-normal">/ {sources.length}</span>
              </span>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 block font-medium">Verified Issue Jobs</span>
              <span className="text-lg font-bold text-emerald-600">{verifiedJobs.length}</span>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 block font-medium">Review Queue</span>
              <span className="text-lg font-bold text-amber-600">{reviewQueue.length}</span>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 block font-medium">Seen Ledger (SQLite)</span>
              <div className="flex items-center gap-1.5">
                <span className="text-lg font-bold text-gray-800">{data.seen_count}</span>
                {data.seen_count > 0 && (
                  <button
                    onClick={handleResetSeen}
                    title="Clear state/seen.sqlite3 so previously drafted jobs can be included again"
                    className="text-[10px] text-rose-600 hover:underline font-semibold cursor-pointer"
                  >
                    Reset
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <label className="flex items-center gap-1.5 text-xs text-gray-700 bg-gray-100 px-2.5 py-1.5 rounded-lg cursor-pointer select-none">
            <input
              type="checkbox"
              checked={earlyCareerOnly}
              onChange={(e) => setEarlyCareerOnly(e.target.checked)}
              className="rounded text-violet-600"
            />
            <span>Early-Career Only</span>
          </label>

          <label className="flex items-center gap-1.5 text-xs text-gray-700 bg-gray-100 px-2.5 py-1.5 rounded-lg cursor-pointer select-none">
            <input
              type="checkbox"
              checked={ignoreSeen}
              onChange={(e) => setIgnoreSeen(e.target.checked)}
              className="rounded text-violet-600"
            />
            <span>Ignore Seen Ledger</span>
          </label>

          <button
            onClick={handleRunBot}
            disabled={isRunning}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold text-white shadow-2xs transition-all cursor-pointer ${
              isRunning ? 'bg-violet-400 cursor-not-allowed' : 'bg-violet-600 hover:bg-violet-700 active:scale-98'
            }`}
          >
            <Play size={14} fill="currentColor" className={isRunning ? 'animate-pulse' : ''} />
            {isRunning ? 'Running Bot & Verifying Links…' : 'Run Flerken Bot'}
          </button>

          <a
            href="/api/flerken-bot/download/md"
            className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-900 text-white px-3 py-2 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
          >
            <Download size={14} /> .MD Issue
          </a>

          <a
            href="/api/flerken-bot/download/docx"
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
          >
            <FileText size={14} /> Word (.docx)
          </a>

          <button
            onClick={handleCreateSubstackDraft}
            disabled={!data.latest_markdown || isRunning}
            className="flex items-center gap-1.5 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white px-3 py-2 rounded-lg text-xs font-semibold shadow-2xs transition-colors cursor-pointer"
            title="Create an unpublished draft on flerkenstudio.substack.com via python-substack CLI"
          >
            <Send size={13} /> Substack Draft
          </button>
        </div>
      </div>

      {/* Status / Feedback Banner */}
      {(isRunning || data.bot_status?.error || draftFeedback) && (
        <div className="px-6 pt-3">
          {isRunning && (
            <div className="bg-violet-50 border border-violet-200 text-violet-800 px-4 py-2.5 rounded-lg text-xs flex items-center gap-2">
              <RefreshCw size={14} className="animate-spin text-violet-600" />
              <span>
                Collecting from {enabledSourcesCount} enabled boards, verifying official employer URLs via HTTP, and rendering newsletter issue…
              </span>
            </div>
          )}
          {data.bot_status?.error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-xs flex items-center gap-2 mt-1">
              <AlertTriangle size={14} />
              <span>Bot Error: {data.bot_status.error}</span>
            </div>
          )}
          {draftFeedback && (
            <div
              className={`px-4 py-2.5 rounded-lg text-xs flex items-center justify-between mt-1 border ${
                draftFeedback.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : draftFeedback.type === 'error'
                  ? 'bg-amber-50 border-amber-200 text-amber-900'
                  : 'bg-blue-50 border-blue-200 text-blue-800'
              }`}
            >
              <span>{draftFeedback.text}</span>
              <button onClick={() => setDraftFeedback(null)} className="text-xs font-bold ml-4 cursor-pointer">
                ✕
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Sub-Tab Navigation ─────────────────────────── */}
      <div className="px-6 pt-3 flex items-center justify-between border-b border-gray-200 bg-white">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSubTab('issue')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              subTab === 'issue'
                ? 'border-violet-600 text-violet-700 bg-violet-50/40'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <BookOpen size={14} />
            Latest Newsletter Issue (.md)
          </button>
          <button
            onClick={() => setSubTab('verified')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              subTab === 'verified'
                ? 'border-emerald-600 text-emerald-700 bg-emerald-50/40'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <ShieldCheck size={14} />
            Verified Official Jobs ({verifiedJobs.length})
          </button>
          <button
            onClick={() => setSubTab('review')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              subTab === 'review'
                ? 'border-amber-600 text-amber-700 bg-amber-50/40'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <AlertTriangle size={14} />
            Review Queue ({reviewQueue.length})
          </button>
          <button
            onClick={() => setSubTab('sources')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              subTab === 'sources'
                ? 'border-blue-600 text-blue-700 bg-blue-50/40'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <Settings size={14} />
            Sources &amp; Config ({sources.length})
          </button>
        </div>

        {data.latest_filename && (
          <span className="text-[11px] text-gray-400 font-mono pb-2">
            Latest file: {data.latest_filename}
          </span>
        )}
      </div>

      {/* ── Main Content Area ──────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-6">
        {subTab === 'issue' && (
          <div className="max-w-5xl mx-auto bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
            <div className="bg-gray-50 px-5 py-3 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-gray-800">
                  {data.latest_filename || 'Generated Substack Issue Markdown'}
                </h3>
                <p className="text-[11px] text-gray-500">
                  Ready to paste into Substack or download as Markdown (.md) / Word (.docx)
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyMarkdown}
                  disabled={!data.latest_markdown}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-gray-300 hover:bg-gray-100 text-gray-700 cursor-pointer"
                >
                  {copied ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
                  {copied ? 'Copied Markdown!' : 'Copy Markdown'}
                </button>
              </div>
            </div>

            {data.latest_markdown ? (
              <div className="p-6">
                <pre className="whitespace-pre-wrap font-mono text-xs text-gray-800 bg-gray-50 p-5 rounded-xl border border-gray-200 leading-relaxed max-h-[65vh] overflow-y-auto">
                  {data.latest_markdown}
                </pre>
              </div>
            ) : (
              <div className="p-12 text-center">
                <Bot size={40} className="mx-auto text-violet-400 mb-3" />
                <h4 className="text-base font-bold text-gray-800 mb-1">No Newsletter Issue Generated Yet</h4>
                <p className="text-xs text-gray-500 max-w-md mx-auto mb-4">
                  Click <strong>Run Flerken Bot</strong> above to fetch roles from enabled Greenhouse &amp; Lever boards, verify all application links via HTTP, and generate your Substack Markdown &amp; Word issue.
                </p>
                <button
                  onClick={handleRunBot}
                  disabled={isRunning}
                  className="inline-flex items-center gap-1.5 bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-lg text-xs font-bold cursor-pointer"
                >
                  <Play size={14} fill="currentColor" /> Run Flerken Bot Now
                </button>
              </div>
            )}
          </div>
        )}

        {subTab === 'verified' && (
          <div className="space-y-4">
            <div className="bg-white p-3 rounded-xl border border-gray-200 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 overflow-x-auto">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap cursor-pointer ${
                      selectedCategory === cat
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
              <div className="relative min-w-[240px]">
                <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search title, company, city…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-2xs">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-100 text-gray-700 border-b border-gray-200">
                    <th className="py-2.5 px-4 font-bold">#</th>
                    <th className="py-2.5 px-4 font-bold">Role Title</th>
                    <th className="py-2.5 px-4 font-bold">Company</th>
                    <th className="py-2.5 px-4 font-bold">Category</th>
                    <th className="py-2.5 px-4 font-bold">Location</th>
                    <th className="py-2.5 px-4 font-bold">Work Mode</th>
                    <th className="py-2.5 px-4 font-bold">Verification</th>
                    <th className="py-2.5 px-4 font-bold">Official Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredVerifiedJobs.map((job, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="py-2.5 px-4 text-gray-400 font-mono">{idx + 1}</td>
                      <td className="py-2.5 px-4 font-semibold text-gray-900">{job.title}</td>
                      <td className="py-2.5 px-4 font-medium text-violet-700">{job.company}</td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded-full text-[11px] bg-blue-50 text-blue-700 font-medium">
                          {job.category}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-gray-600">{job.location}</td>
                      <td className="py-2.5 px-4 text-gray-600">{job.work_mode}</td>
                      <td className="py-2.5 px-4">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-emerald-50 text-emerald-700 font-semibold">
                          <ShieldCheck size={12} /> {job.verification_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4">
                        <a
                          href={job.official_url || job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-blue-600 hover:underline font-semibold"
                        >
                          Apply <ExternalLink size={12} />
                        </a>
                      </td>
                    </tr>
                  ))}
                  {filteredVerifiedJobs.length === 0 && (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-gray-400">
                        No verified jobs match the current filter. Run the bot to collect fresh listings.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {subTab === 'review' && (
          <div className="space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-amber-900">
                  Safety Gate: Unverified / Aggregator Candidates (`output/review_queue.json`)
                </h3>
                <p className="text-xs text-amber-800">
                  Flerken Studio Bot never publishes aggregator-only links or broken HTTP links as verified opportunities. They are held here for manual inspection.
                </p>
              </div>
              <a
                href="/api/flerken-bot/download/review"
                className="flex items-center gap-1.5 bg-amber-700 hover:bg-amber-800 text-white px-3 py-1.5 rounded-lg text-xs font-semibold"
              >
                <Download size={13} /> review_queue.json
              </a>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-2xs">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-100 text-gray-700 border-b border-gray-200">
                    <th className="py-2.5 px-4 font-bold">#</th>
                    <th className="py-2.5 px-4 font-bold">Title</th>
                    <th className="py-2.5 px-4 font-bold">Company / Source</th>
                    <th className="py-2.5 px-4 font-bold">Status</th>
                    <th className="py-2.5 px-4 font-bold">Verification Note</th>
                    <th className="py-2.5 px-4 font-bold">Candidate URL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {reviewQueue.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="py-2.5 px-4 text-gray-400 font-mono">{idx + 1}</td>
                      <td className="py-2.5 px-4 font-semibold text-gray-900">{item.title}</td>
                      <td className="py-2.5 px-4 text-gray-700">{item.company}</td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded-full text-[11px] bg-amber-100 text-amber-800 font-semibold">
                          {item.verification_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-gray-600">{item.verification_note}</td>
                      <td className="py-2.5 px-4">
                        {item.url ? (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-600 hover:underline"
                          >
                            Inspect <ExternalLink size={12} />
                          </a>
                        ) : (
                          <span className="text-gray-400">N/A</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {reviewQueue.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-gray-400">
                        Review queue is empty — all checked candidate links passed verification!
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {subTab === 'sources' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Add New Source Card */}
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-2xs h-fit">
              <h3 className="text-sm font-bold text-gray-900 mb-1 flex items-center gap-1.5">
                <Plus size={16} className="text-violet-600" /> Add Source to `config/sources.yaml`
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                Add a public Greenhouse board token, Lever site slug, or RSS/Atom feed.
              </p>

              <form onSubmit={handleAddSource} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Adapter Type</label>
                  <select
                    value={newSourceType}
                    onChange={(e) => setNewSourceType(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-white"
                  >
                    <option value="greenhouse">Greenhouse (Official Employer Board)</option>
                    <option value="lever">Lever (Official Employer Postings)</option>
                    <option value="rss">RSS / Atom Feed</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Company / Source Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Stripe, Postman, Razorpay"
                    value={newSourceName}
                    onChange={(e) => setNewSourceName(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    required
                  />
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-1">
                    {newSourceType === 'greenhouse'
                      ? 'Greenhouse Board Token'
                      : newSourceType === 'lever'
                      ? 'Lever Site Slug'
                      : 'RSS / Atom Feed URL'}
                  </label>
                  <input
                    type="text"
                    placeholder={
                      newSourceType === 'greenhouse'
                        ? 'e.g. stripe'
                        : newSourceType === 'lever'
                        ? 'e.g. cred'
                        : 'https://example.com/jobs.rss'
                    }
                    value={newSourceToken}
                    onChange={(e) => setNewSourceToken(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 font-mono"
                    required
                  />
                </div>

                {newSourceType === 'rss' && (
                  <div>
                    <label className="block font-semibold text-gray-700 mb-1">Feed Kind</label>
                    <select
                      value={newSourceKind}
                      onChange={(e) => setNewSourceKind(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-white"
                    >
                      <option value="aggregator">Aggregator (Held in Review Queue unless official_url tag exists)</option>
                      <option value="official">Official Employer Feed</option>
                    </select>
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full bg-violet-600 hover:bg-violet-700 text-white font-bold py-2 rounded-lg transition-colors cursor-pointer"
                >
                  + Add Source to YAML
                </button>
              </form>
            </div>

            {/* Configured Sources Table */}
            <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
              <div className="px-5 py-3.5 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Configured Sources (`flerken-studio-bot/config/sources.yaml`)</h3>
                  <p className="text-[11px] text-gray-500">
                    Toggle boards on/off or remove placeholder sources
                  </p>
                </div>
                <span className="text-xs font-semibold text-violet-700">
                  {enabledSourcesCount} Enabled / {sources.length} Total
                </span>
              </div>

              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-100 text-gray-700 border-b border-gray-200">
                    <th className="py-2.5 px-4 font-bold">Enabled</th>
                    <th className="py-2.5 px-4 font-bold">Type</th>
                    <th className="py-2.5 px-4 font-bold">Company / Name</th>
                    <th className="py-2.5 px-4 font-bold">Board / Site / Feed URL</th>
                    <th className="py-2.5 px-4 font-bold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {sources.map((src, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="py-2.5 px-4">
                        <input
                          type="checkbox"
                          checked={Boolean(src.enabled)}
                          onChange={() => handleToggleSource(idx, Boolean(src.enabled))}
                          className="rounded text-violet-600 cursor-pointer w-4 h-4"
                        />
                      </td>
                      <td className="py-2.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            src.type === 'greenhouse'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : src.type === 'lever'
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          {src.type}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-semibold text-gray-900">{src.name}</td>
                      <td className="py-2.5 px-4 font-mono text-gray-600">
                        {src.board || src.site || src.url}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <button
                          onClick={() => handleDeleteSource(idx)}
                          className="text-gray-400 hover:text-rose-600 p-1 cursor-pointer"
                          title="Remove source"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ── Substack Draft & Cookie Setup Modal ─────────── */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-gray-200 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-gray-900">Create Substack Draft</h3>
              <button
                onClick={() => setShowAuthModal(false)}
                className="text-gray-400 hover:text-gray-700 text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-xs text-emerald-900">
              <p className="font-bold mb-1">✅ Option 1 (Instant — No Cookie Needed):</p>
              <p className="mb-2.5">
                The entire newsletter issue Markdown has already been <strong>copied to your clipboard</strong>! Click below to open your Substack editor and press <kbd className="px-1.5 py-0.5 bg-white border rounded font-mono">Ctrl+V</kbd>.
              </p>
              <a
                href="https://flerkenstudio.substack.com/publish/post"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setShowAuthModal(false)}
                className="inline-flex items-center gap-1.5 bg-orange-600 hover:bg-orange-700 text-white font-bold px-4 py-2 rounded-lg shadow-2xs"
              >
                Open Substack Editor &amp; Paste <ExternalLink size={13} />
              </a>
            </div>

            <div className="border-t border-gray-200 pt-3.5 space-y-2.5 text-xs">
              <p className="font-bold text-gray-800">🔐 Option 2 (Automated API Draft via python-substack):</p>
              <p className="text-gray-500">
                Paste your Substack session cookie (<code className="bg-gray-100 px-1 rounded">substack.sid=...</code> or <code className="bg-gray-100 px-1 rounded">connect.sid=...</code>). It will be saved only to your local <code className="bg-gray-100 px-1 rounded">flerken-studio-bot/.env</code> (gitignored).
              </p>
              <input
                type="password"
                placeholder="substack.sid=s%3A..."
                value={cookieInput}
                onChange={(e) => setCookieInput(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 font-mono text-xs"
              />
              <div className="flex justify-end gap-2 pt-1">
                <button
                  onClick={() => setShowAuthModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100 font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleCreateSubstackDraft(cookieInput)}
                  disabled={!cookieInput.trim()}
                  className="px-4 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white font-bold cursor-pointer"
                >
                  Save Cookie &amp; Create Draft
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
