import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { AllCommunityModule, ModuleRegistry, themeAlpine } from 'ag-grid-community';
import { Orbit, Download, Search, RefreshCw, CheckCircle2, XCircle, Globe, ExternalLink, Play } from 'lucide-react';
import { useTools } from './hooks/useTools';
import PipelineDrawer from './components/PipelineDrawer';

// Register all AG Grid Community modules
ModuleRegistry.registerModules([AllCommunityModule]);

// Custom Google-Sheets-like theme based on Alpine
const googleSheetsTheme = themeAlpine.withParams({
  backgroundColor: '#ffffff',
  foregroundColor: '#000000',
  headerBackgroundColor: '#4285f4',
  headerFontWeight: 700,
  headerTextColor: '#ffffff',
  borderColor: '#e2e3e3',
  rowBorder: { color: '#e2e3e3', width: 1, style: 'solid' },
  oddRowBackgroundColor: '#f8f9fa',
  fontSize: 13,
  fontFamily: 'Arial, sans-serif',
  cellHorizontalPadding: 8,
  headerColumnBorder: { color: 'rgba(255,255,255,0.3)', width: 1, style: 'solid' },
  columnBorder: { color: '#e2e3e3', width: 1, style: 'solid' },
});

/* ── Cell renderers ─────────────────────────────────────── */
const LinkCellRenderer = (props) => {
  if (!props.value) return null;
  return (
    <a href={props.value} target="_blank" rel="noopener noreferrer"
       className="text-blue-600 hover:underline flex items-center gap-1 h-full text-xs">
      {new URL(props.value).hostname} <ExternalLink size={11} />
    </a>
  );
};

const VerifiedCellRenderer = (props) => {
  if (props.value === null || props.value === undefined) return null;
  return props.value ? (
    <span className="text-green-600 flex items-center justify-center h-full"><CheckCircle2 size={15} /></span>
  ) : (
    <span className="text-red-400 flex items-center justify-center h-full"><XCircle size={15} /></span>
  );
};

const LogoCellRenderer = (props) => {
  if (!props.value) return <span className="text-gray-300 flex items-center justify-center h-full"><Globe size={15} /></span>;
  return (
    <span className="flex items-center justify-center h-full">
      <img src={props.value} alt="" className="w-5 h-5 object-contain rounded-sm"
           onError={(e) => { e.target.style.display = 'none'; }} />
    </span>
  );
};

const CategoriesCellRenderer = (props) => {
  if (!props.value || !Array.isArray(props.value) || props.value.length === 0) return null;
  return (
    <span className="flex items-center gap-1 h-full overflow-hidden">
      {props.value.map((cat, i) => (
        <span key={i} className="bg-blue-50 text-blue-700 text-[10px] font-medium px-1.5 py-0.5 rounded whitespace-nowrap">
          {cat}
        </span>
      ))}
    </span>
  );
};

const PricingCellRenderer = (props) => {
  if (!props.value) return null;
  const val = props.value;
  let colorClass = "bg-gray-100 text-gray-700";
  if (val === "Free") colorClass = "bg-emerald-50 text-emerald-700 border border-emerald-200";
  else if (val === "Open Source") colorClass = "bg-purple-50 text-purple-700 border border-purple-200";
  else if (val === "Freemium") colorClass = "bg-blue-50 text-blue-700 border border-blue-200";
  else if (val === "Paid") colorClass = "bg-amber-50 text-amber-700 border border-amber-200";
  return (
    <span className="flex items-center h-full">
      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${colorClass}`}>
        {val}
      </span>
    </span>
  );
};

const FeaturesCellRenderer = (props) => {
  if (!props.value || !Array.isArray(props.value) || props.value.length === 0) return null;
  return (
    <span className="flex items-center gap-1 h-full overflow-hidden text-xs text-gray-600" title={props.value.join(' • ')}>
      {props.value.slice(0, 2).map((feat, i) => (
        <span key={i} className="bg-gray-100 text-gray-700 text-[10px] px-1.5 py-0.5 rounded truncate max-w-[140px]">
          {feat}
        </span>
      ))}
      {props.value.length > 2 && (
        <span className="text-[10px] text-gray-400 font-medium">+{props.value.length - 2}</span>
      )}
    </span>
  );
};

/* ── Main App ───────────────────────────────────────────── */
export default function App() {
  const { tools, loading, error, refetch } = useTools();
  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const gridRef = useRef(null);

  // Stats
  const totalTools = tools.length;
  const verifiedCount = tools.filter((t) => t.verified).length;
  const pendingCount = totalTools - verifiedCount;

  // Unique categories
  const allCategories = useMemo(() => {
    const cats = new Set();
    tools.forEach(tool => {
      if (Array.isArray(tool.categories)) {
        tool.categories.forEach(c => cats.add(c));
      }
    });
    return ['All', ...Array.from(cats).sort()];
  }, [tools]);

  // CSV export
  const onBtnExport = useCallback(() => {
    if (gridRef.current?.api) {
      gridRef.current.api.exportDataAsCsv({ fileName: 'ai_tools_export.csv' });
    }
  }, []);

  // Column definitions
  const columnDefs = useMemo(() => [
    {
      headerName: '#',
      valueGetter: (p) => (p.node?.rowIndex ?? 0) + 1,
      width: 55,
      pinned: 'left',
      sortable: false,
      filter: false,
      suppressHeaderMenuButton: true,
    },
    { field: 'logo_url', headerName: '', width: 50, cellRenderer: LogoCellRenderer, sortable: false, filter: false, suppressHeaderMenuButton: true },
    { field: 'name', headerName: 'Name', width: 170, pinned: 'left', filter: true },
    { field: 'pricing', headerName: 'Pricing', width: 115, cellRenderer: PricingCellRenderer, filter: true },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 260, filter: true, tooltipField: 'description' },
    { field: 'features', headerName: 'Key Features', width: 220, cellRenderer: FeaturesCellRenderer, filter: true },
    { field: 'url', headerName: 'Website', width: 180, cellRenderer: LinkCellRenderer, filter: true },
    { field: 'categories', headerName: 'Categories', width: 180, cellRenderer: CategoriesCellRenderer, filter: true,
      filterValueGetter: (p) => (p.data?.categories || []).join(', ') },
    { field: 'source_name', headerName: 'Source', width: 120, filter: true },
    { field: 'verified', headerName: 'Verified', width: 90, cellRenderer: VerifiedCellRenderer },
    { field: 'http_status', headerName: 'HTTP', width: 75 },
    { field: 'aliases', headerName: 'Aliases', width: 160,
      valueFormatter: (p) => (Array.isArray(p.value) ? p.value.join('; ') : ''), filter: true },
    { field: 'last_verified', headerName: 'Last Verified', width: 120 },
  ], []);

  const defaultColDef = useMemo(() => ({
    sortable: true,
    resizable: true,
    enableCellTextSelection: true,
  }), []);

  // External category filter
  const isExternalFilterPresent = useCallback(() => selectedCategory !== 'All', [selectedCategory]);

  const doesExternalFilterPass = useCallback((node) => {
    if (selectedCategory === 'All') return true;
    const cats = node.data?.categories;
    return Array.isArray(cats) && cats.includes(selectedCategory);
  }, [selectedCategory]);

  // Re-trigger grid filter when category pill changes
  useEffect(() => {
    if (gridRef.current?.api) {
      gridRef.current.api.onFilterChanged();
    }
  }, [selectedCategory]);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* ── Header ──────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg text-white shadow-sm">
            <Orbit size={22} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 tracking-tight leading-tight">AI Orbit Pipeline</h1>
            <p className="text-[11px] text-gray-500 font-medium">Data Collection &amp; Verification Dashboard</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => setIsDrawerOpen(true)}
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-3.5 py-1.5 rounded-md text-sm font-semibold shadow-sm transition-all active:scale-98 cursor-pointer">
            <Play size={14} fill="currentColor" /> Run Pipeline
          </button>
          <button onClick={refetch} disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors">
            <RefreshCw size={15} className={loading ? 'animate-spin text-blue-600' : ''} />
            {loading ? 'Syncing…' : 'Sync'}
          </button>
          <button onClick={onBtnExport}
            className="flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-md text-sm font-medium shadow-sm transition-colors">
            <Download size={14} /> Export CSV
          </button>
        </div>
      </header>

      {/* ── Stats Bar ───────────────────────────────── */}
      <div className="bg-white px-6 py-3 border-b border-gray-200 flex items-center gap-8 text-sm flex-wrap">
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs font-medium">Total Tools</span>
          <span className="text-xl font-bold text-gray-900">{totalTools.toLocaleString()}</span>
        </div>
        <div className="h-8 w-px bg-gray-200"></div>
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs font-medium">50K Target Progress</span>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-indigo-600">
              {((totalTools / 50000) * 100).toFixed(1)}%
            </span>
            <span className="text-xs text-gray-400 font-medium">({totalTools.toLocaleString()} / 50K)</span>
          </div>
        </div>
        <div className="h-8 w-px bg-gray-200"></div>
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs font-medium">Verified</span>
          <span className="text-xl font-bold text-green-600">{verifiedCount.toLocaleString()}</span>
        </div>
        <div className="h-8 w-px bg-gray-200"></div>
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs font-medium">Pending</span>
          <span className="text-xl font-bold text-yellow-600">{pendingCount.toLocaleString()}</span>
        </div>
        <div className="h-8 w-px bg-gray-200"></div>
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs font-medium">Categories</span>
          <span className="text-xl font-bold text-blue-600">{Math.max(0, allCategories.length - 1)}</span>
        </div>
      </div>

      {/* ── Controls Row ────────────────────────────── */}
      <div className="px-4 pt-3">
        <div className="flex items-center justify-between bg-white p-2.5 rounded-lg border border-gray-200 shadow-sm">
          {/* Category pills */}
          <div className="flex-1 overflow-x-auto no-scrollbar flex items-center gap-1.5 px-1">
            {allCategories.map(cat => (
              <button key={cat} onClick={() => setSelectedCategory(cat)}
                className={`whitespace-nowrap px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border ${
                  selectedCategory === cat
                    ? 'bg-blue-100 text-blue-700 border-blue-200'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border-transparent'
                }`}>
                {cat}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative ml-3 min-w-[220px]">
            <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none">
              <Search size={14} className="text-gray-400" />
            </div>
            <input type="text"
              className="block w-full pl-8 pr-3 py-1.5 border border-gray-300 rounded-md text-sm bg-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Quick search…"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* ── Error banner ────────────────────────────── */}
      {error && (
        <div className="mx-4 mt-3 bg-red-50 border-l-4 border-red-500 p-3 rounded-md flex items-center gap-2">
          <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-700">Error loading data: {error}</p>
        </div>
      )}

      {/* ── AG Grid ─────────────────────────────────── */}
      <main className="flex-1 px-4 py-3 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
        <div className="flex-1 bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden" style={{ height: 'calc(100vh - 270px)' }}>
          <AgGridReact
            ref={gridRef}
            theme={googleSheetsTheme}
            rowData={tools}
            columnDefs={columnDefs}
            defaultColDef={defaultColDef}
            rowHeight={32}
            headerHeight={36}
            pagination={true}
            paginationPageSize={50}
            paginationPageSizeSelector={[25, 50, 100, 200]}
            rowSelection="multiple"
            quickFilterText={searchText}
            isExternalFilterPresent={isExternalFilterPresent}
            doesExternalFilterPass={doesExternalFilterPass}
            tooltipShowDelay={400}
            loading={loading}
          />
        </div>
      </main>

      {/* ── Footer ──────────────────────────────────── */}
      <footer className="bg-white border-t border-gray-200 px-6 py-1.5 text-[11px] text-gray-400 flex justify-between">
        <span>AI Orbit Pipeline © {new Date().getFullYear()}</span>
        <span>Powered by Supabase</span>
      </footer>

      {/* ── Pipeline Runner Drawer ─────────────────── */}
      <PipelineDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onPipelineComplete={refetch}
      />
    </div>
  );
}
