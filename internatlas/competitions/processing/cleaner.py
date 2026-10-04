"""Normalize raw scraped dicts into standardized records with Priority Scoring and Real Official URL Resolution."""
import re
from datetime import datetime

from ..schema import make_record
from ..config import PREMIUM_ORGANISERS, PREMIUM_MIN_PRIZE
from .url_resolver import resolve_official_url

CATEGORY_KEYWORDS = {
    "hackathon": ["hackathon", "hack", "devfest", "buildathon", "hackfest"],
    "coding": ["code", "coding", "algorithm", "programming", "icpc", "hackerearth", "dsa", "competitive programming", "developer", "cp", "contest"],
    "case": ["case", "consult", "strategy", "business challenge", "valuation", "brand", "analytics"],
    "quiz": ["quiz", "crucible", "trivia", "brainwave", "olympiad", "general knowledge", "gyan"],
    "bplan": ["business plan", "bplan", "b-plan", "startup", "pitch", "e-cell", "venture", "incubation", "entrepreneurship", "conquest", "venture capital"],
    "design": ["design", "ui/ux", "ux", "logo", "cad", "creative", "rendering", "graphic", "art"],
    "debate": ["debate", "mun", "model united nations", "parliamentary", "elocution", "oratory", "declamation"],
}

PRIZE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(k|l|lakhs?|lacs?|crore|cr)?\b", re.I)

DATE_FORMATS = [
    "%d %b %Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d",
    "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y %I:%M %p",
    "%d %b, %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"
]

TIER1_ORGS = [
    "iit", "indian institute of technology",
    "iim", "indian institute of management",
    "bits", "bits pilani",
    "nit", "national institute of technology",
    "srcc", "shri ram college", "st stephen",
    "microsoft", "google", "amazon", "flipkart", "tata", "meta", "apple",
    "adobe", "samsung", "uber", "goldman sachs", "morgan stanley", "jp morgan",
    "mckinsey", "bain", "bcg", "hcltech", "godrej", "tcs"
]


def parse_date(raw):
    """Best-effort date -> ISO string (YYYY-MM-DD). None if unparseable."""
    if not raw:
        return None
    raw_str = str(raw).strip()
    if "T" in raw_str:
        try:
            return raw_str.split("T")[0]
        except Exception:
            pass
    
    clean_str = re.sub(r"(?i)^(apply by|deadline|registration ends?|ends?|starts?)[:\s]*", "", raw_str)
    clean_str = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", clean_str)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(clean_str, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_prize_value(prize_text):
    if not prize_text:
        return None
    m = PRIZE_PATTERN.search(prize_text.replace(",", ""))
    if not m:
        return None
    val = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit == "k":
        val *= 1_000
    elif unit.startswith("l"):
        val *= 100_000
    elif unit in ("cr", "crore"):
        val *= 10_000_000
    return val


def classify_category(title: str, prize_text: str = "", raw_type: str = "") -> str:
    text = f"{title} {prize_text} {raw_type}".lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in text for k in kws):
            return cat
    return "other"


def calculate_priority_score(rec: dict) -> int:
    """Calculates priority score (0 to 100) based on organiser credibility, prize pool, participation, and eligibility clarity."""
    score = 0
    org = (rec.get("organiser") or "").lower()
    org_tier = rec.get("organiser_tier")
    prize_val = rec.get("prize_value") or 0
    prize_text = (rec.get("prize_pool") or "").lower()
    url = rec.get("official_url") or ""

    # 1. Organiser Reputation (Up to 35 pts)
    if org_tier == 1 or any(t in org for t in TIER1_ORGS):
        score += 35
    elif org_tier == 2 or any(word in org for word in ["university", "college", "institute", "technologies", "solutions"]):
        score += 20
    elif rec.get("source") in ("unstop", "devfolio", "hackerearth"):
        score += 15

    # 2. Meaningful Prize / Recognition (Up to 25 pts)
    if prize_val >= 100_000:
        score += 25
    elif prize_val >= 25_000:
        score += 18
    elif prize_val >= 5_000:
        score += 12
    elif any(k in prize_text for k in ["ppo", "internship", "cash", "certificate", "trophy", "voucher", "grant", "reward"]):
        score += 10

    # 3. Active Official Website Link (Up to 20 pts)
    if url.startswith("https://") or url.startswith("http://"):
        score += 15
        if not any(d in url.lower() for d in ["unstop.com", "devfolio.co", "hackerearth.com", "example.com"]):
            score += 5  # Bonus for actual organiser official domain!

    # 4. Clear Eligibility & Registration Deadline (Up to 20 pts)
    deadline = rec.get("reg_deadline")
    if deadline:
        score += 10
        try:
            d = datetime.strptime(deadline, "%Y-%m-%d").date()
            if d >= datetime.now().date():
                score += 10
        except Exception:
            pass

    return min(score, 100)


def is_premium(rec: dict) -> bool:
    org = (rec.get("organiser") or "").lower()
    prize_val = rec.get("prize_value") or 0
    if any(name in org for name in TIER1_ORGS):
        return True
    if prize_val >= PREMIUM_MIN_PRIZE:
        return True
    return rec.get("priority_score", 0) >= 60


def clean(raw: dict):
    """Returns a standardized record with resolved official organiser URL, or None if required fields missing."""
    if not isinstance(raw, dict):
        return None
    title = (raw.get("title") or "").strip()
    raw_url = (raw.get("official_url") or raw.get("discovery_url") or "").strip()
    if not title or not raw_url:
        return None
        
    prize_text = (raw.get("prize_pool") or "").strip()
    prize_value = extract_prize_value(prize_text)
    
    cat = classify_category(
        title, 
        prize_text, 
        raw_type=f"{raw.get('type_raw', '')} {raw.get('subtype_raw', '')} {raw.get('filter_tags', '')}"
    )

    elig = raw.get("eligibility")
    elig_str = str(elig)[:300] if elig else None

    # Resolve actual official organiser website URL
    resolved_url = resolve_official_url(raw)

    rec = make_record(
        title=title,
        organiser=(raw.get("organiser") or "").strip(),
        organiser_type=raw.get("organiser_type", "platform"),
        category=cat,
        eligibility=elig_str,
        mode=raw.get("mode", "Online"),
        reg_deadline=parse_date(raw.get("reg_deadline")),
        event_date=parse_date(raw.get("event_date")),
        prize_pool=prize_text,
        prize_value=prize_value,
        official_url=resolved_url,
        discovery_url=raw_url,
        source=raw.get("source", ""),
    )
    
    rec["priority_score"] = calculate_priority_score({**rec, "organiser_tier": raw.get("organiser_tier")})
    rec["premium"] = int(is_premium(rec))
    return rec
