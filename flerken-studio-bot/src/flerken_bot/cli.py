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

    # Sort candidates by recency (newest published_at first)
    candidates.sort(key=lambda j: j.published_at or "", reverse=True)

    for job in candidates:
        job.category = categorize(job)

    max_jobs = int(max_jobs_override or collection.get("max_jobs_per_issue", 60))
    store = SeenStore(state_db)

    # Prioritize unseen fresh candidates, backfilling with freshest active live candidates if needed
    new_candidates = store.only_new(candidates)
    if ignore_seen:
        pool_to_verify = candidates
    elif len(new_candidates) >= max_jobs:
        pool_to_verify = new_candidates
    else:
        seen_candidates = [c for c in candidates if c not in new_candidates]
        pool_to_verify = new_candidates + seen_candidates

    pool_to_verify = pool_to_verify[: max(max_jobs * 2, 140)]

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


def _find_substack_cmd() -> list[str]:
    import shutil

    exe = shutil.which("substack")
    if exe:
        return [exe]
    py_dir = Path(sys.executable).resolve().parent
    for candidate in (py_dir / "substack.exe", py_dir / "substack"):
        if candidate.exists():
            return [str(candidate)]
    try:
        import substack  # noqa: F401
        return [sys.executable, "-m", "substack.cli"]
    except ImportError:
        raise RuntimeError("Substack CLI not installed. Run: pip install python-substack")


def _normalize_cookie_str(raw: str) -> str:
    val = raw.strip().strip('"').strip("'")
    if not val:
        return ""
    if "=" not in val:
        return f"substack.sid={val}; connect.sid={val}"
    return val


def create_substack_draft(markdown_path: Path, publication_url: str, cookies_string: str | None = None) -> int:
    """Use python-substack CLI; draft creation only. Never publish or send."""
    import subprocess
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=True)
        load_dotenv(ROOT.parent / ".env", override=False)
    except ImportError:
        pass

    env = os.environ.copy()
    env["PUBLICATION_URL"] = publication_url
    if cookies_string and cookies_string.strip():
        env["COOKIES_STRING"] = _normalize_cookie_str(cookies_string)
    elif env.get("COOKIES_STRING"):
        env["COOKIES_STRING"] = _normalize_cookie_str(env["COOKIES_STRING"])

    has_auth = bool(
        env.get("COOKIES_STRING")
        or env.get("COOKIES_PATH")
        or (env.get("EMAIL") and env.get("PASSWORD"))
    )
    if not has_auth:
        raise RuntimeError(
            "AUTH_REQUIRED: Substack session cookie (COOKIES_STRING) is not configured yet. "
            "Paste your Substack cookie in the Substack Auth modal, or paste the copied Markdown directly into your opened Substack editor."
        )

    title = markdown_path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
    base_cmd = _find_substack_cmd()
    command = [*base_cmd, "--json", "--publication-url", publication_url, "drafts", "create", str(markdown_path), "--title", title]
    LOG.info("Creating unpublished Substack draft for %s", publication_url)
    result = subprocess.run(command, env=env, check=False, text=True, capture_output=True)
    if result.stdout:
        LOG.info("Substack CLI response: %s", result.stdout.strip()[:1000])
    if result.returncode != 0:
        err_detail = (result.stderr or result.stdout or "").strip()[:500]
        LOG.error("Substack draft creation failed: %s", err_detail)
        raise RuntimeError(f"Substack API error: {err_detail or 'Check your Substack COOKIES_STRING session cookie.'}")
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
