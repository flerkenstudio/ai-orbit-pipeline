"""Global configuration for the AI Orbit ingestion pipeline."""
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # optional, raises rate limits
HF_TOKEN = os.getenv("HF_TOKEN", "")          # optional Hugging Face token for bulk Spaces

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
REQUEST_TIMEOUT = 12
MAX_RETRIES = 3
RATE_LIMIT_SLEEP = 0.5          # seconds between official-site fetches

TARGET_RECORDS = 300
DESCRIPTION_MIN = 30
DESCRIPTION_MAX = 400

# Approved category taxonomy
TAXONOMY = [
    "Coding", "Writing", "Image Generation", "Video Generation",
    "Audio & Music", "Chat & Assistant", "Search", "Productivity",
    "Design", "Marketing", "Data & Analytics", "Developer Tools",
    "Translation", "Education", "Research", "Automation",
    "Speech Recognition", "Agent Framework", "Open Source", "Other",
]

LOG_LEVEL = "INFO"
LOG_FILE = "logs/pipeline.log"
