import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { AllCommunityModule, ModuleRegistry, themeAlpine } from 'ag-grid-community';
import {
  FileText,
  Download,
  Copy,
  Check,
  Play,
  RefreshCw,
  Search,
  ExternalLink,
  Briefcase,
  MapPin,
  Flame,
  Sparkles,
  Table,
  BookOpen,
  Loader2,
  Building2,
  CheckCircle2
} from 'lucide-react';

ModuleRegistry.registerModules([AllCommunityModule]);

const substackGridTheme = themeAlpine.withParams({
  backgroundColor: '#ffffff',
  foregroundColor: '#0f172a',
  headerBackgroundColor: '#0f172a',
  headerFontWeight: 700,
  headerTextColor: '#ffffff',
  borderColor: '#e2e8f0',
  rowBorder: { color: '#e2e8f0', width: 1, style: 'solid' },
  oddRowBackgroundColor: '#f8fafc',
  fontSize: 13,
  fontFamily: 'Inter, system-ui, sans-serif',
  cellHorizontalPadding: 10,
});

const SECTIONS_ORDER = [
  'Hottest New Opportunities - Apply Fast',
  'Latest Software Development & Core Engineering Opportunities',
  'Latest Artificial Intelligence & Machine Learning Opportunities',
  'Latest Data Analytics, Research & Intelligence Roles',
  'Latest Product Design, Media & Content Strategy Roles',
  'Latest Business Operations, HR, Marketing & Strategy Roles',
];

const RoleLinkRenderer = (props) => {
  if (!props.value) return null;
  const comp = props.data?.company || '';
  const url = props.data?.apply_url || '';
  return (
    <div className="flex items-center justify-between gap-2 h-full w-full">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-indigo-700 hover:text-indigo-900 hover:underline font-semibold text-xs truncate"
        title={`${comp} hiring - ${props.value}`}
      >
        {comp} hiring - {props.value}
      </a>
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200 text-[10px] font-bold shrink-0"
        >
          <span>Direct Portal</span>
          <ExternalLink size={9} />
        </a>
      )}
    </div>
  );
};

const AtsBadgeRenderer = (props) => {
  if (!props.value) return null;
  const v = String(props.value);
  let cls = 'bg-slate-100 text-slate-700 border-slate-200';
  if (v === 'Greenhouse') cls = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  else if (v === 'Workday') cls = 'bg-blue-50 text-blue-700 border-blue-200';
  else if (v === 'Lever') cls = 'bg-purple-50 text-purple-700 border-purple-200';
  else if (v === 'Ashby') cls = 'bg-amber-50 text-amber-800 border-amber-200';
  else if (v === 'SmartRecruiters') cls = 'bg-indigo-50 text-indigo-700 border-indigo-200';
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${cls}`}>
      {v}
    </span>
  );
};

export default function SubstackView() {
  const [payload, setPayload] = useState({
    jobs: [],
    sections: {},
    title: '',
    subtitle: '',
    date_str: '',
    markdown: '',
    total: 0,
  });
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('doc'); // 'doc' | 'grid'
  const [selectedSection, setSelectedSection] = useState('all');
  const [quickFilter, setQuickFilter] = useState('');
  const [scraping, setScraping] = useState(false);
  const [scrapeStatusText, setScrapeStatusText] = useState('');
  const [copiedRich, setCopiedRich] = useState(false);
  const [copiedMd, setCopiedMd] = useState(false);
  const docPreviewRef = useRef(null);

  const fetchSubstackData = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch('http://localhost:8000/api/substack/jobs');
      if (resp.ok) {
        const data = await resp.json();
        setPayload(data);
      }
    } catch (err) {
      console.error('Error loading Substack jobs:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSubstackData();
  }, [fetchSubstackData]);

  const handleRunScraper = async () => {
    setScraping(true);
    setScrapeStatusText('Querying Greenhouse, Lever, Ashby, SmartRecruiters & Workday portals...');
    try {
      const resp = await fetch('http://localhost:8000/api/substack/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ include_seed: true }),
      });
      if (!resp.ok) throw new Error('Failed to start Substack scraper');

      const interval = setInterval(async () => {
        const sResp = await fetch('http://localhost:8000/api/substack/status');
        if (sResp.ok) {
          const sData = await sResp.json();
          if (sData.is_running) {
            if (sData.total_boards > 0) {
              setScrapeStatusText(
                `Scraping direct career boards (${sData.completed_boards}/${sData.total_boards}) — Latest: ${sData.last_company || '...'}`
              );
            }
          } else {
            clearInterval(interval);
            setScraping(false);
            setScrapeStatusText('');
            fetchSubstackData();
          }
        }
      }, 1200);
    } catch (e) {
      console.error(e);
      setScraping(false);
    }
  };

  const handleDownloadDocx = () => {
    window.open('http://localhost:8000/api/substack/download-docx', '_blank');
  };

  const handleDownloadXlsx = () => {
    window.open('http://localhost:8000/api/substack/download-xlsx', '_blank');
  };

  const handleCopyRichText = async () => {
    if (!docPreviewRef.current) return;
    try {
      const htmlContent = docPreviewRef.current.innerHTML;
      const plainText = payload.markdown || docPreviewRef.current.innerText;
      if (window.ClipboardItem) {
        const item = new ClipboardItem({
          'text/html': new Blob([htmlContent], { type: 'text/html' }),
          'text/plain': new Blob([plainText], { type: 'text/plain' }),
        });
        await navigator.clipboard.write([item]);
      } else {
        await navigator.clipboard.writeText(plainText);
      }
      setCopiedRich(true);
      setTimeout(() => setCopiedRich(false), 2500);
    } catch (e) {
      await navigator.clipboard.writeText(payload.markdown || '');
      setCopiedRich(true);
      setTimeout(() => setCopiedRich(false), 2500);
    }
  };

  const handleCopyMarkdown = async () => {
    await navigator.clipboard.writeText(payload.markdown || '');
    setCopiedMd(true);
    setTimeout(() => setCopiedMd(false), 2500);
  };

  const filteredJobs = useMemo(() => {
    let list = payload.jobs || [];
    if (selectedSection !== 'all') {
      list = list.filter((j) => j.section === selectedSection);
    }
    if (quickFilter.trim()) {
      const q = quickFilter.toLowerCase();
      list = list.filter(
        (j) =>
          (j.company || '').toLowerCase().includes(q) ||
          (j.role_title || '').toLowerCase().includes(q) ||
          (j.location || '').toLowerCase().includes(q) ||
          (j.ats_source || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [payload.jobs, selectedSection, quickFilter]);

  const columnDefs = useMemo(
    () => [
      {
        headerName: 'Company & Role (Direct Link)',
        field: 'role_title',
        flex: 2.3,
        minWidth: 300,
        cellRenderer: RoleLinkRenderer,
      },
      {
        headerName: 'Company',
        field: 'company',
        width: 170,
        filter: 'agTextColumnFilter',
      },
      {
        headerName: 'Substack Section',
        field: 'section',
        flex: 1.5,
        minWidth: 230,
      },
      {
        headerName: 'Location',
        field: 'location',
        width: 170,
      },
      {
        headerName: 'Mode',
        field: 'work_mode',
        width: 110,
      },
      {
        headerName: 'ATS Portal',
        field: 'ats_source',
        width: 140,
        cellRenderer: AtsBadgeRenderer,
      },
    ],
    []
  );

  const atsCounts = useMemo(() => {
    const jobs = payload.jobs || [];
    const uniqueCompanies = new Set(jobs.map((j) => j.company)).size;
    const remoteCount = jobs.filter((j) => j.work_mode === 'Remote').length;
    return { total: jobs.length, uniqueCompanies, remoteCount };
  }, [payload.jobs]);

  return (
    <div className="flex flex-col h-full bg-slate-50 font-sans overflow-hidden">
      {/* ── Top Action Toolbar ──────────────────────────── */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          {/* View Mode Toggle: Substack Word Preview vs Data Grid */}
          <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
            <button
              onClick={() => setViewMode('doc')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'doc'
                  ? 'bg-white text-rose-600 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <BookOpen size={14} />
              <span>Substack / Word Doc Preview</span>
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'grid'
                  ? 'bg-white text-indigo-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Table size={14} />
              <span>Table View ({filteredJobs.length})</span>
            </button>
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search company, role, city, ATS..."
              value={quickFilter}
              onChange={(e) => setQuickFilter(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs w-56 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:bg-white"
            />
          </div>
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleRunScraper}
            disabled={scraping}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-all active:scale-95 cursor-pointer disabled:opacity-50"
          >
            {scraping ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
            <span>Scrape Live Career Portals</span>
          </button>

          <button
            onClick={handleDownloadDocx}
            className="flex items-center gap-1.5 bg-rose-600 hover:bg-rose-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-2xs transition-all active:scale-95 cursor-pointer"
            title="Download formatted Microsoft Word (.docx) document with clickable links"
          >
            <FileText size={14} />
            <span>Download Word (.docx)</span>
          </button>

          <button
            onClick={handleCopyRichText}
            className="flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer"
            title="Copy formatted rich text with clickable links directly for Substack editor"
          >
            {copiedRich ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
            <span>{copiedRich ? 'Copied for Substack!' : 'Copy Rich Text'}</span>
          </button>

          <button
            onClick={handleCopyMarkdown}
            className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 transition-all cursor-pointer"
            title="Copy raw Markdown"
          >
            {copiedMd ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
            <span>{copiedMd ? 'Copied MD!' : 'Markdown'}</span>
          </button>

          <button
            onClick={handleDownloadXlsx}
            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer"
          >
            <Download size={14} />
            <span>Excel</span>
          </button>

          <button
            onClick={fetchSubstackData}
            disabled={loading}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            title="Refresh"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin text-rose-600' : ''} />
          </button>
        </div>
      </div>

      {/* ── Stats & Section Filter Bar ──────────────────── */}
      <div className="bg-white border-b border-slate-200 px-6 py-2 flex items-center justify-between flex-wrap gap-3 text-xs">
        <div className="flex items-center gap-6 font-medium">
          <div className="flex items-center gap-1.5">
            <Flame size={15} className="text-rose-600" />
            <span className="text-slate-500">Verified Direct Roles:</span>
            <span className="font-bold text-slate-900">{atsCounts.total}</span>
          </div>
          <div className="h-4 w-px bg-slate-200" />
          <div className="flex items-center gap-1.5">
            <Building2 size={15} className="text-indigo-600" />
            <span className="text-slate-500">Hiring Companies:</span>
            <span className="font-bold text-indigo-700">{atsCounts.uniqueCompanies}</span>
          </div>
          <div className="h-4 w-px bg-slate-200" />
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-600" />
            <span className="text-slate-500">Direct ATS Portals:</span>
            <span className="font-semibold text-emerald-700">
              100% Official (Greenhouse · Workday · Lever · Ashby · SmartRecruiters)
            </span>
          </div>
        </div>

        {/* Section Filter Pills */}
        <div className="flex items-center gap-1 flex-wrap">
          <button
            onClick={() => setSelectedSection('all')}
            className={`text-[11px] font-semibold px-2.5 py-1 rounded-md cursor-pointer transition-colors ${
              selectedSection === 'all'
                ? 'bg-rose-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All 6 Sections
          </button>
          {[
            { id: SECTIONS_ORDER[0], short: '🔥 Hottest Top 10' },
            { id: SECTIONS_ORDER[1], short: '💻 SDE & Core Eng' },
            { id: SECTIONS_ORDER[2], short: '🤖 AI & ML' },
            { id: SECTIONS_ORDER[3], short: '📊 Data & Research' },
            { id: SECTIONS_ORDER[4], short: '🎨 Design & Media' },
            { id: SECTIONS_ORDER[5], short: '💼 Business, HR & Ops' },
          ].map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedSection(s.id)}
              className={`text-[11px] font-semibold px-2.5 py-1 rounded-md cursor-pointer transition-colors ${
                selectedSection === s.id
                  ? 'bg-rose-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {s.short}
            </button>
          ))}
        </div>
      </div>

      {/* ── Live Scraping Progress Banner ───────────────── */}
      {scraping && (
        <div className="bg-indigo-50 border-b border-indigo-200 px-6 py-2 flex items-center gap-2 text-xs text-indigo-900 font-medium">
          <Loader2 size={14} className="animate-spin text-indigo-600" />
          <span>{scrapeStatusText}</span>
        </div>
      )}

      {/* ── Main Content Area ───────────────────────────── */}
      {viewMode === 'doc' ? (
        <div className="flex-1 overflow-y-auto p-6 bg-slate-100">
          <div
            ref={docPreviewRef}
            className="max-w-4xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200 p-8 sm:p-10 text-slate-900 leading-relaxed"
          >
            {/* Newsletter Header */}
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mb-3">
              {payload.title ||
                '🔴 InternAtlas (🎓 💼) - 60+ Hottest Early Career & Internship Roles - Do Not Miss'}
            </h1>
            <p className="text-sm text-slate-600 font-medium mb-2">{payload.subtitle}</p>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6">
              {payload.date_str}
            </p>

            <hr className="border-slate-200 my-5" />

            <div className="space-y-2 text-sm text-slate-800">
              <p>Hi Guys,</p>
              <p>Do like and restack this post to support our initiative.</p>
              <p>
                📲 If you want daily new opportunity alerts directly on your phone, join our
                community on WhatsApp/Telegram!
              </p>
            </div>

            <hr className="border-slate-200 my-5" />

            {/* 6 Categorized Sections */}
            {SECTIONS_ORDER.filter(
              (secTitle) => selectedSection === 'all' || selectedSection === secTitle
            ).map((secTitle) => {
              const secJobs = (payload.sections?.[secTitle] || []).filter((j) => {
                if (!quickFilter.trim()) return true;
                const q = quickFilter.toLowerCase();
                return (
                  (j.company || '').toLowerCase().includes(q) ||
                  (j.role_title || '').toLowerCase().includes(q) ||
                  (j.location || '').toLowerCase().includes(q)
                );
              });
              if (secJobs.length === 0) return null;

              return (
                <div key={secTitle} className="mb-8">
                  <h2 className="text-lg font-extrabold text-slate-900 mb-3 pb-1 border-b border-slate-100">
                    {secTitle}
                  </h2>
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    {secJobs.map((job, idx) => (
                      <li key={job.id || idx} className="text-slate-800 leading-snug">
                        <a
                          href={job.apply_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 underline font-medium"
                        >
                          {job.company} hiring - {job.role_title}
                        </a>{' '}
                        <span className="text-slate-600">
                          ({job.location} · {job.work_mode})
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              );
            })}

            <hr className="border-slate-200 my-6" />

            <p className="text-xs italic text-slate-500">
              *All links in this edition are 100% verified direct official career portals. Happy
              applying and all the best!*
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 w-full relative">
          <div className="absolute inset-0">
            <AgGridReact
              theme={substackGridTheme}
              rowData={filteredJobs}
              columnDefs={columnDefs}
              pagination={true}
              paginationPageSize={25}
              paginationPageSizeSelector={[25, 50, 100]}
              animateRows={true}
            />
          </div>
        </div>
      )}
    </div>
  );
}
