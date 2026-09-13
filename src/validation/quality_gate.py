"""Final validation pass — produces a report proving data quality."""
import logging
from datetime import datetime, timezone

log = logging.getLogger("pipeline")


def run_validation(entities: list) -> dict:
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "total": len(entities), "passed": 0, "failed": 0,
              "issues": {}}

    for e in entities:
        issues = []
        if not e.name or len(e.name.strip()) < 1:
            issues.append("missing_name")
        if not e.description or len(e.description) < 30:
            issues.append("short_description")
        if not e.url.startswith("https://"):
            issues.append("not_https")
        if not e.logo_url:
            issues.append("missing_logo")
        if not e.categories:
            issues.append("missing_category")
        if not e.source.get("name"):
            issues.append("missing_source")

        if issues:
            report["failed"] += 1
            for i in issues:
                report["issues"].setdefault(i, []).append(e.name)
        else:
            report["passed"] += 1
        e.last_verified = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    log.info("Validation: %d/%d passed", report["passed"], report["total"])
    return report
