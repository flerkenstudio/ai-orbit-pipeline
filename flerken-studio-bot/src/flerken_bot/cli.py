from __future__ import annotations

import argparse
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
import sys

import yaml
import requests

from .quality import SeenStore, categorize, deduplicate, is_early_career, is_target_job, verify_job, verify_jobs_concurrent
from .render import render_newsletter, render_newsletter_docx, slugify
from .sources import collect_sources

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("flerken_bot")


def load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def run(
    config_path: str,
    output_dir: str,
    state_db: str,
    dry_run: bool = False,
    ignore_seen: bool = False,
    max_jobs_override: int | None = None,
    early_career_only: bool | None = None,
) -> Path | None:
    import json

    config = load_config(config_path)
    collection = config.get("collection", {})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    jobs = deduplicate(collect_sources(config))
    if not jobs:
        LOG.warning("No listings collected. Configure enabled sources in %s", config_path)
        return None

    include_india = bool(collection.get("include_india", True))
    include_remote = bool(collection.get("include_remote_global", True))
    use_early_filter = early_career_only if early_career_only is not None else bool(collection.get("early_career_only", True))

    candidates = [job for job in jobs if is_target_job(job, include_india, include_remote)]
    if use_early_filter:
        early_candidates = [job for job in candidates if is_early_career(job)]
        if early_candidates:
            candidates = early_candidates

    for job in candidates:
        job.category = categorize(job)

    max_jobs = int(max_jobs_override or collection.get("max_jobs_per_issue", 60))
    store = SeenStore(state_db)

    # Check additional candidates beyond max_jobs in case some fail HTTP verification
    pool_to_verify = candidates if ignore_seen else store.only_new(candidates)
    pool_to_verify = pool_to_verify[: max(max_jobs * 2, 100)]

    session = requests.Session()
    session.headers.update({"User-Agent": collection.get("user_agent", "FlerkenStudioBot/0.1")})
    checked = verify_jobs_concurrent(
        pool_to_verify,
        session,
        timeout=int(collection.get("request_timeout_seconds", 15)),
        require_official=bool(collection.get("require_official_application_url", True)),
        max_workers=16,
    )

    # Only verified official links enter the article by default. Uncertain links are
    # saved to a review report rather than presented as confirmed opportunities.
    eligible = [job for job in checked if job.verification_status == "verified_link" and job.official_url]
    review = [job for job in checked if job not in eligible]
    fresh = eligible[:max_jobs]

    review_path = output / "review_queue.json"
    review_path.write_text(json.dumps([j.to_dict() for j in review], ensure_ascii=False, indent=2), encoding="utf-8")

    verified_path = output / "verified_jobs.json"
    verified_path.write_text(json.dumps([j.to_dict() for j in fresh], ensure_ascii=False, indent=2), encoding="utf-8")

    if not fresh:
        LOG.info("No new verified jobs to draft. Review queue: %s", review_path)
        return None

    today = date.today()
    brand = str(config.get("publication", {}).get("brand", "InternAtlas"))
    markdown = render_newsletter(fresh, brand, today)
    filename = f"{today.isoformat()}-{slugify(f'{len(fresh)} early career opportunities')}.md"
    markdown_path = output / filename
    markdown_path.write_text(markdown, encoding="utf-8")

    # Also write latest_issue.md and latest_issue.docx for instant UI preview & Word download
    (output / "latest_issue.md").write_text(markdown, encoding="utf-8")
    try:
        render_newsletter_docx(fresh, output / "latest_issue.docx", brand, today)
        render_newsletter_docx(fresh, output / filename.replace(".md", ".docx"), brand, today)
    except Exception as exc:
        LOG.warning("Could not write DOCX version of newsletter: %s", exc)

    # Mark as seen only after the Markdown draft is safely written.
    if not ignore_seen:
        store.mark_seen(fresh)
    LOG.info("Generated %d verified listings into %s", len(fresh), markdown_path)
    LOG.info("Unverified/aggregator candidates saved to %s", review_path)
    return markdown_path


def create_substack_draft(markdown_path: Path, publication_url: str) -> int:
    """Use python-substack CLI; draft creation only. Never publish or send."""
    import subprocess
    import shutil

    env = os.environ.copy()
    env["PUBLICATION_URL"] = publication_url
    # python-substack supports COOKIES_STRING / COOKIES_PATH or EMAIL/PASSWORD.
    title = markdown_path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
    executable = shutil.which("substack")
    if not executable:
        raise RuntimeError("Substack CLI not installed. Install project extras with: pip install -e .[publish]")
    command = [executable, "--json", "--publication-url", publication_url, "drafts", "create", str(markdown_path), "--title", title]
    LOG.info("Creating unpublished Substack draft for %s", publication_url)
    result = subprocess.run(command, env=env, check=False, text=True, capture_output=True)
    if result.stdout:
        LOG.info("Substack CLI response: %s", result.stdout.strip()[:1000])
    if result.returncode != 0:
        LOG.error("Substack draft creation failed: %s", result.stderr.strip()[:1000])
        raise RuntimeError("Substack draft creation failed; inspect logs and authentication configuration")
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and draft Flerken Studio newsletter issues.")
    parser.add_argument("run", nargs="?", choices=["run"], default="run")
    parser.add_argument("--config", default="config/sources.yaml")
    parser.add_argument("--output", default="output")
    parser.add_argument("--state-db", default="state/seen.sqlite3")
    parser.add_argument("--dry-run", action="store_true", help="Generate Markdown only; do not contact Substack")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    path = run(args.config, args.output, args.state_db, args.dry_run)
    if path and not args.dry_run and os.getenv("CREATE_SUBSTACK_DRAFT", "false").lower() == "true":
        publication_url = os.getenv("PUBLICATION_URL", "https://flerkenstudio.substack.com/")
        create_substack_draft(path, publication_url)
    elif path:
        LOG.info("Markdown generated. Substack draft creation is disabled; review the file before enabling it.")


if __name__ == "__main__":
    main()
