import React, { useState, useEffect, useRef } from 'react';
import {
  Play, CheckCircle2, AlertTriangle, XCircle, Terminal, RefreshCw,
  ExternalLink, Globe, Layers, ArrowRight, ShieldCheck, Database, X, Square
} from 'lucide-react';

const STAGES = [
  { id: 'discovery', name: 'Discovery', icon: Layers },
  { id: 'extraction', name: 'Enrichment', icon: Globe },
  { id: 'validation', name: 'Validation', icon: ShieldCheck },
  { id: 'export', name: 'Export & Sync', icon: Database },
];

export default function PipelineDrawer({ isOpen, onClose, onPipelineComplete }) {
  const [isRunning, setIsRunning] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [stage, setStage] = useState('idle'); // idle, discovery, extraction, classification, validation, export, completed, error, stopping, stopped
  const [progress, setProgress] = useState({ current: 0, total: 0, percent: 0 });
  const [currentTool, setCurrentTool] = useState(null);
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const logsEndRef = useRef(null);
  const timerRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Elapsed timer when running
  useEffect(() => {
    if (isRunning) {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRunning]);

  // Connect to SSE stream
  useEffect(() => {
    if (!isOpen) return;

    const eventSource = new EventSource('/api/pipeline/stream');

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'init') {
          if (data.state) {
            setIsRunning(data.state.is_running);
            setStage(data.state.stage);
            setProgress({
              current: data.state.current || 0,
              total: data.state.total || 0,
              percent: data.state.percent || 0,
            });
            setCurrentTool(data.state.last_tool);
            if (data.state.summary) setSummary(data.state.summary);
          }
          if (data.recent_logs) {
            setLogs(data.recent_logs);
          }
        } else if (data.type === 'log') {
          setLogs((prev) => [...prev.slice(-300), data]);
        } else if (data.type === 'stage') {
          setStage(data.stage);
          if (data.message) {
            setLogs((prev) => [...prev, { level: 'INFO', message: data.message, timestamp: new Date().toLocaleTimeString() }]);
          }
        } else if (data.type === 'discovery_done') {
          setStage('extraction');
          setProgress((prev) => ({ ...prev, total: data.unique_count }));
          if (data.message) {
            setLogs((prev) => [...prev, { level: 'INFO', message: data.message, timestamp: new Date().toLocaleTimeString() }]);
          }
        } else if (data.type === 'progress') {
          setProgress({
            current: data.current,
            total: data.total,
            percent: data.percent,
          });
          if (data.tool) setCurrentTool(data.tool);
          if (data.message) {
            setLogs((prev) => [...prev, { level: 'INFO', message: data.message, timestamp: new Date().toLocaleTimeString() }]);
          }
        } else if (data.type === 'completed') {
          setIsRunning(false);
          setIsStopping(false);
          setStage('completed');
          setSummary(data);
          if (onPipelineComplete) onPipelineComplete();
          if (data.message) {
            setLogs((prev) => [...prev, { level: 'SUCCESS', message: data.message, timestamp: new Date().toLocaleTimeString() }]);
          }
        } else if (data.type === 'stopped') {
          setIsRunning(false);
          setIsStopping(false);
          setStage('stopped');
          if (data.message) {
            setLogs((prev) => [...prev, { level: 'WARNING', message: data.message, timestamp: new Date().toLocaleTimeString() }]);
          }
        } else if (data.type === 'stage' && data.stage === 'stopping') {
          setStage('stopping');
          setIsStopping(true);
        } else if (data.type === 'error') {
          setIsRunning(false);
          setIsStopping(false);
          setStage('error');
          if (data.message) {
            setLogs((prev) => [...prev, { level: 'ERROR', message: data.message, timestamp: new Date().toLocaleTimeString() }]);
          }
        }
      } catch (e) {
        console.error('Failed to parse SSE event', e);
      }
    };

    eventSource.onerror = () => {
      // Reconnection handled automatically by EventSource
    };

    return () => {
      eventSource.close();
    };
  }, [isOpen, onPipelineComplete]);

  // Start pipeline run
  const handleStartPipeline = async () => {
    try {
      setIsRunning(true);
      setIsStopping(false);
      setStage('discovery');
      setProgress({ current: 0, total: 0, percent: 0 });
      setCurrentTool(null);
      setSummary(null);
      setElapsed(0);
      setLogs([{ level: 'INFO', message: 'Starting AI Orbit Pipeline run...', timestamp: new Date().toLocaleTimeString() }]);

      const res = await fetch('/api/pipeline/run', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Failed to start pipeline');
      }
    } catch (err) {
      setIsRunning(false);
      setStage('error');
      setLogs((prev) => [...prev, { level: 'ERROR', message: err.message, timestamp: new Date().toLocaleTimeString() }]);
    }
  };

  // Stop pipeline run
  const handleStopPipeline = async () => {
    try {
      setIsStopping(true);
      setLogs((prev) => [...prev, { level: 'WARNING', message: 'Stop signal sent. Finishing current operation...', timestamp: new Date().toLocaleTimeString() }]);
      await fetch('/api/pipeline/stop', { method: 'POST' });
    } catch (err) {
      console.error('Failed to stop pipeline', err);
    }
  };

  if (!isOpen) return null;

  const formatSeconds = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/50 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isRunning) onClose();
      }}
    >
      <div
        className="w-full max-w-2xl bg-white shadow-2xl rounded-2xl flex flex-col max-h-[90vh] border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Top Header ───────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50/80">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 text-white rounded-lg shadow-xs">
              <Terminal size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900 leading-tight">Pipeline Control &amp; Live Monitor</h2>
              <p className="text-xs text-gray-500">Live multi-source scraping, entity resolution &amp; verification</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isRunning && stage !== 'stopping' && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 text-amber-700 text-xs font-semibold rounded-full border border-amber-200 animate-pulse">
                <RefreshCw size={12} className="animate-spin" /> In Progress ({formatSeconds(elapsed)})
              </span>
            )}
            {stage === 'stopping' && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 bg-red-50 text-red-700 text-xs font-semibold rounded-full border border-red-200 animate-pulse">
                <RefreshCw size={12} className="animate-spin" /> Stopping…
              </span>
            )}
            {stage === 'stopped' && !isRunning && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-700 text-xs font-semibold rounded-full border border-amber-200">
                <AlertTriangle size={13} /> Stopped
              </span>
            )}
            {stage === 'completed' && !isRunning && (
              <span className="flex items-center gap-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full border border-emerald-200">
                <CheckCircle2 size={13} /> Completed
              </span>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors ml-2"
              title="Close drawer"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* ── Stepper Bar ──────────────────────────────────── */}
          <div className="grid grid-cols-4 gap-2">
            {STAGES.map((s, idx) => {
              const Icon = s.icon;
              const isCurrent = stage === s.id;
              const isPast =
                stage === 'completed' ||
                (s.id === 'discovery' && stage !== 'idle') ||
                (s.id === 'extraction' && ['validation', 'export', 'completed'].includes(stage)) ||
                (s.id === 'validation' && ['export', 'completed'].includes(stage));

              return (
                <div
                  key={s.id}
                  className={`flex flex-col items-center text-center p-2.5 rounded-lg border text-xs font-medium transition-colors ${
                    isCurrent
                      ? 'bg-blue-50 border-blue-300 text-blue-800 ring-2 ring-blue-500/20'
                      : isPast
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                      : 'bg-gray-50 border-gray-200 text-gray-400'
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    {isPast ? <CheckCircle2 size={14} className="text-emerald-600" /> : <Icon size={14} />}
                    <span className="font-semibold">{s.name}</span>
                  </div>
                  <span className="text-[10px] text-gray-500">
                    Step {idx + 1}
                  </span>
                </div>
              );
            })}
          </div>

          {/* ── Progress Bar ─────────────────────────────────── */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="flex justify-between items-center text-xs font-medium text-gray-700 mb-2">
              <span className="flex items-center gap-1.5">
                <span className="font-bold text-gray-900">Overall Progress</span>
                {stage !== 'idle' && (
                  <span className="text-gray-500">
                    ({progress.current} / {progress.total || '…'} tools processed)
                  </span>
                )}
              </span>
              <span className="text-blue-600 font-bold">{progress.percent}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress.percent}%` }}
              />
            </div>
          </div>

          {/* ── Current Tool Live Preview Card ───────────────── */}
          {currentTool && (
            <div className="bg-white border border-blue-100 rounded-xl p-4 shadow-xs bg-linear-to-r from-blue-50/40 to-indigo-50/20">
              <div className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider mb-2">
                Currently Enriching
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-white border border-gray-200 flex items-center justify-center p-1.5 shadow-2xs shrink-0">
                    {currentTool.logo_url ? (
                      <img
                        src={currentTool.logo_url}
                        alt=""
                        className="w-full h-full object-contain"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    ) : (
                      <Globe size={18} className="text-gray-400" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-gray-900 truncate">
                      {currentTool.name}
                    </h3>
                    <a
                      href={currentTool.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-blue-600 hover:underline flex items-center gap-1 truncate"
                    >
                      {currentTool.url} <ExternalLink size={10} />
                    </a>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {currentTool.pricing && (
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">
                      {currentTool.pricing}
                    </span>
                  )}
                  {currentTool.verified ? (
                    <span className="flex items-center gap-1 text-emerald-600 text-xs font-medium bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      <CheckCircle2 size={12} /> 200 OK
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-gray-500 text-xs font-medium bg-gray-100 px-2 py-0.5 rounded-full">
                      HTTP {currentTool.http_status || 'Pending'}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Completed Run Summary ────────────────────────── */}
          {summary && stage === 'completed' && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                <CheckCircle2 size={16} /> Pipeline Successfully Executed
              </div>
              <div className="grid grid-cols-3 gap-3 text-center pt-2">
                <div className="bg-white p-2.5 rounded-lg border border-emerald-100">
                  <div className="text-lg font-bold text-gray-900">{summary.entities_count}</div>
                  <div className="text-[10px] text-gray-500 font-medium">Entities Created</div>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-emerald-100">
                  <div className="text-lg font-bold text-gray-900">{summary.relationships_count}</div>
                  <div className="text-[10px] text-gray-500 font-medium">Relationships</div>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-emerald-100">
                  <div className="text-lg font-bold text-emerald-600">
                    {summary.passed} / {summary.total}
                  </div>
                  <div className="text-[10px] text-gray-500 font-medium">Quality Gate Passed</div>
                </div>
              </div>
            </div>
          )}

          {/* ── Live Terminal Console ────────────────────────── */}
          <div className="border border-gray-800 bg-[#0f172a] rounded-xl overflow-hidden shadow-inner flex flex-col h-72">
            <div className="bg-[#1e293b] px-4 py-2 flex items-center justify-between border-b border-gray-800 text-xs text-gray-400">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                </div>
                <span className="font-mono text-gray-300 ml-1">pipeline.log</span>
              </div>
              <span className="text-[11px] text-gray-500 font-mono">
                {logs.length} lines
              </span>
            </div>

            <div className="flex-1 p-3 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-1 text-gray-300">
              {logs.length === 0 ? (
                <div className="text-gray-500 italic p-2">Ready to run. Click "Start Scraping Pipeline" below.</div>
              ) : (
                logs.map((log, i) => {
                  let colorClass = 'text-gray-300';
                  if (log.level === 'WARNING') colorClass = 'text-amber-400';
                  if (log.level === 'ERROR') colorClass = 'text-rose-400 font-semibold';
                  if (log.level === 'SUCCESS') colorClass = 'text-emerald-400 font-semibold';

                  return (
                    <div key={i} className="flex gap-2">
                      <span className="text-gray-500 select-none shrink-0">{log.timestamp || '--:--'}</span>
                      <span className={`break-all ${colorClass}`}>{log.message}</span>
                    </div>
                  );
                })
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>

        {/* ── Bottom Action Footer ─────────────────────────── */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Close
          </button>

          <div className="flex items-center gap-3">
            {isRunning && (
              <button
                onClick={handleStopPipeline}
                disabled={isStopping}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-bold text-red-600 bg-red-50 hover:bg-red-100 border border-red-200 shadow-xs transition-colors cursor-pointer active:scale-98"
              >
                <Square size={13} fill="currentColor" /> {isStopping ? 'Stopping…' : 'Stop Pipeline'}
              </button>
            )}

            {!isRunning ? (
              <button
                onClick={handleStartPipeline}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 active:scale-98 shadow-sm transition-all cursor-pointer"
              >
                <Play size={15} fill="currentColor" /> {stage === 'stopped' ? 'Restart Pipeline' : 'Start Scraping Pipeline'}
              </button>
            ) : (
              <div className="flex items-center gap-2 text-xs font-medium text-blue-700 bg-blue-50 px-3.5 py-2.5 rounded-lg border border-blue-200">
                <RefreshCw size={14} className="animate-spin text-blue-600" />
                <span>Processing Pipeline…</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
