from __future__ import annotations

from collections import defaultdict
from datetime import date
import re

from .models import Job


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:70] or "newsletter"


def _ordinal_day(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


CATEGORY_DISPLAY: dict[str, tuple[str, str]] = {
    "Software Engineering": ("💻", "Software Engineering"),
    "Software Development & Core Engineering": ("💻", "Software Engineering"),
    "Software Development & Core Engineering Opportunities": ("💻", "Software Engineering"),
    "AI/ML": ("🤖", "AI/ML"),
    "Artificial Intelligence & Machine Learning": ("🤖", "AI/ML"),
    "Artificial Intelligence & Machine Learning Opportunities": ("🤖", "AI/ML"),
    "Cybersecurity": ("🛡️", "Cybersecurity"),
    "Cybersecurity & Infrastructure": ("🛡️", "Cybersecurity"),
    "Cybersecurity Opportunities": ("🛡️", "Cybersecurity"),
    "Data Analytics": ("📊", "Data Analytics"),
    "Data Analytics, Research & Intelligence": ("📊", "Data Analytics"),
    "Data Analytics, Research & Intelligence Roles": ("📊", "Data Analytics"),
    "Product Design & Media": ("🎨", "Product Design & Media"),
    "Product Design, Media & Content Strategy": ("🎨", "Product Design & Media"),
    "Product Design, Media & Content Strategy Roles": ("🎨", "Product Design & Media"),
    "Business Ops & HR": ("💼", "Business Ops & HR"),
    "Business Operations, HR, Marketing & Strategy": ("💼", "Business Ops & HR"),
    "Business Operations, HR, Marketing & Strategy Roles": ("💼", "Business Ops & HR"),
    "Other Early-Career": ("🚀", "Other Early-Career"),
    "Other Early-Career Opportunities": ("🚀", "Other Early-Career"),
}


def format_work_mode(mode: str) -> str:
    m = (mode or "").lower()
    if "remote" in m:
        return "🌐 Remote"
    if "hybrid" in m:
        return "⚡ Hybrid"
    return "🏢 In-Office"


def render_newsletter(jobs: list[Job], brand: str = "InternAtlas", publication_date: date | None = None) -> str:
    publication_date = publication_date or date.today()
    grouped: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        grouped[job.category].append(job)
    lead_companies: list[str] = []
    for job in jobs:
        if job.company not in lead_companies:
            lead_companies.append(job.company)
        if len(lead_companies) == 8:
            break

    day_str = f"{_ordinal_day(publication_date.day)} {publication_date.strftime('%B %Y')}"
    count_str = f"{len(jobs)}"

    lead_text = ""
    if lead_companies:
        sample_cos = (
            f"{', '.join(lead_companies[:3])} and {lead_companies[3]}"
            if len(lead_companies) >= 4
            else ", ".join(lead_companies)
        )
        lead_text = f"From {sample_cos} - explore opportunities across tech, AI, product, design, and more, with direct links to company career pages."

    lines = [
        f"# 🔴 {brand} — {count_str} Verified Internships at Top Companies — {publication_date.strftime('%d %B %Y')}",
        "",
    ]
    if lead_text:
        lines.extend([
            f"### {lead_text}",
            "",
        ])

    lines.extend([
        "Hi everyone,",
        "",
        f"Welcome to today's curated edition of {count_str} verified early career & internship opportunities across Tier-1 tech MNCs, high-growth startups, and core engineering leaders in India.",
        "",
        "Every role is verified directly on official company career portals with zero broker sites and zero fees. Do like and restack this post to support our initiative and help your peers!",
        "",
        "📲 Want daily opportunity alerts directly on your phone? Join our community on WhatsApp.",
        "",
        "---",
        "",
    ])

    for category, category_jobs in grouped.items():
        emoji, label = CATEGORY_DISPLAY.get(category, ("🚀", category))
        lines.extend([
            f"## {emoji} {label} ({len(category_jobs)})",
            "",
        ])
        for index, job in enumerate(category_jobs, 1):
            title = job.title.replace("[", "\\[").replace("]", "\\]").strip()
            company = job.company.strip() or "Employer not specified"
            location = job.location.strip() or "Location not specified"
            mode_badge = format_work_mode(job.work_mode)
            lines.append(f"{index}. **{company}** — {title} 📍 {location} · {mode_badge} · **[Apply Direct ↗︎]({job.url})**")
            if job.verification_status != "verified_link":
                lines.append(f"   - **Review note:** {job.verification_note}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "*Every role is verified directly on official company career portals with zero broker sites and zero fees. Reachability does not guarantee that a role remains open. Happy applying and all the best!*",
        "",
    ])
    return "\n".join(lines)


def _add_hyperlink(paragraph, text: str, url: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE

    part = paragraph.part
    r_id = part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    c = OxmlElement("w:color")
    c.set(qn("w:val"), "1155CC")
    rPr.append(c)

    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)

    b = OxmlElement("w:b")
    rPr.append(b)

    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def render_newsletter_docx(
    jobs: list[Job],
    output_path: str | Path,
    brand: str = "InternAtlas",
    publication_date: date | None = None,
) -> Path:
    from pathlib import Path
    from docx import Document
    from docx.shared import Pt, RGBColor

    publication_date = publication_date or date.today()
    grouped: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        grouped[job.category].append(job)

    lead_companies: list[str] = []
    for job in jobs:
        if job.company not in lead_companies:
            lead_companies.append(job.company)
        if len(lead_companies) == 8:
            break

    day_str = f"{_ordinal_day(publication_date.day)} {publication_date.strftime('%B %Y')}"
    count_str = f"{len(jobs)}"

    lead_text = ""
    if lead_companies:
        sample_cos = (
            f"{', '.join(lead_companies[:3])} and {lead_companies[3]}"
            if len(lead_companies) >= 4
            else ", ".join(lead_companies)
        )
        lead_text = f"From {sample_cos} - explore opportunities across tech, AI, product, design, and more, with direct links to company career pages."

    doc = Document()
    doc.add_heading(
        f"🔴 {brand} — {count_str} Verified Internships at Top Companies — {publication_date.strftime('%d %B %Y')}",
        level=1,
    )
    if lead_text:
        sub = doc.add_paragraph(lead_text)
        if sub.runs:
            sub.runs[0].italic = True

    doc.add_paragraph("Hi everyone,")
    doc.add_paragraph(
        f"Welcome to today's curated edition of {count_str} verified early career & internship opportunities across Tier-1 tech MNCs, high-growth startups, and core engineering leaders in India."
    )
    doc.add_paragraph(
        "Every role is verified directly on official company career portals with zero broker sites and zero fees. Do like and restack this post to support our initiative and help your peers!"
    )
    doc.add_paragraph(
        "📲 Want daily opportunity alerts directly on your phone? Join our community on WhatsApp."
    )

    for category, category_jobs in grouped.items():
        emoji, label = CATEGORY_DISPLAY.get(category, ("🚀", category))
        doc.add_heading(f"{emoji} {label} ({len(category_jobs)})", level=2)
        for index, job in enumerate(category_jobs, 1):
            title = job.title.strip()
            company = job.company.strip() or "Employer not specified"
            location = job.location.strip() or "Location not specified"
            mode_badge = format_work_mode(job.work_mode)
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            p.add_run(f"{index}. ")
            r_comp = p.add_run(company)
            r_comp.bold = True
            p.add_run(f" — {title} 📍 {location} · {mode_badge} · ")
            _add_hyperlink(p, "Apply Direct ↗︎", job.url)

    disclaimer = doc.add_paragraph()
    run = disclaimer.add_run(
        "Every role is verified directly on official company career portals with zero broker sites and zero fees. Reachability does not guarantee that a role remains open. Happy applying and all the best!"
    )
    run.italic = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor(100, 116, 139)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return out
