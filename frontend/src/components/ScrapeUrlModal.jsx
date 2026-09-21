import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Globe,
  Link as LinkIcon,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Sparkles,
  Loader2,
  ShieldCheck,
  ArrowRight,
  Download,
  FileSpreadsheet,
  Layers,
  StopCircle,
  FolderDown
} from 'lucide-react';

export default function ScrapeUrlModal({ isOpen, onClose, onToolScraped }) {
  const [activeTab, setActiveTab] = useState('single'); // 'single' | 'directory'

  // Single URL state
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Directory scrape state
  const [dirUrl, setDirUrl] = useState('https://www.example.com/');
  const [dirLimit, setDirLimit] = useState(10000); // 1000, 5000, 10000, 20000, 50000, null (all)
  const [dirState, setDirState] = useState({
    is_running: false,
    total: 0,
    completed: 0,
    extracted: 0,
    percent: 0.0,
    last_tool: null,
    output_xlsx: 'agenthunter_agents_full.xlsx',
    output_csv: 'agenthunter_agents_full.csv',
    status: 'idle',
    error: null,
  });
  const [dirLoading, setDirLoading] = useState(false);
  const [dirError, setDirError] = useState(null);
  const pollTimerRef = useRef(null);

  // Fetch directory status periodically when active
  useEffect(() => {
    if (!isOpen) return;

    const fetchDirStatus = async () => {
      try {
        const resp = await fetch('http://localhost:8000/api/pipeline/directory-status');
        if (resp.ok) {
          const data = await resp.json();
          setDirState(data);
        }
      } catch {
        // silent polling catch
      }
    };

    fetchDirStatus();
    pollTimerRef.current = setInterval(fetchDirStatus, 1500);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [isOpen, dirState.is_running]);

  if (!isOpen) return null;

  // Single Tool Scrape Handler
  const handleSingleScrape = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch('http://localhost:8000/api/pipeline/scrape-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || `Server responded with status ${resp.status}`);
      }

      const toolData = await resp.json();
      setResult(toolData);
      if (onToolScraped) {
        onToolScraped(toolData);
      }
    } catch (err) {
      setError(err.message || 'Failed to scrape URL. Please check the address and try again.');
    } finally {
      setLoading(false);
    }
  };

  // Directory Scrape Trigger Handler
  const handleStartDirScrape = async () => {
    setDirLoading(true);
    setDirError(null);
    try {
      const resp = await fetch('http://localhost:8000/api/pipeline/scrape-directory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: dirUrl.trim(),
          limit: dirLimit === 'all' ? null : Number(dirLimit),
          workers: 25,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || `Server error ${resp.status}`);
      }
    } catch (err) {
      setDirError(err.message || 'Failed to trigger directory scrape.');
    } finally {
      setDirLoading(false);
    }
  };

  // Stop Directory Scrape
  const handleStopDirScrape = async () => {
    try {
      await fetch('http://localhost:8000/api/pipeline/stop-directory', { method: 'POST' });
    } catch {
      // ignore
    }
  };

  // Download Trigger
  const handleDownload = (filename) => {
    window.open(`http://localhost:8000/api/pipeline/download?file=${encodeURIComponent(filename)}`, '_blank');
  };

  const getPricingBadge = (pricing) => {
    if (!pricing) return null;
    let colorClass = 'bg-gray-100 text-gray-700';
    if (pricing === 'Free') colorClass = 'bg-emerald-50 text-emerald-700 border border-emerald-200';
    else if (pricing === 'Open Source') colorClass = 'bg-purple-50 text-purple-700 border border-purple-200';
    else if (pricing === 'Freemium') colorClass = 'bg-blue-50 text-blue-700 border border-blue-200';
    else if (pricing === 'Paid') colorClass = 'bg-amber-50 text-amber-700 border border-amber-200';

    return (
      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${colorClass}`}>
        {pricing}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 w-full max-w-xl max-h-[90vh] flex flex-col overflow-hidden transition-all">

        {/* Header with Navigation Tabs */}
        <div className="px-6 pt-5 pb-3 border-b border-gray-100 bg-gradient-to-r from-gray-50/80 to-white">
          <div className="flex items-center justify-between pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                <Sparkles size={18} />
              </div>
              <div>
                <h2 className="text-base font-bold text-gray-900 leading-tight">AI Scraper & Enricher</h2>
                <p className="text-xs text-gray-500">Extract structured data per AIOrbit specifications</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-1.5 rounded-lg transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
            <button
              onClick={() => setActiveTab('single')}
              className={`flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${activeTab === 'single'
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              <Globe size={14} />
              <span>Single Tool URL</span>
            </button>
            <button
              onClick={() => setActiveTab('directory')}
              className={`flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${activeTab === 'directory'
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              <Layers size={14} />
              <span>Directory / Batch Scrape</span>
              {dirState.is_running && (
                <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping" />
              )}
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5">

          {/* ================= TAB 1: SINGLE URL ================= */}
          {activeTab === 'single' && (
            <>
              {/* Input Form */}
              <form onSubmit={handleSingleScrape} className="space-y-3">
                <div>
                  <label htmlFor="url-input" className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Target Tool Website URL
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                      <LinkIcon size={15} />
                    </div>
                    <input
                      id="url-input"
                      type="url"
                      required
                      placeholder="https://cursor.com, https://v0.dev, or AgentHunter page"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      disabled={loading}
                      className="w-full pl-9 pr-24 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all"
                    />
                    <button
                      type="submit"
                      disabled={loading || !url.trim()}
                      className="absolute right-1.5 top-1.5 bottom-1.5 px-3.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shadow-xs active:scale-95 cursor-pointer"
                    >
                      {loading ? (
                        <>
                          <Loader2 size={13} className="animate-spin" />
                          <span>Scraping...</span>
                        </>
                      ) : (
                        <>
                          <span>Scrape</span>
                          <ArrowRight size={13} />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </form>

              {/* Error Notice */}
              {error && (
                <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2.5 text-xs text-red-700">
                  <AlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Extraction Failed</p>
                    <p className="mt-0.5 text-red-600">{error}</p>
                  </div>
                </div>
              )}

              {/* Loading Indicator Card */}
              {loading && (
                <div className="p-6 rounded-xl border border-indigo-100 bg-indigo-50/50 flex flex-col items-center justify-center text-center space-y-2.5">
                  <Loader2 size={28} className="animate-spin text-indigo-600" />
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Probing & Analyzing Website</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Extracting metadata, logo, features, pricing, and live HTTP verification...
                    </p>
                  </div>
                </div>
              )}

              {/* Single Result Preview Card */}
              {result && !loading && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg border border-emerald-200">
                    <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                    <span>Successfully scraped and saved to catalog!</span>
                  </div>

                  <div className="p-4 rounded-xl border border-gray-200 bg-gray-50/60 space-y-3.5 shadow-xs">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        {result.logo_url ? (
                          <img
                            src={result.logo_url}
                            alt={result.name}
                            className="w-10 h-10 rounded-lg object-contain bg-white p-1 border border-gray-200 shadow-2xs shrink-0"
                            onError={(e) => { e.target.style.display = 'none'; }}
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-gray-200 flex items-center justify-center text-gray-500 shrink-0">
                            <Globe size={20} />
                          </div>
                        )}
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-gray-900 text-base leading-tight">{result.name}</h3>
                            {getPricingBadge(result.pricing)}
                          </div>
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-indigo-600 hover:underline flex items-center gap-1 mt-0.5 font-medium"
                          >
                            {result.url} <ExternalLink size={10} />
                          </a>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-green-50 text-green-700 border border-green-200 shrink-0">
                        <ShieldCheck size={13} className="text-green-600" />
                        <span>HTTP {result.http_status || 200} Verified</span>
                      </div>
                    </div>

                    <p className="text-xs text-gray-600 leading-relaxed bg-white p-3 rounded-lg border border-gray-100">
                      {result.description}
                    </p>

                    {result.features && result.features.length > 0 && (
                      <div>
                        <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
                          Extracted Features ({result.features.length})
                        </span>
                        <div className="space-y-1">
                          {result.features.slice(0, 4).map((f, i) => (
                            <div key={i} className="text-xs text-gray-700 flex items-center gap-1.5">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />
                              <span className="truncate">{f}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.categories && result.categories.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-gray-200/60">
                        <span className="text-[11px] text-gray-400 font-medium">Categories:</span>
                        {result.categories.map((c, i) => (
                          <span key={i} className="bg-white text-indigo-700 border border-indigo-100 text-[10px] font-medium px-2 py-0.5 rounded-md">
                            {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {/* ================= TAB 2: DIRECTORY SCRAPE ================= */}
          {activeTab === 'directory' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Directory Website
                </label>
                <input
                  type="url"
                  placeholder="https://www.example.com/"
                  value={dirUrl}
                  onChange={(e) => setDirUrl(e.target.value)}
                  disabled={dirState.is_running}
                  className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all"
                />
              </div>

              {/* Quantity Presets */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-gray-700">
                    Batch Extraction Target Range
                  </label>
                  <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">
                    Goal: 50K Pipeline
                  </span>
                </div>
                
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {[
                    { label: '1,000', value: 1000, desc: '~1.5 min' },
                    { label: '5,000', value: 5000, desc: '~7 mins' },
                    { label: '10,000', value: 10000, desc: '~15 mins' },
                    { label: '20,000', value: 20000, desc: '~30 mins' },
                    { label: '50,000', value: 50000, desc: 'Target Goal' },
                    { label: 'Max', value: 'all', desc: 'All Found' },
                  ].map((preset) => (
                    <button
                      key={preset.value}
                      type="button"
                      disabled={dirState.is_running}
                      onClick={() => setDirLimit(preset.value)}
                      className={`p-2 rounded-xl border text-center transition-all cursor-pointer ${dirLimit === preset.value
                          ? 'border-indigo-600 bg-indigo-50/70 text-indigo-900 ring-2 ring-indigo-600/20'
                          : 'border-gray-200 bg-gray-50/50 hover:bg-gray-100 text-gray-700'
                        }`}
                    >
                      <div className="text-xs font-bold">{preset.label}</div>
                      <div className="text-[10px] text-gray-500">{preset.desc}</div>
                    </button>
                  ))}
                </div>

                {/* Custom numeric target input */}
                <div className="mt-2.5 flex items-center gap-2 bg-gray-50 p-2 rounded-xl border border-gray-200">
                  <span className="text-xs text-gray-600 font-semibold shrink-0">Custom Target:</span>
                  <input
                    type="number"
                    min="10"
                    max="100000"
                    step="1000"
                    placeholder="e.g. 10000, 20000, 50000"
                    value={typeof dirLimit === 'number' ? dirLimit : ''}
                    onChange={(e) => setDirLimit(e.target.value ? Number(e.target.value) : 'all')}
                    disabled={dirState.is_running}
                    className="w-32 px-2.5 py-1 bg-white border border-gray-300 rounded-lg text-xs font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="text-xs text-indigo-700 font-medium">
                    {typeof dirLimit === 'number' ? `${dirLimit.toLocaleString()} tools` : 'All tools discovered'}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2.5 pt-1">
                {!dirState.is_running ? (
                  <button
                    type="button"
                    onClick={handleStartDirScrape}
                    disabled={dirLoading}
                    className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer"
                  >
                    {dirLoading ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Sparkles size={14} />
                    )}
                    <span>
                      Start Directory Scrape ({dirLimit === 'all' ? 'All Available' : `${Number(dirLimit).toLocaleString()} Agents`})
                    </span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleStopDirScrape}
                    className="flex-1 py-2.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer"
                  >
                    <StopCircle size={14} />
                    <span>Stop Scraping</span>
                  </button>
                )}
              </div>

              {/* Live Progress Bar when running */}
              {dirState.is_running && (
                <div className="p-4 rounded-xl border border-indigo-100 bg-indigo-50/40 space-y-2.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-indigo-900 flex items-center gap-1.5">
                      <Loader2 size={13} className="animate-spin text-indigo-600" />
                      Scraping in Background ({dirState.extracted} extracted)
                    </span>
                    <span className="font-bold text-indigo-700">{dirState.percent}%</span>
                  </div>

                  <div className="w-full bg-indigo-200/60 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(dirState.percent, 3)}%` }}
                    />
                  </div>

                  <div className="flex justify-between items-center text-[11px] text-gray-500">
                    <span>{dirState.completed} / {dirState.total} evaluated</span>
                    <span className="truncate max-w-[200px] italic">
                      Current: {dirState.last_tool || 'Working...'}
                    </span>
                  </div>
                </div>
              )}

              {/* Instant Excel Downloads (Always available!) */}
              <div className="mt-2 p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="text-emerald-600" size={18} />
                    <span className="text-xs font-bold text-emerald-900">
                      Excel Spreadsheet Downloads
                    </span>
                  </div>
                  <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                    {dirState.extracted ? `${dirState.extracted.toLocaleString()} Records` : 'Ready'}
                  </span>
                </div>

                <p className="text-[11px] text-emerald-800 leading-normal">
                  Data exported adhering strictly to AIOrbit schema (25 fields) and ready for instant download:
                </p>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleDownload(dirState.output_xlsx || 'agenthunter_agents_full.xlsx')}
                    className="flex items-center justify-center gap-2 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer active:scale-95"
                  >
                    <Download size={13} />
                    <span>Download Excel (.xlsx)</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDownload(dirState.output_csv || 'agenthunter_agents_full.csv')}
                    className="flex items-center justify-center gap-2 py-2 px-3 bg-white hover:bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer active:scale-95"
                  >
                    <FolderDown size={13} />
                    <span>Download CSV (.csv)</span>
                  </button>
                </div>
              </div>

            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs">
          <span className="text-gray-400">Strict AIOrbit schema compliance (25 fields)</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-900 hover:bg-black text-white font-medium rounded-lg transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
