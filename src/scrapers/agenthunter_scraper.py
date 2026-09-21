"""AgentHunter.io Specialized Scraper
Extracts structured AI Agent records matching the AIOrbit Agent Data Requirements schema.
Exports to Excel (.xlsx) and CSV.
"""
import argparse
import concurrent.futures
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from typing import Dict, List, Any, Optional

import requests
from bs4 import BeautifulSoup
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("agenthunter")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
        clean_q = {k: v for k, v in q.items() if not k.lower().startswith(("utm_", "ref", "source"))}
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


def get_all_agent_urls(base_url: str = "https://www.agenthunter.io/", max_needed: Optional[int] = None) -> List[str]:
    """Fetch agent/tool detail URLs from sitemaps, supporting recursive sitemap indexes up to 50k+ URLs."""
    if not base_url or "example.com" in base_url.lower():
        base_url = "https://www.agenthunter.io/"

    parsed_base = urllib.parse.urlparse(base_url)
    root_domain = f"{parsed_base.scheme or 'https'}://{parsed_base.netloc}"

    candidate_sitemaps = [
        f"{root_domain}/sitemap.xml",
        f"{root_domain}/sitemap_index.xml",
        f"{root_domain}/sitemaps.xml",
    ]

    all_urls = []
    visited_sitemaps = set()

    for sitemap_url in candidate_sitemaps:
        if sitemap_url in visited_sitemaps:
            continue
        try:
            log.info("Inspecting sitemap: %s", sitemap_url)
            r = requests.get(sitemap_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            visited_sitemaps.add(sitemap_url)

            # Check if this is a sitemap index with child sitemaps
            child_sitemaps = re.findall(r"<loc>(https?://[^<]+sitemap[^<]*\.xml)</loc>", r.text, re.I)
            if child_sitemaps:
                log.info("Found sitemap index with %d sub-sitemaps.", len(child_sitemaps))
                for child in child_sitemaps:
                    if max_needed and len(all_urls) >= max_needed:
                        break
                    if child in visited_sitemaps:
                        continue
                    visited_sitemaps.add(child)
                    try:
                        cr = requests.get(child, headers=HEADERS, timeout=15)
                        if cr.status_code == 200:
                            locs = re.findall(r"<loc>(https?://[^<]+)</loc>", cr.text)
                            filtered = [u for u in locs if not u.endswith(".xml")]
                            all_urls.extend(filtered)
                    except Exception:
                        pass
            else:
                locs = re.findall(r"<loc>(https?://[^<]+)</loc>", r.text)
                filtered = [u for u in locs if not u.endswith(".xml")]
                all_urls.extend(filtered)

            if all_urls:
                break
        except Exception as exc:
            log.warning("Sitemap fetch warning for %s: %s", sitemap_url, exc)

    # For agenthunter specifically or agent paths: filter to agent URLs if present
    agent_specific = [u for u in all_urls if "/agent/" in u or "/tool/" in u or "/ai/" in u]
    final_urls = agent_specific if agent_specific else all_urls

    unique_urls = sorted(list(set(final_urls)))
    log.info("Discovered %d unique tool/agent URLs.", len(unique_urls))
    return unique_urls



def parse_agent_page(url: str) -> Optional[Dict[str, Any]]:
    """Fetch and extract structured agent data conforming to the AIOrbit requirements."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            log.warning("HTTP %d for %s", r.status_code, url)
            return None
    except Exception as exc:
        log.warning("Request error for %s: %s", url, exc)
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    slug = url.rstrip("/").split("/")[-1]

    # 1. JSON-LD SoftwareApplication schema extraction
    ld_data = {}
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
            if data.get("@type") == "SoftwareApplication":
                ld_data = data
                break
        except Exception:
            continue

    name = ld_data.get("name") or slug.replace("-", " ").title()
    tagline = ld_data.get("description") or ""
    category = ld_data.get("applicationCategory") or "AI Agent"
    logo_url = ld_data.get("image") or ""

    # 2. Extract links (Official website, GitHub, API docs)
    website_url = ""
    github_url = ""
    api_docs_url = ""

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        link_text = a.get_text(" ", strip=True).lower()
        if not href.startswith("http"):
            continue

        if "github.com" in href.lower():
            if not github_url or len(href) < len(github_url):
                github_url = clean_tracking_url(href)
        elif any(w in link_text for w in ["visit website", "official website", "website", "get started", "launch"]):
            if "agenthunter.io" not in href and "reddit.com" not in href:
                website_url = clean_tracking_url(href)
        elif any(w in link_text for w in ["api doc", "documentation", "docs"]):
            api_docs_url = clean_tracking_url(href)

    # Fallback for websiteUrl if not found in button text
    if not website_url:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("http") and "agenthunter.io" not in href and not any(d in href for d in ["reddit.com", "twitter.com", "x.com", "github.com"]):
                website_url = clean_tracking_url(href)
                break

    # 3. Parse Sections: Agent Details, Key Features, Use Cases
    sections: Dict[str, List[str]] = {}
    for h2 in soup.find_all(["h2", "h3"]):
        sec_title = h2.get_text(strip=True)
        items = []
        parent = h2.find_parent()
        if parent:
            # Bullet points
            for li in parent.find_all("li"):
                txt = li.get_text(" ", strip=True)
                if txt and txt not in items and txt != sec_title:
                    items.append(txt)
            # Paragraphs if no bullets
            if not items:
                for p in parent.find_all("p"):
                    txt = p.get_text(" ", strip=True)
                    if txt and txt not in items and txt != sec_title:
                        items.append(txt)
        sections[sec_title] = items

    # Long Description (About)
    details_items = sections.get("Agent Details", [])
    if details_items:
        long_description = " ".join(details_items)
    else:
        # Fallback to general meta description
        meta_desc = soup.find("meta", {"name": "description"})
        long_description = meta_desc.get("content", "") if meta_desc else tagline

    # Clean long description
    long_description = re.sub(r"\s+", " ", long_description).strip()

    # Short Description (Max 7-8 words, suitable for card)
    words = tagline.split()
    if words and len(words) <= 10:
        short_description = tagline
    elif words:
        short_description = " ".join(words[:8])
    else:
        short_description = f"AI agent for {category.lower()}"

    # Features
    features_list = sections.get("Key Features", [])
    # Filter out navigation items
    features_list = [f for f in features_list if len(f) > 5 and not f.startswith("The Agent Company")]

    # Use cases
    use_cases_list = sections.get("Use Cases", [])

    # Compatibility / platforms
    compatibility_list = []
    text_corpus = f"{tagline} {long_description}".lower()
    for platform in ["Web Browser", "Mac", "Windows", "Linux", "iOS", "Android", "Slack", "Discord", "Chrome Extension", "Docker"]:
        if platform.lower() in text_corpus:
            compatibility_list.append(platform)
    if not compatibility_list:
        compatibility_list.append("Web Browser")

    # Integrations
    integrations_list = []
    for app_name in ["Slack", "Discord", "GitHub", "Notion", "Google Workspace", "Zapier", "Jira", "Telegram", "Linear"]:
        if app_name.lower() in text_corpus:
            integrations_list.append(app_name)

    # Primary tasks
    primary_tasks = [category]
    if "code" in text_corpus or "developer" in text_corpus:
        primary_tasks.append("Code Generation")
    if "automation" in text_corpus or "workflow" in text_corpus:
        primary_tasks.append("Task Automation")
    if "chat" in text_corpus or "support" in text_corpus:
        primary_tasks.append("Customer Support")

    # Pricing Model determination
    offers = ld_data.get("offers", {})
    price_spec = offers.get("priceSpecification", {}) if isinstance(offers, dict) else {}
    raw_price = str(price_spec.get("price") or offers.get("price") or "").lower()

    if "free trial" in text_corpus:
        pricing_model = "FREE_TRIAL"
    elif "open source" in text_corpus or github_url:
        pricing_model = "FREE" if "free" in raw_price else "FREEMIUM"
    elif "free" in raw_price or "free" in text_corpus:
        pricing_model = "FREE"
    elif any(term in text_corpus for term in ["$", "paid", "subscription", "pricing"]):
        pricing_model = "PAID"
    elif "freemium" in text_corpus:
        pricing_model = "FREEMIUM"
    else:
        pricing_model = "FREEMIUM"

    pricing_raw = raw_price if raw_price and raw_price != "varies" else ("Free plan available" if pricing_model in ("FREE", "FREEMIUM") else "Contact for pricing")

    # Open Source & API flags
    is_open_source = bool(github_url) or "open source" in text_corpus or "open-source" in text_corpus
    has_api = bool(api_docs_url) or any(k in text_corpus for k in ["rest api", "api access", "api integration", "api key"])

    record = {
        "name": name,
        "slug": slug,
        "shortDescription": short_description,
        "description": tagline or short_description,
        "longDescription": long_description,
        "websiteUrl": website_url or url,
        "logoUrl": logo_url,
        "category": category,
        "categorySlug": slugify(category),
        "primaryTask": "; ".join(dict.fromkeys(primary_tasks)),
        "features": "\n• " + "\n• ".join(features_list) if features_list else "",
        "useCases": "\n• " + "\n• ".join(use_cases_list) if use_cases_list else "",
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


def export_to_excel(records: List[Dict[str, Any]], output_path: str = "data/export/agenthunter_agents.xlsx"):
    """Export records to a professionally styled Excel spreadsheet (.xlsx)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "AI Agents"

    # Header styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Deep blue
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

    # Also save CSV version for versatility
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


def run_scraper(base_url: str = "https://www.agenthunter.io/", limit: Optional[int] = None, max_workers: int = 25, output_file: str = "data/export/agenthunter_agents.xlsx", progress_callback=None, stop_check=None):
    start_time = time.time()
    urls = get_all_agent_urls(base_url=base_url, max_needed=limit)
    if limit:
        urls = urls[:limit]
        log.info("Limiting scrape to %d agents (from %d available).", len(urls), len(urls))

    if limit and limit >= 5000:
        max_workers = min(max(max_workers, 30), 40)
    log.info("Starting concurrent scraping with %d worker threads on %d URLs...", max_workers, len(urls))
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
        future_to_url = {executor.submit(parse_agent_page, u): u for u in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            if stop_check and stop_check():
                log.warning("Scraping stopped early by user.")
                break

            completed += 1
            rec = future.result()
            if rec:
                records.append(rec)

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
                log.info("Progress: %d/%d (%.1f%%) — Extracted %d agents",
                         completed, len(urls), (completed / len(urls)) * 100, len(records))

    log.info("Scraping finished in %.1f seconds. Total extracted: %d", time.time() - start_time, len(records))
    export_to_excel(records, output_file)

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
    parser = argparse.ArgumentParser(description="Scrape AgentHunter.io into styled Excel sheet")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of agents to scrape (e.g. 50, 100)")
    parser.add_argument("--workers", type=int, default=15, help="Number of concurrent worker threads (default: 15)")
    parser.add_argument("--output", type=str, default="data/export/agenthunter_agents.xlsx", help="Output Excel file path")
    args = parser.parse_args()

    run_scraper(limit=args.limit, max_workers=args.workers, output_file=args.output)
