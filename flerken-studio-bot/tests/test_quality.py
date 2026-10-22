from pathlib import Path

import requests

from flerken_bot.models import Job
from flerken_bot.quality import SeenStore, categorize, deduplicate, verify_job
from flerken_bot.render import render_newsletter


class FakeResponse:
    status_code = 200
    url = "https://boards.greenhouse.io/acme/jobs/123"
    def close(self):
        pass


class FakeSession:
    def get(self, *args, **kwargs):
        return FakeResponse()


def sample_job(**kwargs):
    data = dict(title="Software Engineer Intern", company="Acme", url="https://boards.greenhouse.io/acme/jobs/123", official_url="https://boards.greenhouse.io/acme/jobs/123", location="Bengaluru, India", work_mode="In-office", source_kind="official")
    data.update(kwargs)
    return Job(**data)


def test_deduplicate_by_url():
    assert len(deduplicate([sample_job(), sample_job(title="Different title")])) == 1


def test_category_detects_software():
    assert categorize(sample_job()) == "Software Development & Core Engineering"


def test_official_link_reachable_is_marked_link_verified():
    job = verify_job(sample_job(), FakeSession())
    assert job.verification_status == "verified_link"
    assert "does not guarantee" not in job.verification_note


def test_aggregator_without_official_url_requires_review():
    job = sample_job(source_kind="aggregator", official_url="", url="https://jobs.example/123")
    job = verify_job(job, FakeSession(), require_official=True)
    assert job.verification_status == "needs_review"


def test_render_has_categories_and_caveat():
    job = sample_job()
    job.category = categorize(job)
    text = render_newsletter([job])
    assert "Software Engineering" in text
    assert "does not guarantee that a role remains open" in text


def test_seen_store_only_returns_new_then_marks_seen(tmp_path: Path):
    store = SeenStore(tmp_path / "seen.sqlite3")
    job = sample_job()
    assert store.only_new([job]) == [job]
    store.mark_seen([job])
    assert store.only_new([job]) == []
