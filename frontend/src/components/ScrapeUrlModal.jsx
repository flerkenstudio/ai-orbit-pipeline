import React, { useState } from 'react';
import {
  X,
  Globe,
  Link as LinkIcon,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Sparkles,
  Loader2,
  Tag,
  DollarSign,
  ShieldCheck,
  ArrowRight
} from 'lucide-react';

export default function ScrapeUrlModal({ isOpen, onClose, onToolScraped }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleScrape = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch('http://localhost:8000/api/pipeline/scrape-url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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

  const resetForm = () => {
    setUrl('');
    setError(null);
    setResult(null);
  };

  const getPricingBadge = (pricing) => {
    if (!pricing) return null;
    let colorClass = "bg-gray-100 text-gray-700";
    if (pricing === "Free") colorClass = "bg-emerald-50 text-emerald-700 border border-emerald-200";
    else if (pricing === "Open Source") colorClass = "bg-purple-50 text-purple-700 border border-purple-200";
    else if (pricing === "Freemium") colorClass = "bg-blue-50 text-blue-700 border border-blue-200";
    else if (pricing === "Paid") colorClass = "bg-amber-50 text-amber-700 border border-amber-200";

    return (
      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${colorClass}`}>
        {pricing}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 w-full max-w-xl max-h-[90vh] flex flex-col overflow-hidden transition-all">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50/80 to-white">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900 leading-tight">Scrape Single AI Tool</h2>
              <p className="text-xs text-gray-500">Extract pricing, features, logos & metadata from any website</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-1.5 rounded-lg transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          
          {/* Input Form */}
          <form onSubmit={handleScrape} className="space-y-3">
            <div>
              <label htmlFor="url-input" className="block text-xs font-semibold text-gray-700 mb-1.5">
                Target Website URL
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <LinkIcon size={15} />
                </div>
                <input
                  id="url-input"
                  type="url"
                  required
                  placeholder="https://cursor.com or https://v0.dev"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={loading}
                  className="w-full pl-9 pr-24 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all"
                />
                <button
                  type="submit"
                  disabled={loading || !url.trim()}
                  className="absolute right-1.5 top-1.5 bottom-1.5 px-3.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shadow-sm active:scale-95"
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
                  Fetching homepage, detecting pricing model, parsing feature bullets, and probing HTTP status...
                </p>
              </div>
            </div>
          )}

          {/* Result Preview Card */}
          {result && !loading && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg border border-emerald-200">
                <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                <span>Successfully scraped and incrementally saved to catalog!</span>
              </div>

              <div className="p-4 rounded-xl border border-gray-200 bg-gray-50/60 space-y-3.5 shadow-sm">
                
                {/* Header info */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {result.logo_url ? (
                      <img
                        src={result.logo_url}
                        alt={result.name}
                        className="w-10 h-10 rounded-lg object-contain bg-white p-1 border border-gray-200 shadow-xs shrink-0"
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

                  {/* Verification badge */}
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-green-50 text-green-700 border border-green-200 shrink-0">
                    <ShieldCheck size={13} className="text-green-600" />
                    <span>HTTP {result.http_status || 200} Verified</span>
                  </div>
                </div>

                {/* Description */}
                <p className="text-xs text-gray-600 leading-relaxed bg-white p-3 rounded-lg border border-gray-100">
                  {result.description}
                </p>

                {/* Extracted Features */}
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

                {/* Categories */}
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

        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs">
          {result ? (
            <>
              <button
                onClick={resetForm}
                className="text-indigo-600 hover:text-indigo-700 font-medium cursor-pointer"
              >
                + Scrape another tool
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-900 hover:bg-black text-white font-medium rounded-lg transition-colors cursor-pointer"
              >
                Done
              </button>
            </>
          ) : (
            <>
              <span className="text-gray-400">Powered by AI Orbit Feature Extractor</span>
              <button
                onClick={onClose}
                className="px-3.5 py-1.5 text-gray-600 hover:bg-gray-200/60 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  );
}
