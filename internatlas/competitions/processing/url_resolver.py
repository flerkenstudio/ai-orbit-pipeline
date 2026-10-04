"""Official Website URL Resolver.
Resolves the actual official website URL of the college, university, institute, or company hosting the opportunity."""
import re

ORGANISER_WEBSITE_MAP = {
    # Tier-1 IITs
    "iit bombay": "https://iitb.ac.in",
    "indian institute of technology, bombay": "https://iitb.ac.in",
    "iit delhi": "https://iitd.ac.in",
    "indian institute of technology, delhi": "https://iitd.ac.in",
    "iit madras": "https://iitm.ac.in",
    "indian institute of technology, madras": "https://iitm.ac.in",
    "iit kharagpur": "https://iitkgp.ac.in",
    "indian institute of technology, kharagpur": "https://iitkgp.ac.in",
    "iit kanpur": "https://iitk.ac.in",
    "indian institute of technology, kanpur": "https://iitk.ac.in",
    "iit roorkee": "https://iitr.ac.in",
    "indian institute of technology, roorkee": "https://iitr.ac.in",
    "iit guwahati": "https://iitg.ac.in",
    "indian institute of technology, guwahati": "https://iitg.ac.in",
    "iit hyderabad": "https://iith.ac.in",
    "indian institute of technology, hyderabad": "https://iith.ac.in",
    "iit indore": "https://iiti.ac.in",
    "indian institute of technology, indore": "https://iiti.ac.in",
    "iit ropar": "https://iitrpr.ac.in",
    "indian institute of technology, ropar": "https://iitrpr.ac.in",
    "iit bhu": "https://iitbhu.ac.in",
    "indian institute of technology, bhu": "https://iitbhu.ac.in",
    "iit ism dhanbad": "https://iitism.ac.in",
    "iit gandhinagar": "https://iitgn.ac.in",
    "iit patna": "https://iitp.ac.in",
    "iit mandi": "https://iitmandi.ac.in",
    "iit jodhpur": "https://iitj.ac.in",
    "iit bhubaneswar": "https://iitbbs.ac.in",
    "iit tirupati": "https://iittp.ac.in",
    "iit palakkad": "https://iitpkd.ac.in",

    # Tier-1 IIMs
    "iim ahmedabad": "https://iima.ac.in",
    "indian institute of management, ahmedabad": "https://iima.ac.in",
    "iim bangalore": "https://iimb.ac.in",
    "indian institute of management, bangalore": "https://iimb.ac.in",
    "iim calcutta": "https://iimcal.ac.in",
    "indian institute of management, calcutta": "https://iimcal.ac.in",
    "iim lucknow": "https://iiml.ac.in",
    "indian institute of management, lucknow": "https://iiml.ac.in",
    "iim kozhikode": "https://iimk.ac.in",
    "indian institute of management, kozhikode": "https://iimk.ac.in",
    "iim indore": "https://iimidr.ac.in",
    "indian institute of management, indore": "https://iimidr.ac.in",
    "iim rohtak": "https://iimrohtak.ac.in",
    "indian institute of management, rohtak": "https://iimrohtak.ac.in",
    "iim raipur": "https://iimraipur.ac.in",
    "indian institute of management, raipur": "https://iimraipur.ac.in",

    # BITS, NITs & IIITs
    "bits pilani": "https://bits-pilani.ac.in",
    "bits goa": "https://www.bits-pilani.ac.in/goa/",
    "bits hyderabad": "https://www.bits-pilani.ac.in/hyderabad/",
    "nit trichy": "https://nitt.edu",
    "national institute of technology, tiruchirappalli": "https://nitt.edu",
    "trichy": "https://nitt.edu",
    "nit surathkal": "https://nitk.ac.in",
    "national institute of technology, karnataka": "https://nitk.ac.in",
    "nit warangal": "https://nitw.ac.in",
    "nit rourkela": "https://nitrkl.ac.in",
    "nit calicut": "https://nitc.ac.in",
    "svnit": "https://svnit.ac.in",
    "dtu": "https://dtu.ac.in",
    "delhi technological university": "https://dtu.ac.in",
    "nsut": "https://nsut.ac.in",
    "iiit hyderabad": "https://iiit.ac.in",
    "iiit delhi": "https://iiitd.ac.in",
    "iiit allahabad": "https://iiita.ac.in",
    "iiit bangalore": "https://iiitb.ac.in",

    # DU & Top Colleges
    "fms": "https://fms.edu",
    "faculty of management studies": "https://fms.edu",
    "srcc": "https://srcc.du.ac.in",
    "shri ram college of commerce": "https://srcc.du.ac.in",
    "st. stephen": "https://ststephens.edu",
    "hindu college": "https://hinducollege.ac.in",
    "hansraj college": "https://hansrajcollege.ac.in",
    "kirori mal college": "https://kmc.du.ac.in",
    "lady shri ram": "https://lsr.edu.in",
    "miranda house": "https://mirandahouse.ac.in",
    "atma ram sanatan dharma": "https://arsdcollege.ac.in",
    "bennett university": "https://bennett.edu.in",
    "goa institute of management": "https://gim.ac.in",
    "bannari amman": "https://bitsathy.ac.in",
    "upes": "https://upes.ac.in",
    "kiet": "https://kiet.edu",
    "christ university": "https://christuniversity.in",
    "symbiosis": "https://siu.edu.in",
    "nmims": "https://nmims.edu",
    "nitte": "https://nitte.edu.in",

    # Major Tech & Corporate Companies
    "microsoft": "https://imaginecup.microsoft.com",
    "google": "https://developers.google.com",
    "flipkart": "https://grid.flipkart.com",
    "amazon": "https://amazon.com",
    "tata": "https://tata.com",
    "hcltech": "https://hcltech.com",
    "godrej": "https://godrej.com",
    "kartexa": "https://kartexa.com",
    "algobulls": "https://algobulls.com",
    "gogo pogo": "https://gogopogo.in",
    "accenture": "https://accenture.com",
    "tcs": "https://tcs.com",
    "infosys": "https://infosys.com",
    "wipro": "https://wipro.com",
    "ibm": "https://ibm.com",
    "meta": "https://meta.com",
    "adobe": "https://adobe.com",
    "samsung": "https://samsung.com",
    "uber": "https://uber.com",
}


def clean_url_string(u: str) -> str:
    if not u or not isinstance(u, str):
        return ""
    m = re.search(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s,;\"]*)?', u)
    if m:
        url = m.group(0).rstrip('.,;')
        if not any(d in url.lower() for d in ['unstop.com', 'devfolio.co', 'hackerearth.com']):
            return url
    return ""


def resolve_official_url(raw: dict) -> str:
    """Resolves the actual official website URL of the college, university, institute, or company hosting the opportunity."""
    if not isinstance(raw, dict):
        return ""

    # 1. Map Organiser Name against lookup table
    org_name = (raw.get("organiser") or "").lower().strip()
    for key, official_url in ORGANISER_WEBSITE_MAP.items():
        if key in org_name:
            return official_url

    # 2. Check title against lookup table
    title = (raw.get("title") or "").lower()
    for key, official_url in ORGANISER_WEBSITE_MAP.items():
        if key in title:
            return official_url

    # 3. Check official_email_domains (e.g. @iiml.ac.in -> https://iiml.ac.in)
    email_domain = raw.get("official_email_domains")
    if email_domain and isinstance(email_domain, str):
        first_dom = email_domain.split(',')[0].strip()
        dom_match = re.search(r'([a-zA-Z0-9-]+\.(?:ac\.in|edu\.in|edu|com|org|co\.in|in))', first_dom)
        if dom_match:
            dom = dom_match.group(1).lower()
            if not any(free in dom for free in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'unstop.com', 'unstop.demo']):
                return f"https://{dom}"

    # 4. Check direct site_url / website_url / external_url in raw fields
    for key in ["site_url", "website_url", "external_url", "official_website"]:
        u = clean_url_string(raw.get(key))
        if u:
            return u

    # 5. Extract external links from description/eligibility text
    desc = raw.get("eligibility") or raw.get("description") or raw.get("regnRequirements") or ""
    if desc:
        ext_urls = re.findall(r'https?://[^\s\"\'<>]+', str(desc))
        for u in ext_urls:
            u_clean = clean_url_string(u)
            if u_clean and not any(d in u_clean.lower() for d in ['google.com/forms', 'docs.google.com', 'discord', 'telegram', 'whatsapp', 'github.com']):
                return u_clean

    # 6. Fallback domain derivation from Organiser Name
    clean_org = re.sub(r'\(.*?\)', '', org_name).strip()
    words = [w for w in clean_org.split() if w not in ['indian', 'institute', 'of', 'technology', 'management', 'university', 'college', 'deemed', 'the', '&', 'and', 'national', 'school', 'department', 'studies', 'faculty']]
    if words:
        slug = "".join(words[:2])
        if len(slug) >= 3 and slug.isalpha():
            return f"https://www.{slug}.ac.in"

    # Fallback to discovery URL if nothing else can be resolved
    return raw.get("discovery_url") or "https://unstop.com"
