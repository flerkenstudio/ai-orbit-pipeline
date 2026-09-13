"""Export to entities.json, relationships.json, CSV (Google Sheets), report."""
import csv
import json
import os


def _ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/export", exist_ok=True)


def export_entities(entities: list, path="data/entities.json"):
    _ensure_dirs()
    out = []
    for e in entities:
        out.append({
            "id": e.id, "entity_type": e.entity_type, "name": e.name,
            "description": e.description, "url": e.url,
            "logo_url": e.logo_url, "categories": e.categories,
            "aliases": sorted(e.aliases), "source": e.source,
            "verified": e.verified, "http_status": e.http_status,
            "last_verified": e.last_verified,
            "pricing": getattr(e, "pricing", ""),
            "features": getattr(e, "features", []),
            "social_links": getattr(e, "social_links", {}),
            "open_source": getattr(e, "open_source", False),
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return path


def export_relationships(rels: list, path="data/relationships.json"):
    _ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rels, f, indent=2, ensure_ascii=False)
    return path


def export_sheets_csv(entities: list, path="data/export/tools_sheet.csv"):
    _ensure_dirs()
    cols = ["ID", "Name", "Entity Type", "Description", "Official Website",
            "Official Logo", "Pricing", "Features", "Category", "Subcategory",
            "Source", "Source URL", "GitHub Repo", "Verification Status",
            "HTTP Status", "Last Verified", "Aliases"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for e in entities:
            cats = e.categories
            feats = " | ".join(getattr(e, "features", []))
            socials = getattr(e, "social_links", {})
            gh = socials.get("github", "")
            w.writerow([
                e.id, e.name, e.entity_type, e.description, e.url,
                e.logo_url, getattr(e, "pricing", ""), feats,
                cats[0] if cats else "",
                cats[1] if len(cats) > 1 else "",
                e.source.get("name", ""), e.source.get("url", ""),
                gh, "Verified" if e.verified else "Pending", e.http_status,
                e.last_verified, "; ".join(sorted(e.aliases)),
            ])
    return path


def export_report(report: dict, path="data/validation_report.json"):
    _ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return path


def export_to_google_sheets_api(entities: list):
    import gspread
    from dotenv import load_dotenv
    load_dotenv()

    creds_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS', 'google-credentials.json')
    sheet_id = os.getenv('GOOGLE_SHEETS_ID')

    if not sheet_id:
        print('No GOOGLE_SHEETS_ID found, skipping live sheets export.')
        return

    try:
        gc = gspread.service_account(filename=creds_file)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1

        cols = ['ID', 'Name', 'Entity Type', 'Description', 'Official Website',
                'Official Logo', 'Pricing', 'Features', 'Category', 'Subcategory',
                'Source', 'Source URL', 'GitHub Repo', 'Verification Status',
                'HTTP Status', 'Last Verified', 'Aliases']
        rows = [cols]
        for e in entities:
            cats = e.categories
            feats = ' | '.join(getattr(e, 'features', []))
            socials = getattr(e, 'social_links', {})
            gh = socials.get('github', '')
            rows.append([
                e.id, e.name, e.entity_type, e.description, e.url,
                e.logo_url, getattr(e, 'pricing', ''), feats,
                cats[0] if cats else '',
                cats[1] if len(cats) > 1 else '',
                e.source.get('name', ''), e.source.get('url', ''),
                gh, 'Verified' if e.verified else 'Pending', e.http_status,
                e.last_verified, '; '.join(sorted(e.aliases)),
            ])

        worksheet.clear()
        worksheet.update(rows)
        print(f'Successfully updated Google Sheet with {len(rows)-1} entities.')
    except Exception as e:
        print(f'Failed to export to Google Sheets: {e}')

