# AI Orbit Data Ingestion Pipeline

API-first, modular ingestion engine for building a clean dataset of AI tools.

## Architecture
```
Discovery -> Extraction -> Cleaning -> Normalization -> Deduplication
          -> Classification -> Relationships -> Validation -> Export
```

Each stage lives in its own package under `src/`, so any stage can be
swapped or extended without touching the others.

## Entity Resolution Strategy
1. **Domain-first identity** — the canonical registrable domain
   (e.g. `openai.com`) is the primary key for merging duplicates.
2. **Fuzzy name matching** (RapidFuzz, token-sort threshold 92) catches
   near-duplicates that don't share a domain and flags cross-domain
   conflicts into a review queue for manual inspection.
3. **Stable UUIDv5 IDs** are derived from `entity_type + canonical URL`,
   so re-running the pipeline never changes an existing entity's ID.

## Quick Start

### 1. Backend & CLI Pipeline
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Add SUPABASE and optional GITHUB_TOKEN credentials
python run.py                 # Run pipeline directly via CLI
```

### 2. Full Interactive Web Dashboard & Real-Time Runner
Start the FastAPI server and React frontend to run and monitor the pipeline interactively with live progress, streaming logs, and stop controls:

```bash
# Terminal 1 — Start Backend Server (port 8000)
python server.py

# Terminal 2 — Start Frontend Dashboard (port 5173)
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` to access the live dashboard.

## Output

| File | Description |
|---|---|
| `data/entities.json` | Deduplicated, classified tool records |
| `data/relationships.json` | `Tool -> solves -> Task` edges |
| `data/validation_report.json` | Pass/fail counts and issue breakdown |
| `data/export/tools_sheet.csv` | Flat CSV, ready to import into Google Sheets |

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Scaling Path
The current run targets ~300 records from 3 sources (curated seed list +
GitHub + Hacker News). To scale to tens of thousands of records, add more
`BaseSource` implementations and run discovery + extraction with async
workers behind a queue — the core architecture (resolve -> classify ->
validate -> export) doesn't need to change.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: src` | Run `python run.py` from the project root, not from inside `src/` |
| GitHub returns 403 | Add `GITHUB_TOKEN=ghp_xxx` to `.env` (free token at github.com/settings/tokens) |
| Many `Site unreachable` warnings | Normal — some sites block bots; those entities are marked `Pending` instead of failing the whole run |
| Too few entities | Add more rows to `SEEDS` in `src/discovery/seed_source.py` — each is a guaranteed-verified record |
