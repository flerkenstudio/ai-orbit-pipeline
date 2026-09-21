"""Universal Web & Directory Scraper
Extracts structured AI tool / agent records from ANY website or directory link.
Outputs data adhering strictly to the AIOrbit schema in styled Excel (.xlsx) and CSV.
"""
import argparse
import concurrent.futures
import json
import logging
import os
import re
import sys
import os
import time
import urllib.parse
from typing import Dict, List, Any, Optional, Set

import requests
from bs4 import BeautifulSoup
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.scrapers.agenthunter_scraper import parse_agent_page as parse_agenthunter_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("universal_scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

COLUMNS = [
    ("name", "Name", 22),
    ("slug", "Slug", 18),
    ("shortDescription", "Short Description", 30),
    ("description", "Tagline / Description", 40),
    ("longDescription", "Long Description (About)", 60),
    ("websiteUrl", "Official Website URL", 32),
    ("logoUrl", "Logo URL", 32),
    ("category", "Primary Category", 20),
    ("categorySlug", "Category Slug", 18),
    ("primaryTask", "Primary Task(s)", 25),
    ("features", "Key Features", 50),
    ("useCases", "Use Cases", 50),
    ("integrations", "Integrations", 25),
    ("compatibility", "Supported Platforms", 25),
    ("pricingModel", "Pricing Model", 16),
    ("pricingRaw", "Pricing Raw", 20),
    ("hasApi", "Has API", 12),
    ("apiDocsUrl", "API Docs URL", 25),
    ("isOpenSource", "Is Open Source", 14),
    ("githubUrl", "GitHub Repository", 30),
    ("provider", "Provider / Company", 20),
    ("providerWebsite", "Provider Website", 25),
    ("releaseDate", "Release Date", 16),
    ("pros", "Pros", 30),
    ("cons", "Cons", 30),
]


def clean_tracking_url(url: str) -> str:
    """Strip utm_ and tracking parameters from a URL."""
    if not url:
        return ""
    try:
        p = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qs(p.query)
        clean_q = {k: v for k, v in q.items() if not k.lower().startswith(("utm_", "ref", "source", "via"))}
        new_query = urllib.parse.urlencode(clean_q, doseq=True)
        return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, ""))
    except Exception:
        return url.strip()


def slugify(text: str) -> str:
    if not text:
        return ""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def is_generic_page(url: str) -> bool:
    """Return True if URL is a generic site page (not a tool detail page)."""
    path = urllib.parse.urlparse(url).path.lower().rstrip("/")
    if not path or path in ["", "/", "/index.html"]:
        return True
    bad_segments = [
        "privacy", "terms", "policy", "login", "signup", "register",
        "about", "contact", "pricing", "blog", "posts", "author", "tag",
        "category", "categories", "faq", "help", "support", "careers",
        "jobs", "press", "cookie", "legal", "sitemap", "feed"
    ]
    parts = [p for p in path.split("/") if p]
    if any(p in bad_segments for p in parts):
        return True
    if any(url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg", ".css", ".js", ".pdf", ".xml"]):
        return True
    return False


def discover_urls_from_site(target_url: str, limit: Optional[int] = None) -> List[str]:
    """Dynamically discover detail/tool URLs from ANY given website link or sitemap."""
    target_url = target_url.strip()
    if not target_url.startswith("http"):
        target_url = "https://" + target_url

    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    root_url = f"{parsed.scheme}://{parsed.netloc}"

    # Special handling for agenthunter.io
    if "agenthunter.io" in domain:
        log.info("AgentHunter directory detected, fetching specialized sitemap...")
        try:
            r = requests.get("https://www.agenthunter.io/sitemap.xml", headers=HEADERS, timeout=20)
            if r.status_code == 200:
                urls = re.findall(r"<loc>(https://www\.agenthunter\.io/agent/[^<]+)</loc>", r.text)
                return sorted(list(set(urls)))
        except Exception as exc:
            log.warning("AgentHunter sitemap fetch failed: %s", exc)

    discovered_urls: Set[str] = set()

    # 1. Check XML Sitemaps
    sitemap_candidates = [
        f"{root_url}/sitemap.xml",
        f"{root_url}/sitemap_index.xml",
        f"{root_url}/sitemaps.xml",
        f"{root_url}/robots.txt",
    ]

    for sm_url in sitemap_candidates:
        if limit and len(discovered_urls) >= limit:
            break
        try:
            r = requests.get(sm_url, headers=HEADERS, timeout=12)
            if r.status_code != 200:
                continue

            if sm_url.endswith("robots.txt"):
                # Parse sitemap entries from robots.txt
                sm_links = re.findall(r"Sitemap:\s*(https?://\S+)", r.text, re.I)
                for sl in sm_links:
                    try:
                        sr = requests.get(sl, headers=HEADERS, timeout=12)
                        if sr.status_code == 200:
                            locs = re.findall(r"<loc>(https?://[^<]+)</loc>", sr.text)
                            for loc in locs:
                                if not loc.endswith(".xml") and not is_generic_page(loc):
                                    discovered_urls.add(loc)
                    except Exception:
                        pass
                continue

            # Check if this is a sitemapindex
            sub_sitemaps = re.findall(r"<loc>(https?://[^<]+sitemap[^<]*\.xml)</loc>", r.text, re.I)
            if sub_sitemaps:
                log.info("Discovered sitemap index at %s with %d sub-sitemaps.", sm_url, len(sub_sitemaps))
                for sub in sub_sitemaps:
                    if limit and len(discovered_urls) >= limit:
                        break
                    try:
                        sub_r = requests.get(sub, headers=HEADERS, timeout=12)
                        if sub_r.status_code == 200:
                            locs = re.findall(r"<loc>(https?://[^<]+)</loc>", sub_r.text)
                            for loc in locs:
                                if not loc.endswith(".xml") and not is_generic_page(loc):
                                    discovered_urls.add(loc)
                    except Exception:
                        pass
            else:
                locs = re.findall(r"<loc>(https?://[^<]+)</loc>", r.text)
                for loc in locs:
                    if not loc.endswith(".xml") and not is_generic_page(loc):
                        discovered_urls.add(loc)

            if len(discovered_urls) > 5:
                log.info("Discovered %d URLs via sitemap %s", len(discovered_urls), sm_url)
                break
        except Exception as exc:
            log.warning("Sitemap check warning for %s: %s", sm_url, exc)

    # 2. HTML Link Extraction & Crawling on target_url directly
    if not discovered_urls or len(discovered_urls) < 10:
        log.info("Crawling links directly from target page: %s", target_url)
        pages_to_crawl = [target_url]
        crawled_pages = set()

        # Follow pagination up to 5 pages if needed
        while pages_to_crawl and (not limit or len(discovered_urls) < limit):
            current_page = pages_to_crawl.pop(0)
            if current_page in crawled_pages:
                continue
            crawled_pages.add(current_page)

            try:
                r = requests.get(current_page, headers=HEADERS, timeout=12)
                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    full_link = urllib.parse.urljoin(current_page, href)
                    p_link = urllib.parse.urlparse(full_link)

                    # Same domain check
                    if p_link.netloc.lower() == domain:
                        clean_link = clean_tracking_url(full_link)
                        # Check pagination
                        if any(k in href.lower() for k in ["page=", "/page/", "?p=", "/p/"]) and clean_link not in crawled_pages:
                            if len(crawled_pages) < 8 and clean_link not in pages_to_crawl:
                                pages_to_crawl.append(clean_link)
                        elif not is_generic_page(clean_link):
                            discovered_urls.add(clean_link)
            except Exception as exc:
                log.warning("Page crawl error for %s: %s", current_page, exc)

    # If no sub-links could be extracted (e.g. single tool website or landing page)
    if not discovered_urls:
        log.info("No sub-pages discovered; adding target URL as single tool: %s", target_url)
        discovered_urls.add(target_url)

    final_list = sorted(list(discovered_urls))
    log.info("Total discovered URLs for %s: %d", domain, len(final_list))
    return final_list


def parse_generic_page(url: str, source_domain: str = "") -> Optional[Dict[str, Any]]:
    """Universal parser that extracts structured tool metadata from ANY web page."""
    # If it is agenthunter, use the specialized parser
    if "agenthunter.io" in url.lower():
        return parse_agenthunter_page(url)

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            log.warning("HTTP %d for %s", r.status_code, url)
            return None
    except Exception as exc:
        log.warning("Fetch error for %s: %s", url, exc)
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    parsed_url = urllib.parse.urlparse(url)
    slug = [p for p in parsed_url.path.strip("/").split("/") if p][-1] if parsed_url.path.strip("/") else slugify(parsed_url.netloc)

    # 1. JSON-LD Extraction
    ld_data = {}
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") in ["SoftwareApplication", "WebApplication", "Product", "Organization"]:
                        ld_data = item
                        break
            elif isinstance(data, dict):
                if data.get("@type") in ["SoftwareApplication", "WebApplication", "Product", "Organization"]:
                    ld_data = data
                    break
                elif "@graph" in data and isinstance(data["@graph"], list):
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") in ["SoftwareApplication", "WebApplication", "Product", "Organization"]:
                            ld_data = item
                            break
        except Exception:
            continue

    # 2. Name Extraction
    name = ld_data.get("name")
    if not name:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            name = og_title["content"].strip()
    if not name:
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)
    if not name:
        title_el = soup.find("title")
        if title_el:
            raw_title = title_el.get_text(strip=True)
            # Remove title decorations
            name = re.split(r"[-|:•—]", raw_title)[0].strip()
    if not name:
        name = slug.replace("-", " ").title()

    # Clean name
    name = re.sub(r"\s+", " ", name).strip()

    # 3. Description / Tagline Extraction
    tagline = ld_data.get("description")
    if not tagline:
        meta_desc = (
            soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", property="og:description")
            or soup.find("meta", attrs={"name": "twitter:description"})
        )
        if meta_desc and meta_desc.get("content"):
            tagline = meta_desc["content"].strip()

    if not tagline:
        # First informative paragraph
        for p in soup.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if len(txt) > 30:
                tagline = txt
                break

    tagline = re.sub(r"\s+", " ", tagline or "").strip()

    # Short Description
    words = tagline.split()
    if words and len(words) <= 10:
        short_desc = tagline
    elif words:
        short_desc = " ".join(words[:8])
    else:
        short_desc = f"{name} - AI tool"

    # 4. Long Description (About)
    long_desc_items = []
    for heading in soup.find_all(["h2", "h3"]):
        h_text = heading.get_text(strip=True).lower()
        if any(w in h_text for w in ["about", "overview", "what is", "description", "details", "introduction"]):
            parent = heading.find_parent()
            if parent:
                for p in parent.find_all("p"):
                    ptxt = p.get_text(" ", strip=True)
                    if ptxt and ptxt not in long_desc_items and len(ptxt) > 20:
                        long_desc_items.append(ptxt)

    if long_desc_items:
        long_description = " ".join(long_desc_items)
    else:
        long_description = tagline

    long_description = re.sub(r"\s+", " ", long_description).strip()

    # 5. Outbound Official Website Link
    website_url = ""
    github_url = ""
    api_docs_url = ""

    current_domain = parsed_url.netloc.lower()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        link_text = a.get_text(" ", strip=True).lower()
        if not href.startswith("http"):
            continue

        p_href = urllib.parse.urlparse(href)
        href_domain = p_href.netloc.lower()

        if "github.com" in href_domain:
            if not github_url or len(href) < len(github_url):
                github_url = clean_tracking_url(href)
        elif any(w in link_text for w in ["visit", "website", "get started", "launch", "try now", "go to"]):
            if href_domain != current_domain and not any(d in href_domain for d in ["twitter.com", "x.com", "facebook.com", "linkedin.com", "youtube.com"]):
                website_url = clean_tracking_url(href)
        elif any(w in link_text for w in ["api doc", "docs", "documentation", "developers"]):
            api_docs_url = clean_tracking_url(href)

    # If the page itself is the official site
    if not website_url:
        website_url = clean_tracking_url(url)

    # 6. Logo Extraction
    logo_url = ld_data.get("image") or ld_data.get("logo")
    if not logo_url:
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_img and og_img.get("content"):
            logo_url = og_img["content"].strip()
    if not logo_url:
        icon_el = soup.find("link", rel=lambda r: r and "icon" in r.lower())
        if icon_el and icon_el.get("href"):
            logo_url = urllib.parse.urljoin(url, icon_el["href"])
    if not logo_url:
        target_domain = urllib.parse.urlparse(website_url).netloc
        logo_url = f"https://www.google.com/s2/favicons?domain={target_domain}&sz=128"

    # 7. Category & Classification
    category = ld_data.get("applicationCategory") or ""
    if not category:
        # Check breadcrumbs
        for bc in soup.find_all(["nav", "div"], attrs={"aria-label": lambda a: a and "breadcrumb" in a.lower()}):
            items = [li.get_text(strip=True) for li in bc.find_all("li") if li.get_text(strip=True)]
            if len(items) > 1:
                category = items[-2]
                break
    if not category:
        text_corpus = f"{name} {tagline} {long_description}".lower()
        if "code" in text_corpus or "developer" in text_corpus:
            category = "Coding AI"
        elif "image" in text_corpus or "photo" in text_corpus or "art" in text_corpus:
            category = "Image Generation"
        elif "video" in text_corpus:
            category = "Video AI"
        elif "audio" in text_corpus or "voice" in text_corpus:
            category = "Voice & Audio"
        elif "writing" in text_corpus or "content" in text_corpus or "copy" in text_corpus:
            category = "Copywriting & Content"
        elif "automation" in text_corpus or "agent" in text_corpus:
            category = "Task Automation"
        elif "support" in text_corpus or "chat" in text_corpus:
            category = "Customer Support"
        else:
            category = "Productivity AI"

    # 8. Key Features Extraction
    features_list = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        h_text = heading.get_text(strip=True).lower()
        if any(w in h_text for w in ["feature", "capability", "capabilities", "why choose", "benefits"]):
            parent = heading.find_parent()
            if parent:
                for li in parent.find_all("li"):
                    txt = li.get_text(" ", strip=True)
                    if txt and len(txt) > 6 and txt not in features_list:
                        features_list.append(txt)
            if len(features_list) >= 3:
                break

    if not features_list:
        for li in soup.find_all("li"):
            txt = li.get_text(" ", strip=True)
            if 15 < len(txt) < 150 and not any(b in txt.lower() for b in ["privacy", "terms", "login", "cookie"]):
                features_list.append(txt)
            if len(features_list) >= 5:
                break

    # 9. Use Cases Extraction
    use_cases_list = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        h_text = heading.get_text(strip=True).lower()
        if any(w in h_text for w in ["use case", "use-case", "who is", "applications", "built for"]):
            parent = heading.find_parent()
            if parent:
                for li in parent.find_all("li"):
                    txt = li.get_text(" ", strip=True)
                    if txt and len(txt) > 6 and txt not in use_cases_list:
                        use_cases_list.append(txt)
            if len(use_cases_list) >= 3:
                break

    # 10. Compatibility & Integrations
    compatibility_list = []
    text_corpus = f"{name} {tagline} {long_description}".lower()
    for platform in ["Web Browser", "Mac", "Windows", "Linux", "iOS", "Android", "Slack", "Discord", "Chrome Extension", "Docker"]:
        if platform.lower() in text_corpus:
            compatibility_list.append(platform)
    if not compatibility_list:
        compatibility_list.append("Web Browser")

    integrations_list = []
    for app_name in ["Slack", "Discord", "GitHub", "Notion", "Google Workspace", "Zapier", "Jira", "Telegram", "Linear"]:
        if app_name.lower() in text_corpus:
            integrations_list.append(app_name)

    # 11. Pricing Model
    if "free trial" in text_corpus:
        pricing_model = "FREE_TRIAL"
    elif "open source" in text_corpus or github_url:
        pricing_model = "FREE"
    elif "100% free" in text_corpus or "free forever" in text_corpus or "completely free" in text_corpus:
        pricing_model = "FREE"
    elif any(term in text_corpus for term in ["$", "/mo", "per month", "subscription", "billed annually"]):
        pricing_model = "PAID"
    elif "freemium" in text_corpus or "free plan" in text_corpus or "free tier" in text_corpus:
        pricing_model = "FREEMIUM"
    else:
        pricing_model = "FREEMIUM"

    pricing_raw = "Free plan available" if pricing_model in ("FREE", "FREEMIUM") else "Contact for pricing"

    # 12. Technical Flags
    is_open_source = bool(github_url) or "open source" in text_corpus or "open-source" in text_corpus
    has_api = bool(api_docs_url) or any(k in text_corpus for k in ["rest api", "api access", "api integration", "api key"])

    record = {
        "name": name,
        "slug": slugify(slug or name),
        "shortDescription": short_desc,
        "description": tagline or short_desc,
        "longDescription": long_description,
        "websiteUrl": website_url,
        "logoUrl": logo_url,
        "category": category,
        "categorySlug": slugify(category),
        "primaryTask": category,
        "features": "\n• " + "\n• ".join(features_list[:6]) if features_list else "",
        "useCases": "\n• " + "\n• ".join(use_cases_list[:5]) if use_cases_list else "",
        "integrations": "; ".join(integrations_list),
        "compatibility": "; ".join(compatibility_list),
        "pricingModel": pricing_model,
        "pricingRaw": pricing_raw,
        "hasApi": has_api,
        "apiDocsUrl": api_docs_url,
        "isOpenSource": is_open_source,
        "githubUrl": github_url,
        "provider": "",
        "providerWebsite": "",
        "releaseDate": "",
        "pros": "",
        "cons": "",
    }
    return record


def export_records_to_excel(records: List[Dict[str, Any]], output_path: str):
    """Export records to a styled Excel (.xlsx) spreadsheet and CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "AI Tools & Agents"

    # Styling definitions
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    border_thin = Side(border_style="thin", color="D1D5DB")
    cell_border = Border(top=border_thin, left=border_thin, right=border_thin, bottom=border_thin)

    row_font = Font(name="Calibri", size=10)
    top_left_align = Alignment(vertical="top", wrap_text=True)

    # 1. Write headers
    headers = [col[1] for col in COLUMNS]
    ws.append(headers)
    ws.row_dimensions[1].height = 28

    for col_idx, (key, title, width) in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = cell_border
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    # 2. Write data rows
    for row_idx, r in enumerate(records, 2):
        row_values = []
        for key, title, width in COLUMNS:
            val = r.get(key, "")
            if isinstance(val, bool):
                row_values.append("TRUE" if val else "FALSE")
            elif isinstance(val, list):
                row_values.append("; ".join(val))
            else:
                row_values.append(str(val) if val is not None else "")
        ws.append(row_values)
        ws.row_dimensions[row_idx].height = 42

        for col_idx in range(1, len(COLUMNS) + 1):
            c = ws.cell(row=row_idx, column=col_idx)
            c.font = row_font
            c.alignment = top_left_align
            c.border = cell_border

    wb.save(output_path)
    log.info("Saved styled Excel file to: %s (%d records)", output_path, len(records))

    # Also save CSV version
    csv_path = output_path.replace(".xlsx", ".csv")
    import csv
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([col[1] for col in COLUMNS])
        for r in records:
            w.writerow([
                "TRUE" if r.get(k) is True else ("FALSE" if r.get(k) is False else r.get(k, ""))
                for k, t, w_col in COLUMNS
            ])
    log.info("Saved CSV file to: %s", csv_path)


def run_universal_scraper(
    target_url: str,
    limit: Optional[int] = None,
    max_workers: int = 25,
    output_file: str = "data/export/scraped_tools.xlsx",
    progress_callback=None,
    stop_check=None
):
    """Universal batch scraper that discovers and extracts AI tools from ANY target URL."""
    start_time = time.time()
    log.info("Initiating universal scrape for target: %s (limit=%s)", target_url, limit)

    urls = discover_urls_from_site(target_url, limit=limit)
    if not urls:
        log.warning("No URLs discovered for %s", target_url)
        urls = [target_url]

    if limit and limit < len(urls):
        urls = urls[:limit]

    parsed_domain = urllib.parse.urlparse(target_url).netloc
    log.info("Discovered %d target URLs. Starting extraction with %d worker threads...", len(urls), max_workers)

    records = []
    completed = 0

    if progress_callback:
        progress_callback({
            "type": "directory_progress",
            "total": len(urls),
            "completed": 0,
            "extracted": 0,
            "percent": 0.0,
            "last_tool": "Starting...",
            "status": "running"
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(parse_generic_page, u, parsed_domain): u for u in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            if stop_check and stop_check():
                log.warning("Scraping stopped early by user.")
                break

            completed += 1
            try:
                rec = future.result()
                if rec:
                    records.append(rec)
            except Exception as exc:
                log.warning("Parse exception: %s", exc)
                rec = None

            if progress_callback:
                progress_callback({
                    "type": "directory_progress",
                    "total": len(urls),
                    "completed": completed,
                    "extracted": len(records),
                    "percent": round((completed / len(urls)) * 100, 1),
                    "last_tool": rec.get("name") if rec else "",
                    "status": "running"
                })

            if completed % 25 == 0 or completed == len(urls):
                log.info("Progress: %d/%d (%.1f%%) — Extracted %d records",
                         completed, len(urls), (completed / len(urls)) * 100, len(records))

    log.info("Universal scrape finished in %.1f seconds. Total extracted: %d", time.time() - start_time, len(records))
    export_records_to_excel(records, output_file)

    if progress_callback:
        progress_callback({
            "type": "directory_complete",
            "total": len(urls),
            "completed": completed,
            "extracted": len(records),
            "percent": 100.0,
            "output_xlsx": os.path.basename(output_file),
            "output_csv": os.path.basename(output_file).replace(".xlsx", ".csv"),
            "status": "completed"
        })

    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal AI Tool & Directory Scraper")
    parser.add_argument("--url", type=str, required=True, help="Any website or directory URL")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of tools to scrape")
    parser.add_argument("--workers", type=int, default=25, help="Number of worker threads")
    parser.add_argument("--output", type=str, default="data/export/scraped_tools.xlsx", help="Output Excel file path")
    args = parser.parse_args()

    run_universal_scraper(target_url=args.url, limit=args.limit, max_workers=args.workers, output_file=args.output)
