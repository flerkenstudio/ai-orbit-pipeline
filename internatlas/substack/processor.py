"""Filtering, India Location Normalization, and 6-Section Substack Classifier."""
import re
from .config import SECTIONS_ORDER, MARQUEE_COMPANIES

EARLY_CAREER_REGEX = re.compile(
    r"\b(intern|interns|internship|trainee|apprentice|apprenticeship|grad\s+intern|"
    r"early\s+career|graduate\s+apprentice|industrial\s+trainee|diploma\s+trainee|"
    r"management\s+trainee|vapasi|resident|fellow|co-op|new\s+grad|2027\s+cohort|summer\s+2027)\b",
    re.I,
)

INDIA_KEYWORDS = [
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai",
    "gurugram", "gurgaon", "noida", "delhi", "new delhi", "chennai",
    "kolkata", "indore", "mysore", "mysuru", "sanand", "ahmedabad",
    "jaipur", "kochi", "coimbatore", "karnataka", "maharashtra",
    "telangana", "haryana", "tamil nadu", "uttar pradesh", "west bengal",
    "gujarat", "madhya pradesh",
]

CITY_NORMALIZATION = [
    (["bengaluru", "bangalore"], "Bengaluru, Karnataka"),
    (["hyderabad"], "Hyderabad, Telangana"),
    (["pune"], "Pune, Maharashtra"),
    (["mumbai"], "Mumbai, Maharashtra"),
    (["gurugram", "gurgaon"], "Gurugram, Haryana"),
    (["noida"], "Noida, Uttar Pradesh"),
    (["chennai"], "Chennai, Tamil Nadu"),
    (["kolkata"], "Kolkata, West Bengal"),
    (["indore"], "Indore, Madhya Pradesh"),
    (["mysore", "mysuru"], "Mysore, KA"),
    (["sanand"], "Sanand, Gujarat"),
    (["ahmedabad"], "Ahmedabad, Gujarat"),
    (["new delhi", "delhi"], "New Delhi, Delhi"),
    (["multiple locations"], "India (Multiple Locations)"),
]


def is_early_career(title: str) -> bool:
    if not title:
        return False
    return bool(EARLY_CAREER_REGEX.search(title))


def is_india_location(loc_raw: str) -> bool:
    if not loc_raw:
        return False
    text = loc_raw.lower()
    return any(k in text for k in INDIA_KEYWORDS)


def normalize_location_and_mode(loc_raw: str, mode_hint: str = "") -> tuple[str, str]:
    """Returns (formatted_location, work_mode) matching Substack style:
    e.g., ('Bengaluru, Karnataka', 'In-Office') or ('India - Remote', 'Remote')."""
    raw = (loc_raw or "Bengaluru, Karnataka").strip()
    lower = f"{raw} {mode_hint}".lower()

    is_remote = "remote" in lower or "work from home" in lower or "wfh" in lower
    work_mode = "Remote" if is_remote else "In-Office"

    for aliases, canonical in CITY_NORMALIZATION:
        if any(a in lower for a in aliases):
            return canonical, work_mode

    if is_remote:
        return "India - Remote", "Remote"

    if "india" in lower:
        return "India (Multiple Locations)", work_mode

    return raw, work_mode


def classify_domain_section(title: str, department: str = "") -> str:
    """Classifies role into one of the 5 specialized Substack domain sections."""
    text = f"{title} {department}".lower()

    # 1. AI & ML
    if any(k in text for k in [
        "ai", "ml", "machine learning", "artificial intelligence", "llm",
        "deep learning", "nlp", "computer vision", "gen ai", "generative ai",
        "aiml", "data resident"
    ]):
        return "Latest Artificial Intelligence & Machine Learning Opportunities"

    # 2. Product Design, Media & Content Strategy
    if any(k in text for k in [
        "design", "ux", "ui", "visual", "video editor", "content", "media",
        "game design", "artist", "creative", "roto", "paint", "copywriter",
        "photonics", "graphic"
    ]):
        return "Latest Product Design, Media & Content Strategy Roles"

    # 3. Data Analytics, Research & Intelligence
    if any(k in text for k in [
        "data science", "data curation", "data analyst", "analytics",
        "market research", "research intern", "quantitative", "quant",
        "database engine", "business intelligence", "bi intern"
    ]):
        return "Latest Data Analytics, Research & Intelligence Roles"

    # 4. Business Operations, HR, Marketing & Strategy
    if any(k in text for k in [
        "hr", "human resources", "talent acquisition", "recruitment",
        "marketing", "sales", "field sales", "founder's office", "founders office",
        "business", "operations", "finance", "accounting", "company secretary",
        "governance", "employer branding", "corporate communications",
        "customer operations", "supply chain", "learning & development",
        "hospitality", "facilities", "culture", "management trainee",
        "complaint operation", "people experience", "people team"
    ]):
        return "Latest Business Operations, HR, Marketing & Strategy Roles"

    # 5. Default: Software Development & Core Engineering
    return "Latest Software Development & Core Engineering Opportunities"


def compute_priority(company: str, role_title: str, apply_url: str) -> int:
    score = 60
    comp_lower = (company or "").lower().strip()
    if any(m in comp_lower for m in MARQUEE_COMPANIES):
        score += 30
    if any(k in role_title.lower() for k in ["software", "ai", "ml", "data", "quant", "product", "research"]):
        score += 5
    if apply_url and apply_url.startswith("https://"):
        score += 5
    return min(score, 100)


def organize_for_substack(jobs: list) -> list:
    """Assigns sections and selects top 10 marquee roles for 'Hottest New Opportunities - Apply Fast'."""
    # Sort by priority_score descending
    sorted_jobs = sorted(
        jobs,
        key=lambda j: (
            int(j.get("is_hot", 0)),
            int(j.get("priority_score", 0)),
        ),
        reverse=True,
    )

    hot_selected = []
    hot_companies_seen = set()
    remaining = []

    # First pass: honor explicitly marked hot roles or marquee companies (1 per company, max 10)
    for j in sorted_jobs:
        comp_key = (j.get("company") or "").lower().strip()
        is_marquee = any(m in comp_key for m in MARQUEE_COMPANIES)
        if len(hot_selected) < 10 and (j.get("is_hot") or is_marquee) and comp_key not in hot_companies_seen:
            j_copy = dict(j)
            j_copy["is_hot"] = 1
            j_copy["section"] = SECTIONS_ORDER[0]
            hot_selected.append(j_copy)
            hot_companies_seen.add(comp_key)
        else:
            j_copy = dict(j)
            j_copy["is_hot"] = 0
            if not j_copy.get("section") or j_copy["section"] == SECTIONS_ORDER[0]:
                j_copy["section"] = classify_domain_section(j_copy.get("role_title", ""))
            remaining.append(j_copy)

    return hot_selected + remaining
