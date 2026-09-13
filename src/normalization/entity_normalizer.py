"""Canonical entity naming: 'OpenAI, Inc.' / 'Open AI' -> 'openai'."""
import re

LEGAL_SUFFIXES = re.compile(
    r"\s*,?\s*(inc\.?|llc|ltd\.?|corp\.?|corporation|gmbh|pvt\.?|company|labs?|ai)$",
    re.IGNORECASE,
)


def canonical_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r"[^\w\s]", " ", name.lower())
    name = re.sub(r"\s+", " ", name).strip()
    name = LEGAL_SUFFIXES.sub("", name)
    return re.sub(r"\s+", " ", name).strip()
