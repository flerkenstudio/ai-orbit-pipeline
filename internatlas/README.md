# InternAtlas — Competitions Pipeline (drop-in module)

Scrape -> clean -> dedupe (SQLite) -> link-check -> expire -> Excel.

## Setup (Windows / Mac / Linux)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r competitions/requirements.txt
playwright install chromium
```
Python 3.10+ required.

## 1. Test with no internet / no scraping (demo data)
```bash
python -m competitions.main --demo
```
Creates `data/competitions/competitions.db` and an Excel file in `data/competitions/exports/`.

## 2. Run unit tests
```bash
python -m unittest discover -s tests -v
```

## 3. Real run (hits live sites)
```bash
python -m competitions.main
```
Useful flags:
- `--no-linkcheck`  skip dead-link checking (faster)
- `--only unstop`   run only one source (unstop, devfolio, or a name from sources.yaml)
- `--freq`          print recommended re-verify frequency

## 4. Plug into your existing InternAtlas repo
Copy the `competitions/` folder into your repo root, `pip install -r competitions/requirements.txt`, then in your existing entry point:
```python
from competitions.pipeline import run_competitions_pipeline
run_competitions_pipeline()
```
Data is stored in `<repo_root>/data/competitions/` (never touches your existing data).

## Notes
- CSS selectors in `scrapers/unstop.py`, `scrapers/devfolio.py` and `sources.yaml` are best guesses. Sites change; inspect with DevTools and update. Better: find the JSON XHR API in the Network tab.
- Each source fails independently; one broken site never kills the run.
- Add static sites by editing `competitions/sources.yaml` only. Entries with `engine: playwright` are skipped until you write a dedicated adapter.
- Always spot-check scraped data before publishing.
