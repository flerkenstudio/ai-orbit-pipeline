import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { AllCommunityModule, ModuleRegistry, themeAlpine } from 'ag-grid-community';
import {
  Trophy,
  Search,
  RefreshCw,
  Download,
  ExternalLink,
  Award,
  Sparkles,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Play,
  Building2,
  GraduationCap,
  Layers,
  Loader2,
  DollarSign,
  Star,
  Globe
} from 'lucide-react';

ModuleRegistry.registerModules([AllCommunityModule]);

const competitionsTheme = themeAlpine.withParams({
  backgroundColor: '#ffffff',
  foregroundColor: '#000000',
  headerBackgroundColor: '#1e293b', // Slate 800
  headerFontWeight: 700,
  headerTextColor: '#ffffff',
  borderColor: '#e2e8f0',
  rowBorder: { color: '#e2e8f0', width: 1, style: 'solid' },
  oddRowBackgroundColor: '#f8fafc',
  fontSize: 13,
  fontFamily: 'Inter, system-ui, sans-serif',
  cellHorizontalPadding: 10,
  headerColumnBorder: { color: 'rgba(255,255,255,0.2)', width: 1, style: 'solid' },
  columnBorder: { color: '#e2e8f0', width: 1, style: 'solid' },
});

/* ── Custom AG Grid Renderers for Competitions ────────────── */

const TitleCellRenderer = (props) => {
  if (!props.value) return null;
  const officialUrl = props.data?.official_url;
  const discoveryUrl = props.data?.discovery_url;
  return (
    <div className="flex items-center justify-between gap-1.5 h-full w-full">
      <span className="font-semibold text-gray-900 text-xs truncate" title={props.value}>
        {props.value}
      </span>
      <div className="flex items-center gap-1 shrink-0">
        {officialUrl && (
          <a
            href={officialUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200 text-[10px] font-bold transition-colors"
            title={`Open official website (${officialUrl})`}
          >
            <Globe size={10} />
            <span>Official Site</span>
            <ExternalLink size={9} />
          </a>
        )}
        {discoveryUrl && (
          <a
            href={discoveryUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 text-[10px] font-medium transition-colors"
            title="Open opportunity listing"
          >
            <span>Listing</span>
            <ExternalLink size={9} />
          </a>
        )}
      </div>
    </div>
  );
};

const PriorityCellRenderer = (props) => {
  const score = props.value || 0;
  let badgeColor = 'bg-slate-100 text-slate-700 border-slate-200';
  if (score >= 80) badgeColor = 'bg-amber-100 text-amber-900 font-extrabold border-amber-300 shadow-2xs';
  else if (score >= 60) badgeColor = 'bg-indigo-100 text-indigo-800 font-bold border-indigo-200';
  else if (score >= 40) badgeColor = 'bg-blue-50 text-blue-700 border-blue-200';

  return (
    <div className="flex items-center h-full">
      <span className={`text-[11px] px-2 py-0.5 rounded-full border flex items-center gap-1 ${badgeColor}`}>
        <Star size={10} className={score >= 80 ? 'fill-amber-600 text-amber-600' : 'text-slate-400'} />
        {score}
      </span>
    </div>
  );
};

const OrganiserCellRenderer = (props) => {
  if (!props.value) return null;
  const isPremium = props.data?.premium === 1 || props.data?.premium === true;
  const orgType = props.data?.organiser_type || '';

  return (
    <div className="flex items-center gap-1.5 h-full">
      {orgType === 'college' ? (
        <GraduationCap size={13} className="text-amber-600 shrink-0" />
      ) : (
        <Building2 size={13} className="text-blue-600 shrink-0" />
      )}
      <span className="truncate text-xs font-medium text-gray-700">{props.value}</span>
      {isPremium && (
        <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-1.5 py-0.2 rounded shrink-0 flex items-center gap-0.5">
          <Award size={10} /> Tier 1
        </span>
      )}
    </div>
  );
};

const CategoryCellRenderer = (props) => {
  if (!props.value) return null;
  const cat = String(props.value).toLowerCase();
  let color = 'bg-gray-100 text-gray-700 border-gray-200';
  if (cat.includes('hack')) color = 'bg-indigo-50 text-indigo-700 border-indigo-200';
  else if (cat.includes('coding')) color = 'bg-blue-50 text-blue-700 border-blue-200';
  else if (cat.includes('quiz')) color = 'bg-purple-50 text-purple-700 border-purple-200';
  else if (cat.includes('case')) color = 'bg-amber-50 text-amber-800 border-amber-200';
  else if (cat.includes('bplan') || cat.includes('pitch')) color = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  else if (cat.includes('design')) color = 'bg-rose-50 text-rose-700 border-rose-200';
  else if (cat.includes('debate')) color = 'bg-cyan-50 text-cyan-700 border-cyan-200';

  return (
    <div className="flex items-center h-full">
      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border capitalize ${color}`}>
        {props.value}
      </span>
    </div>
  );
};

const PrizeCellRenderer = (props) => {
  if (!props.value) return <span className="text-gray-400 text-xs">-</span>;
  return (
    <div className="flex items-center gap-1 h-full text-xs font-bold text-emerald-700">
      <Award size={13} className="text-emerald-600 shrink-0" />
      <span className="truncate">{props.value}</span>
    </div>
  );
};

const DeadlineCellRenderer = (props) => {
  if (!props.value) return <span className="text-gray-400 text-xs">Rolling / TBD</span>;
  const status = props.data?.status;
  const isExpired = status === 'expired';

  return (
    <div className="flex items-center gap-1.5 h-full">
      <Calendar size={13} className={isExpired ? 'text-red-400' : 'text-indigo-500'} />
      <span className={`text-xs font-medium ${isExpired ? 'text-red-600 line-through' : 'text-gray-800'}`}>
        {props.value}
      </span>
      {isExpired && (
        <span className="text-[10px] bg-red-100 text-red-700 font-semibold px-1.5 py-0.2 rounded">
          Expired
        </span>
      )}
    </div>
  );
};

const SourceCellRenderer = (props) => {
  if (!props.value) return null;
  return (
    <span className="text-[11px] font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 uppercase">
      {props.value}
    </span>
  );
};

export default function CompetitionsView() {
  const [competitions, setCompetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quickFilter, setQuickFilter] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineMsg, setPipelineMsg] = useState('');

  // Fetch competitions from SQLite backend endpoint
  const fetchCompetitions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch('http://localhost:8000/api/competitions');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setCompetitions(data);
    } catch (err) {
      setError(err.message || 'Failed to load competitions data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCompetitions();
  }, [fetchCompetitions]);

  // Run scraper pipeline
  const handleRunPipeline = async (demoMode = false) => {
    setPipelineRunning(true);
    setPipelineMsg(demoMode ? 'Running demo competitions pipeline...' : 'Scraping & Resolving Official College/Company Websites...');
    try {
      const resp = await fetch('http://localhost:8000/api/competitions/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ demo: demoMode, no_linkcheck: true }),
      });
      if (!resp.ok) throw new Error('Pipeline trigger failed');
      
      // Poll status for completion
      const interval = setInterval(async () => {
        const sResp = await fetch('http://localhost:8000/api/competitions/status');
        if (sResp.ok) {
          const sData = await sResp.json();
          if (!sData.is_running) {
            clearInterval(interval);
            setPipelineRunning(false);
            fetchCompetitions();
          }
        }
      }, 1500);
    } catch (err) {
      setError(err.message);
      setPipelineRunning(false);
    }
  };

  // Download Excel export
  const handleDownloadExcel = () => {
    window.open('http://localhost:8000/api/competitions/download', '_blank');
  };

  // Metrics
  const stats = useMemo(() => {
    const total = competitions.length;
    const live = competitions.filter(c => c.status === 'live').length;
    const premium = competitions.filter(c => c.premium === 1 || c.premium === true).length;
    const totalPrizeVal = competitions.reduce((acc, c) => acc + (c.prize_value || 0), 0);
    return { total, live, premium, totalPrizeVal };
  }, [competitions]);

  // Filtered rows
  const rowData = useMemo(() => {
    if (selectedCategory === 'all') return competitions;
    return competitions.filter(c => String(c.category || '').toLowerCase() === selectedCategory.toLowerCase());
  }, [competitions, selectedCategory]);

  // Column definitions
  const columnDefs = useMemo(() => [
    {
      headerName: 'Priority',
      field: 'priority_score',
      width: 100,
      cellRenderer: PriorityCellRenderer,
      sort: 'desc',
    },
    {
      headerName: 'Competition Title & Official Links',
      field: 'title',
      flex: 2.2,
      minWidth: 280,
      cellRenderer: TitleCellRenderer,
      filter: 'agTextColumnFilter',
    },
    {
      headerName: 'Organiser / Institute',
      field: 'organiser',
      flex: 1.5,
      minWidth: 180,
      cellRenderer: OrganiserCellRenderer,
      filter: 'agTextColumnFilter',
    },
    {
      headerName: 'Category',
      field: 'category',
      width: 130,
      cellRenderer: CategoryCellRenderer,
      filter: 'agTextColumnFilter',
    },
    {
      headerName: 'Prize Pool',
      field: 'prize_pool',
      width: 160,
      cellRenderer: PrizeCellRenderer,
    },
    {
      headerName: 'Deadline',
      field: 'reg_deadline',
      width: 150,
      cellRenderer: DeadlineCellRenderer,
    },
    {
      headerName: 'Source',
      field: 'source',
      width: 120,
      cellRenderer: SourceCellRenderer,
    },
  ], []);

  return (
    <div className="flex flex-col h-full bg-slate-50 font-sans">

      {/* ── Action Toolbar ────────────────────────────── */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search competitions, organisers..."
              value={quickFilter}
              onChange={(e) => setQuickFilter(e.target.value)}
              className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs w-60 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
            />
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {[
              { id: 'all', label: 'All' },
              { id: 'hackathon', label: 'Hackathons' },
              { id: 'coding', label: 'Coding' },
              { id: 'case', label: 'Case Studies' },
              { id: 'quiz', label: 'Quizzes' },
              { id: 'bplan', label: 'B-Plan' },
              { id: 'design', label: 'Design' },
              { id: 'debate', label: 'Debates' },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`text-xs font-semibold px-2.5 py-1 rounded-lg transition-colors cursor-pointer ${
                  selectedCategory === cat.id
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleRunPipeline(false)}
            disabled={pipelineRunning}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-all active:scale-95 cursor-pointer disabled:opacity-50"
          >
            {pipelineRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
            <span>Scrape Live (Official College/Company Sites)</span>
          </button>

          <button
            onClick={handleDownloadExcel}
            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer"
          >
            <Download size={14} />
            <span>Export Excel</span>
          </button>

          <button
            onClick={fetchCompetitions}
            disabled={loading}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            title="Refresh table"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin text-indigo-600' : ''} />
          </button>
        </div>
      </div>

      {/* ── Stats Bar ─────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200 px-6 py-2.5 flex items-center gap-8 text-xs font-medium flex-wrap">
        <div className="flex items-center gap-2">
          <Trophy size={16} className="text-indigo-600" />
          <span className="text-slate-500">Total Monitored:</span>
          <span className="font-bold text-slate-900">{stats.total}</span>
        </div>
        <div className="h-4 w-px bg-slate-200 hidden sm:block" />
        <div className="flex items-center gap-2">
          <CheckCircle2 size={16} className="text-emerald-600" />
          <span className="text-slate-500">Live Opportunities:</span>
          <span className="font-bold text-emerald-700">{stats.live}</span>
        </div>
        <div className="h-4 w-px bg-slate-200 hidden sm:block" />
        <div className="flex items-center gap-2">
          <Award size={16} className="text-amber-500" />
          <span className="text-slate-500">Tier 1 / IITs / IIMs / Big Tech:</span>
          <span className="font-bold text-amber-700">{stats.premium}</span>
        </div>
        <div className="h-4 w-px bg-slate-200 hidden sm:block" />
        <div className="flex items-center gap-2">
          <DollarSign size={16} className="text-emerald-600" />
          <span className="text-slate-500">Total Prize Pool Value:</span>
          <span className="font-bold text-slate-900">
            ₹{stats.totalPrizeVal.toLocaleString('en-IN')}
          </span>
        </div>
      </div>

      {/* ── Live Scraper Execution Banner ──────────────── */}
      {pipelineRunning && (
        <div className="bg-indigo-50 border-b border-indigo-200 px-6 py-2 flex items-center gap-2 text-xs text-indigo-800 font-medium animate-pulse">
          <Loader2 size={14} className="animate-spin text-indigo-600" />
          <span>{pipelineMsg}</span>
        </div>
      )}

      {/* ── Data Grid ─────────────────────────────────── */}
      <div className="flex-1 w-full relative">
        <div className="absolute inset-0">
          <AgGridReact
            theme={competitionsTheme}
            rowData={rowData}
            columnDefs={columnDefs}
            quickFilterText={quickFilter}
            pagination={true}
            paginationPageSize={20}
            paginationPageSizeSelector={[10, 20, 50, 100]}
            animateRows={true}
            overlayLoadingTemplate={'<span class="ag-overlay-loading-center">Loading Competitions Catalog...</span>'}
            overlayNoRowsTemplate={'<span class="ag-overlay-loading-center">No competitions found in this category.</span>'}
          />
        </div>
      </div>

    </div>
  );
}
