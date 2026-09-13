"""Export to entities.json, relationships.json, CSV (Google Sheets), report."""
import csv
import json
import os


def _ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/export", exist_ok=True)


def export_entities(entities: list, path="data/entities.json"):
    _ensure_dirs()
    existing_by_id = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                prev = json.load(f)
                if isinstance(prev, list):
                    for item in prev:
                        if isinstance(item, dict) and "id" in item:
                            existing_by_id[item["id"]] = item
        except Exception:
            pass

    for e in entities:
        item = {
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
        }
        existing_by_id[e.id] = item

    cumulative = list(existing_by_id.values())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cumulative, f, indent=2, ensure_ascii=False)
    return cumulative


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
            is_dict = isinstance(e, dict)
            e_id = e.get("id", "") if is_dict else e.id
            name = e.get("name", "") if is_dict else e.name
            etype = e.get("entity_type", "Tool") if is_dict else e.entity_type
            desc = e.get("description", "") if is_dict else e.description
            url = e.get("url", "") if is_dict else e.url
            logo = e.get("logo_url", "") if is_dict else e.logo_url
            pricing = e.get("pricing", "") if is_dict else getattr(e, "pricing", "")
            raw_feats = e.get("features", []) if is_dict else getattr(e, "features", [])
            feats = " | ".join(raw_feats) if isinstance(raw_feats, list) else str(raw_feats)
            cats = e.get("categories", []) if is_dict else e.categories
            source = e.get("source", {}) if is_dict else e.source
            src_name = source.get("name", "") if isinstance(source, dict) else ""
            src_url = source.get("url", "") if isinstance(source, dict) else ""
            socials = e.get("social_links", {}) if is_dict else getattr(e, "social_links", {})
            gh = socials.get("github", "") if isinstance(socials, dict) else ""
            verified = e.get("verified", False) if is_dict else e.verified
            status = e.get("http_status", 0) if is_dict else e.http_status
            last_ver = e.get("last_verified", "") if is_dict else e.last_verified
            raw_aliases = e.get("aliases", []) if is_dict else e.aliases
            aliases_str = "; ".join(sorted(raw_aliases)) if isinstance(raw_aliases, (list, set)) else str(raw_aliases)

            w.writerow([
                e_id, name, etype, desc, url,
                logo, pricing, feats,
                cats[0] if cats else "",
                cats[1] if len(cats) > 1 else "",
                src_name, src_url,
                gh, "Verified" if verified else "Pending", status,
                last_ver, aliases_str,
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

