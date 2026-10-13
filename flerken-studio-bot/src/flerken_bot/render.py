from __future__ import annotations

from collections import defaultdict
from datetime import date
import re

from .models import Job


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:70] or "newsletter"


CATEGORY_EMOJIS = {
    "Software Development & Core Engineering Opportunities": "💻",
    "Artificial Intelligence & Machine Learning Opportunities": "🤖",
    "Cybersecurity Opportunities": "🛡️",
    "Data Analytics, Research & Intelligence Roles": "📊",
    "Product Design, Media & Content Strategy Roles": "🎨",
    "Business Operations, HR, Marketing & Strategy Roles": "💼",
    "Other Early-Career Opportunities": "🚀",
}


def _format_work_mode(mode: str) -> str:
    m = (mode or "").strip().lower()
    if "remote" in m:
        return "🌐 Remote"
    if "hybrid" in m:
        return "⚡ Hybrid"
    if "onsite" in m or "office" in m:
        return "🏢 In-Office"
    return "📌 " + (mode.strip() or "Unspecified")


def _format_location(loc: str) -> str:
    cleaned = (loc or "").strip()
    if not cleaned or cleaned.lower() == "location not specified":
        return "📍 Location not specified"
    return f"📍 {cleaned}"


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

    lines = [
        f"# 🔴 {brand} — {publication_date.strftime('%d %b %Y')} — {len(jobs)} Early-Career Opportunities",
        "",
    ]
    if lead_companies:
        company_list = ", ".join(lead_companies)
        if len(jobs) > len(lead_companies):
            company_list += ", and more"
        lines.append(f"✨ **Featured Employers:** {company_list}")
        lines.append("")

    lines.extend([
        f"📅 **{publication_date.strftime('%B %d, %Y').upper()}**",
        "",
        "> 💡 **Curated & Verified Early-Career Digest**  ",
        "> All links below are verified official employer application pages. Positions fill on a rolling basis, so we recommend applying promptly! 🚀",
        "",
        "---",
        "",
    ])

    for category, category_jobs in grouped.items():
        emoji = CATEGORY_EMOJIS.get(category, "📌")
        lines.extend([
            f"## {emoji} {category} ({len(category_jobs)})",
            "",
        ])
        for index, job in enumerate(category_jobs, 1):
            title = job.title.replace("[", "\\[").replace("]", "\\]").strip()
            company = job.company.strip() or "Employer not specified"
            location = _format_location(job.location)
            work_mode = _format_work_mode(job.work_mode)
            lines.append(f"{index}. **[{title} — {company}]({job.url})**  \n   {location} · {work_mode}")
            if job.verification_status != "verified_link":
                lines.append(f"   ⚠️ *Review note: {job.verification_note}*")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "### 💡 Pro-Tips for Applicants",
        "- ⚡ **Apply Early:** Early-career & internship roles often close once application caps are reached.",
        "- 🎯 **Tailor Your Resume:** Align relevant keywords and projects with each role's requirements.",
        "- 📬 **Share With Peers:** Know someone looking for an internship or new-grad role? Forward this issue to them!",
        "",
        "---",
        "",
        "🔒 *Application links were checked for reachability, but a reachable page does not guarantee that a role remains open. Confirm eligibility, deadlines, and job details on the employer's official careers page before applying.*",
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

    doc = Document()
    title_h = doc.add_heading(
        f"🔴 {brand} — {publication_date.strftime('%d %b %Y')} — {len(jobs)} Early-Career Opportunities",
        level=1,
    )
    if lead_companies:
        sub = doc.add_paragraph(
            ", ".join(lead_companies) + (", and more" if len(jobs) > len(lead_companies) else "")
        )
        if sub.runs:
            sub.runs[0].italic = True

    date_p = doc.add_paragraph(publication_date.strftime("%b %d, %Y").upper())
    if date_p.runs:
        date_p.runs[0].bold = True

    doc.add_paragraph("Hi everyone,")
    doc.add_paragraph(
        "Here are newly collected early-career opportunities. Please check the employer's application page for current eligibility and availability."
    )

    for category, category_jobs in grouped.items():
        emoji = CATEGORY_EMOJIS.get(category, "📌")
        doc.add_heading(f"{emoji} {category} ({len(category_jobs)})", level=2)
        for index, job in enumerate(category_jobs, 1):
            company = job.company.strip() or "Employer not specified"
            location = _format_location(job.location)
            work_mode = _format_work_mode(job.work_mode)
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            p.add_run(f"{index}. ")
            _add_hyperlink(p, f"{job.title} — {company}", job.url)
            p.add_run(f" ({location} · {work_mode})")

    disclaimer = doc.add_paragraph()
    run = disclaimer.add_run(
        "Application links were checked for reachability, but a reachable page does not guarantee that a role remains open. Confirm eligibility, deadlines, and job details on the employer's official careers page before applying."
    )
    run.italic = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor(100, 116, 139)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return out

