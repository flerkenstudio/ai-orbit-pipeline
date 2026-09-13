# AI Orbit Dashboard (Frontend)

Interactive web dashboard for the AI Orbit Data Ingestion Pipeline. Built with React 19, Vite, Tailwind CSS v4, and AG Grid Community.

## Features
- **AG Grid Spreadsheet Interface**: Sort, multi-filter, search, and export 260+ ingested AI tools.
- **Pipeline Runner Dialog**: Centered modal with real-time SSE progress, stage indicators, tool cards, and color-coded streaming logs.
- **Control Actions**: Start, stop/cancel, and restart pipeline ingestion directly from the browser.
- **Data Integration**: Connects to Supabase `ai_tools` table with local JSON fallback.

## Running Locally

```bash
# Install dependencies
npm install

# Start development server (port 5173)
npm run dev

# Build for production
npm run build
```
