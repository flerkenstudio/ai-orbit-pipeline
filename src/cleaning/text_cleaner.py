"""Text sanitization: strip HTML, fix whitespace/encoding, clamp length."""
import html
import re

from src.config import DESCRIPTION_MAX


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)          # strip tags
    text = re.sub(r"&[a-z]+;", " ", text)          # leftover entities
    text = re.sub(r"https?://\S+", "", text)       # urls inside descriptions
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_description(text: str) -> str:
    text = clean_text(text)
    if len(text) > DESCRIPTION_MAX:
        text = text[:DESCRIPTION_MAX].rsplit(" ", 1)[0] + "…"
    return text
