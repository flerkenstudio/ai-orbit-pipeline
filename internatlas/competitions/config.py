"""Central configuration. Edit this file to change behaviour."""
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parent

DATA_DIR = REPO_ROOT / "data" / "competitions"
EXPORT_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "competitions.db"
SOURCES_FILE = MODULE_DIR / "sources.yaml"

DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# --- Scraping behaviour ---
REQUEST_DELAY_SECONDS = 3
REQUEST_TIMEOUT = 30
MAX_SCROLLS_UNSTOP = 12
PLAYWRIGHT_HEADLESS = True

# --- Link checking ---
LINKCHECK_CONCURRENCY = 5
DEAD_STATUS_CODES = {404, 410, 451}

# --- Lifecycle ---
IN_SEASON_MONTHS = {11, 12, 1, 2}
VERIFY_FREQUENCY_DAYS = {"in_season": 1, "off_season": 7}

# --- Premium heuristics ---
PREMIUM_ORGANISERS = [
    "iit bombay", "iit delhi", "iit madras", "iim ahmedabad",
    "iim bangalore", "iim calcutta", "bits pilani",
    "microsoft", "google", "amazon", "flipkart", "tata",
]
PREMIUM_MIN_PRIZE = 100000
