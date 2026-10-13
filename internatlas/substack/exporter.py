"""Word (.docx), Substack Markdown/Rich-HTML, and Excel (.xlsx) Exporters for InternAtlas Substack."""
from datetime import datetime
from pathlib import Path
import pandas as pd
import docx
from docx.shared import Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE

from .config import EXPORT_DIR, SECTIONS_ORDER


def _ordinal_day(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _add_hyperlink(paragraph, url: str, text: str):
    """Adds a native clickable hyperlink to a python-docx paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    # Blue color (#1155CC) and single underline
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "1155CC")
    rPr.append(c)

    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)

    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "22")  # 11pt
    rPr.append(sz)

    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)

    paragraph._p.append(hyperlink)
    return hyperlink


def build_substack_metadata(jobs: list) -> dict:
    now = datetime.now()
    day_str = f"{_ordinal_day(now.day)} {now.strftime('%b')}"
    date_upper = now.strftime("%b %d, %Y").upper()
    rounded_count = max(10, (len(jobs) // 10) * 10)

    # Top companies for subtitle
    top_companies = []
    for j in jobs:
        c = (j.get("company") or "").strip()
        # Clean parenthetical short names for subtitle readability
        c_short = c.split("(")[0].strip()
        if c_short and c_short not in top_companies:
            top_companies.append(c_short)
        if len(top_companies) >= 7:
            break

    subtitle = (
        f"{', '.join(top_companies)} and many more"
        if top_companies
        else "Top Tech, Fortune 500 & High-Growth Startups"
    )

    title = f"🔴 InternAtlas (🎓 💼) - {day_str} - {rounded_count}+ Hottest Early Career & Internship Roles - Do Not Miss"

    grouped = {sec: [] for sec in SECTIONS_ORDER}
    for j in jobs:
        sec = j.get("section")
        if sec not in grouped:
            sec = SECTIONS_ORDER[1]
        grouped[sec].append(j)

    return {
        "title": title,
        "subtitle": subtitle,
        "date_str": date_upper,
        "total_jobs": len(jobs),
        "rounded_count": rounded_count,
        "sections": grouped,
    }


def generate_substack_markdown(jobs: list) -> str:
    """Generates exact Substack Markdown matching the user's newsletter template."""
    meta = build_substack_metadata(jobs)
    lines = [
        f"# **{meta['title']}**",
        "",
        meta["subtitle"],
        "",
        meta["date_str"],
        "",
        "---",
        "",
        "Hi Guys,",
        "",
        "Do like and restack this post to support our initiative.",
        "",
        "📲 If you want daily new opportunity alerts directly on your phone, join our community on WhatsApp/Telegram!",
        "",
        "---",
        "",
    ]

SECTION_EMOJIS = {
    "Software Development & Core Engineering Opportunities": "💻",
    "Artificial Intelligence & Machine Learning Opportunities": "🤖",
    "Cybersecurity Opportunities": "🛡️",
    "Data Analytics, Research & Intelligence Roles": "📊",
    "Product Design, Media & Content Strategy Roles": "🎨",
    "Business Operations, HR, Marketing & Strategy Roles": "💼",
}


def _format_mode_badge(mode: str) -> str:
    m = (mode or "").strip().lower()
    if "remote" in m:
        return "🌐 Remote"
    if "hybrid" in m:
        return "⚡ Hybrid"
    if "onsite" in m or "office" in m:
        return "🏢 In-Office"
    return "📌 " + (mode.strip() or "Unspecified")


def generate_substack_markdown(jobs: list) -> str:
    """Generates exact Substack Markdown matching the user's newsletter template."""
    meta = build_substack_metadata(jobs)
    lines = [
        f"# **{meta['title']}**",
        "",
        f"✨ **Featured Employers:** {meta['subtitle']}",
        "",
        f"📅 **{meta['date_str']}**",
        "",
        "> 💡 **Curated & Verified Early-Career Digest**  ",
        "> All links below are direct official career portals. Positions fill on a rolling basis, so apply early! 🚀",
        "",
        "---",
        "",
        "Hi Guys,",
        "",
        "Do like and restack this post to support our initiative! ❤️",
        "",
        "📲 If you want daily new opportunity alerts directly on your phone, join our community on WhatsApp/Telegram!",
        "",
        "---",
        "",
    ]

    for sec_title in SECTIONS_ORDER:
        sec_jobs = meta["sections"].get(sec_title, [])
        if not sec_jobs:
            continue
        emoji = SECTION_EMOJIS.get(sec_title, "📌")
        lines.append(f"## **{emoji} {sec_title} ({len(sec_jobs)})**")
        lines.append("")
        for idx, j in enumerate(sec_jobs, 1):
            comp = j.get("company", "").strip()
            role = j.get("role_title", "").strip()
            url = j.get("apply_url", "").strip()
            loc = j.get("location", "India").strip()
            mode = _format_mode_badge(j.get("work_mode", "In-Office"))
            lines.append(f"{idx}. **[{comp} hiring - {role}]({url})**  \n   📍 {loc} · {mode}")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "### 💡 Pro-Tips for Applicants",
        "- ⚡ **Apply Early:** Early-career openings often close once candidate caps are reached.",
        "- 🎯 **Tailor Your Resume:** Align relevant skills and projects with each role's description.",
        "- 📬 **Share With Friends:** Forward this edition to a classmate or friend looking for internships!",
        "",
        "---",
        "",
        "🔒 *All links in this edition are 100% verified direct official career portals. Happy applying and all the best!*",
    ])
    return "\n".join(lines)


def export_substack_docx(jobs: list, export_dir=None) -> Path:
    """Exports the formatted Word (.docx) document with clickable links ready for Substack."""
    export_dir = Path(export_dir or EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)
    meta = build_substack_metadata(jobs)

    doc = docx.Document()

    # Configure default font
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # 1. Title Heading
    h1 = doc.add_heading(level=1)
    run_h1 = h1.add_run(meta["title"])
    run_h1.bold = True
    run_h1.font.size = Pt(18)
    run_h1.font.color.rgb = RGBColor(17, 24, 39)

    # 2. Subtitle & Date
    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(meta["subtitle"])
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(75, 85, 99)

    p_date = doc.add_paragraph()
    r_date = p_date.add_run(meta["date_str"])
    r_date.bold = True
    r_date.font.size = Pt(10)
    r_date.font.color.rgb = RGBColor(107, 114, 128)

    # Divider & Intro
    doc.add_paragraph("─" * 55)
    doc.add_paragraph("Hi Guys,")
    doc.add_paragraph("Do like and restack this post to support our initiative.")
    doc.add_paragraph(
        "📲 If you want daily new opportunity alerts directly on your phone, join our community on WhatsApp/Telegram!"
    )
    doc.add_paragraph("─" * 55)

    # 3. Categorized Sections with Numbered Hyperlinks
    for sec_title in SECTIONS_ORDER:
        sec_jobs = meta["sections"].get(sec_title, [])
        if not sec_jobs:
            continue

        h2 = doc.add_heading(level=2)
        run_h2 = h2.add_run(sec_title)
        run_h2.bold = True
        run_h2.font.size = Pt(14)
        run_h2.font.color.rgb = RGBColor(30, 41, 59)

        for idx, j in enumerate(sec_jobs, 1):
            comp = j.get("company", "").strip()
            role = j.get("role_title", "").strip()
            url = j.get("apply_url", "").strip()
            loc = j.get("location", "India").strip()
            mode = j.get("work_mode", "In-Office").strip()

            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            r_num = p.add_run(f"{idx}. ")
            r_num.font.size = Pt(11)

            link_text = f"{comp} hiring - {role}"
            _add_hyperlink(p, url, link_text)

            r_loc = p.add_run(f" ({loc} · {mode})")
            r_loc.font.size = Pt(11)
            r_loc.font.color.rgb = RGBColor(55, 65, 81)

    doc.add_paragraph("─" * 55)
    p_foot = doc.add_paragraph()
    r_foot = p_foot.add_run(
        "All links in this edition are 100% verified direct official career portals. Happy applying and all the best!"
    )
    r_foot.italic = True
    r_foot.font.size = Pt(10.5)

    # Keep only the latest 3 exports to avoid clutter
    existing_docx = sorted(export_dir.glob("InternAtlas_Substack_*.docx"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_f in existing_docx[2:]:
        try:
            old_f.unlink()
        except Exception:
            pass

    fname = export_dir / f"InternAtlas_Substack_{datetime.now():%Y%m%d_%H%M%S}.docx"
    doc.save(fname)
    return fname


def export_substack_xlsx(jobs: list, export_dir=None) -> Path:
    """Exports the structured Excel (.xlsx) workbook of all Substack roles."""
    export_dir = Path(export_dir or EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    cols = [
        "section", "company", "role_title", "location", "work_mode",
        "apply_url", "ats_source", "priority_score", "last_verified"
    ]
    df = pd.DataFrame(jobs)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    existing_xlsx = sorted(export_dir.glob("InternAtlas_Substack_*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_f in existing_xlsx[2:]:
        try:
            old_f.unlink()
        except Exception:
            pass

    fname = export_dir / f"InternAtlas_Substack_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    df.to_excel(fname, index=False, sheet_name="Substack Roles")
    return fname
