"""Standalone runner:  python -m competitions.main [--demo] [--no-linkcheck] [--only NAME] [--freq]"""
import sys
from datetime import datetime, timedelta

from .pipeline import run_competitions_pipeline
from .config import IN_SEASON_MONTHS, VERIFY_FREQUENCY_DAYS


def verify_frequency_days() -> int:
    month = datetime.now().month
    return VERIFY_FREQUENCY_DAYS["in_season" if month in IN_SEASON_MONTHS else "off_season"]


def demo_data() -> list:
    d = lambda n: (datetime.now() + timedelta(days=n)).strftime("%d-%m-%Y")
    return [
        {"title": "Flipkart GRiD 7.0", "organiser": "Flipkart", "official_url": "https://example.com/grid",
         "reg_deadline": d(5), "prize_pool": "₹5 Lakh", "source": "demo", "organiser_type": "company"},
        {"title": "Techfest Coding Challenge", "organiser": "IIT Bombay", "official_url": "https://example.com/tf",
         "reg_deadline": d(20), "prize_pool": "50k", "source": "demo", "organiser_type": "college"},
        {"title": "Campus Quiz Night", "organiser": "Local College", "official_url": "https://example.com/quiz",
         "reg_deadline": d(-3), "prize_pool": "", "source": "demo", "organiser_type": "college"},
        {"title": "Startup Pitch Fest", "organiser": "E-Cell", "official_url": "https://example.com/pitch",
         "reg_deadline": None, "prize_pool": "2 lakh", "source": "demo", "organiser_type": "college"},
        {"title": "", "organiser": "Bad Row", "official_url": ""},  # skipped (missing title)
    ]


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--freq" in args:
        print(f"Re-verify every {verify_frequency_days()} day(s) right now")
        sys.exit(0)
    only = args[args.index("--only") + 1] if "--only" in args else None
    if "--demo" in args:
        run_competitions_pipeline(linkcheck=False, raw_override=demo_data())
    else:
        run_competitions_pipeline(linkcheck="--no-linkcheck" not in args, only=only)
