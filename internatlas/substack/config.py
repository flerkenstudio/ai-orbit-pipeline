"""Configuration for InternAtlas Substack Internships & Early Career Pipeline."""
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parent

DATA_DIR = REPO_ROOT / "data" / "substack"
EXPORT_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "internships.db"
COMPANIES_FILE = MODULE_DIR / "companies.yaml"

DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT = 15
MAX_WORKERS = 15

# Section ordering matching the exact Substack post template
SECTIONS_ORDER = [
    "Hottest New Opportunities - Apply Fast",
    "Latest Software Development & Core Engineering Opportunities",
    "Latest Artificial Intelligence & Machine Learning Opportunities",
    "Latest Data Analytics, Research & Intelligence Roles",
    "Latest Product Design, Media & Content Strategy Roles",
    "Latest Business Operations, HR, Marketing & Strategy Roles",
]

# Marquee / Tier-1 companies prioritized for "Hottest New Opportunities - Apply Fast"
MARQUEE_COMPANIES = {
    "thoughtworks", "stripe", "nvidia", "walmart", "walmart global tech",
    "groww", "smartsheet", "marvell", "marvell technology", "hpe",
    "hewlett packard enterprise", "paytm", "phonepe", "salesforce",
    "cisco", "cisco systems", "tower research", "tower research capital",
    "alphagrep", "alphagrep securities", "hackerrank", "meesho", "fampay",
    "fi money", "sarvam ai", "singlestore", "inmobi", "zynga", "scopely",
    "ge aerospace", "ge vernova", "procter & gamble", "p&g", "micron",
    "micron technology", "autodesk", "baker hughes", "stryker", "apollo",
    "apollo global management", "invesco", "dr. reddy's", "bosch", "bosch group",
    "altera", "merck", "iqvia", "cadence", "cadence design systems",
}
