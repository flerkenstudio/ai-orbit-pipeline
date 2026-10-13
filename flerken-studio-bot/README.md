# Flerken Studio Substack Automation Bot

Draft-first newsletter automation for [Flerken Studio](https://flerkenstudio.substack.com/). It uses your InternAtlas Markdown issue as the **format reference**, not as a recurring source of fresh jobs.

## What this first version does

- Collects jobs from enabled public Greenhouse and Lever employer boards, plus permitted RSS feeds.
- Prefers official employer/ATS application links. Aggregator-only items without an explicit official URL go to `output/review_queue.json` and are **not** included as verified listings.
- Checks application URLs for reachability, categorizes roles, filters for India and remote/global listings, deduplicates within a run, and records previously seen jobs in SQLite.
- Generates a dated Markdown issue in the InternAtlas style.
- Runs on GitHub Actions on alternate UTC calendar days, around 9:00 AM IST. `workflow_dispatch` lets you test it manually.
- If the `SUBSTACK_COOKIES_STRING` GitHub secret is configured, it attempts to create an **unpublished draft only** using the `python-substack` CLI. It does not publish or email subscribers.
- Uploads the Markdown and review queue as a workflow artifact.

## Assumptions and current limits

1. The uploaded InternAtlas issue defines layout and tone; job listings must be freshly collected from configured sources.
2. No sources are enabled by default. Configure your company boards/feeds in `config/sources.yaml` before expecting output.
3. Greenhouse/Lever URLs are official ATS-hosted application links, but URL reachability does not prove that the role is still open or that all details are current.
4. Generic RSS feeds are treated as aggregator candidates unless they supply an explicit `<official_url>` field. These require review and are excluded from the generated issue by default.
5. Substack has no stable, documented public API for these draft operations. `python-substack` relies on undocumented Substack interfaces; it may break, and authentication may need refreshing. It is an adapter, not a guaranteed service.
6. The GitHub Actions workflow stores a deduplication SQLite file using Actions cache. Cache is best-effort; for strict durable state across runs, use a small external database or commit a state artifact deliberately.
7. The current implementation checks link reachability but does not yet use an LLM to infer eligibility, deadlines, salary, or role-open status. It never invents those details.

## Quick start on Windows

Install Python 3.11 or 3.12 and Git. In PowerShell:

```powershell
cd flerken-studio-bot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[test,publish]"
Copy-Item config\sources.example.yaml config\sources.yaml
```

The repository includes a starter `config/sources.yaml`; edit it directly. For each company, enable a supported source and replace its placeholder board/site token. For example:

```yaml
- type: greenhouse
  name: Example employer
  company: Example Employer
  board: employer_board_token
  enabled: true
```

For Lever:

```yaml
- type: lever
  name: Example employer
  company: Example Employer
  site: employer_site_slug
  enabled: true
```

Only add RSS feeds that permit automated fetching. Don't bypass logins, CAPTCHAs, robots rules, or site terms. Use official feeds/APIs when available.

Run tests:

```powershell
pytest -q
```

Run collection/generation (Markdown only by default):

```powershell
python -m flerken_bot.cli --config config/sources.yaml --output output --state-db state/seen.sqlite3
```

The first run will produce no issue until you enable at least one source. The output folder contains a Markdown article and `review_queue.json` for items requiring manual verification.

## Configure GitHub Actions

1. Create a private GitHub repository and push this project.
2. Edit `config/sources.yaml` and commit only source configuration (never credentials).
3. In repository **Settings → Secrets and variables → Actions**, add `SUBSTACK_COOKIES_STRING` only if you choose to use cookie-based authentication. Follow the `python-substack` project's authentication instructions; do not paste cookies into chat, code, workflow files, issues, or logs. Cookies grant account access and should be treated like passwords.
4. Open **Actions → Flerken Studio newsletter draft → Run workflow** for a manual test.
5. Review the Markdown artifact and the Substack Drafts section. Confirm the draft belongs to Flerken Studio before using it.

If you do not configure the secret, the workflow generates the Markdown artifact only. This is the safe default. You can still copy the Markdown into Substack manually.

## Substack adapter notes

The workflow uses the `substack` CLI provided by `python-substack` to create a draft from Markdown. It never invokes a publish or send command. The library's own documentation says Substack's upstream API is undocumented and can change. Pin and test a known-good dependency version before relying on production runs. If the CLI breaks, disable `SUBSTACK_COOKIES_STRING` and continue with Markdown artifacts while the adapter is repaired.

## Project layout

```text
config/sources.yaml             Source configuration
src/flerken_bot/sources.py      Greenhouse, Lever, RSS collectors
src/flerken_bot/quality.py      URL checks, categorization, deduplication
src/flerken_bot/render.py       Markdown issue generator
src/flerken_bot/cli.py          Pipeline and optional draft adapter
tests/                          Unit tests
.github/workflows/newsletter.yml Alternate-day scheduled workflow
examples/internatlas_reference.md Uploaded reference newsletter
```

## Safety checklist

- Never store a Substack password or session cookie in Git.
- Use GitHub Actions Secrets for authentication and keep logs free of secret values.
- Keep draft creation separate from publication; review all content manually.
- Confirm that source access complies with each site's terms and rate limits.
- Verify that the generated draft is in the intended publication before publishing.
- Remember that a reachable job page may still be closed, expired, or ineligible for a reader.
